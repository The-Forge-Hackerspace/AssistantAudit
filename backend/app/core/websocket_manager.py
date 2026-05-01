"""
Gestionnaire de connexions WebSocket pour le streaming temps reel.

Gere deux types de connexions :
- user_connections : techniciens connectes via le frontend
- agent_connections : daemons Windows communiquant avec le serveur

Les evenements destines a un user deconnecte sont bufferises (30 min, max 1000)
et rejoues a la reconnexion.
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

from .security import decode_token, verify_agent_token

logger = logging.getLogger(__name__)

BUFFER_MAX_SIZE = 1000
BUFFER_TTL_SECONDS = 1800  # 30 minutes


class ConnectionManager:
    def __init__(self) -> None:
        self.user_connections: dict[int, WebSocket] = {}
        self.agent_connections: dict[str, WebSocket] = {}
        self.agent_owners: dict[str, int] = {}  # agent_uuid -> owner_id (from JWT, trusted)
        self.user_event_buffer: dict[int, list[tuple[datetime, dict]]] = {}
        # Verrou par agent_uuid pour serialiser les reconnexions concurrentes
        # (evite que deux WS en parallele ne s'invalident mutuellement).
        self._agent_locks: dict[str, asyncio.Lock] = {}

    def _get_agent_lock(self, agent_uuid: str) -> asyncio.Lock:
        """Retourne le verrou de l'agent, le cree au besoin (single-threaded loop)."""
        lock = self._agent_locks.get(agent_uuid)
        if lock is None:
            lock = asyncio.Lock()
            self._agent_locks[agent_uuid] = lock
        return lock

    # ── User connections ──────────────────────────────────────────────

    async def connect_user(self, websocket: WebSocket, token: str) -> int | None:
        """
        Authentifie et connecte un user via JWT.
        Retourne user_id si succes, None si auth echoue.
        """
        payload = decode_token(token)
        if payload is None or payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid or expired token")
            return None

        user_id = int(payload["sub"])
        await websocket.accept()
        self.user_connections[user_id] = websocket
        logger.info("WebSocket user connected")

        # Rejouer les evenements bufferises
        await self._replay_buffered_events(user_id, websocket)

        return user_id

    def disconnect_user(self, user_id: int) -> None:
        self.user_connections.pop(user_id, None)
        logger.info("WebSocket user disconnected")

    async def send_to_user(self, user_id: int, event_type: str, data: dict) -> None:
        """
        Envoie un evenement a un user. Si deconnecte, bufferise.
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        ws = self.user_connections.get(user_id)
        if ws is not None:
            try:
                await ws.send_json(event)
                return
            except (WebSocketDisconnect, RuntimeError):
                # Connexion perdue, nettoyer et bufferiser
                self.disconnect_user(user_id)

        # Bufferiser pour reconnexion
        self._buffer_event(user_id, event)

    # ── Agent connections ─────────────────────────────────────────────

    async def connect_agent(self, websocket: WebSocket, token: str) -> str | None:
        """
        Authentifie et connecte un agent via JWT agent.
        Retourne agent_uuid si succes, None si auth echoue.
        """
        import jwt

        try:
            payload = verify_agent_token(token)
        except jwt.PyJWTError:
            await websocket.close(code=4001, reason="Invalid or expired agent token")
            return None

        agent_uuid = payload["sub"]
        owner_id = payload.get("owner_id")

        # Serialiser supersede + register sous un verrou par agent_uuid pour
        # eviter qu'une reconnexion concurrente (meme agent) ne ferme la
        # nouvelle WS ou ne laisse une ancienne en zombie dans le dict.
        async with self._get_agent_lock(agent_uuid):
            # Si une connexion precedente existe, on la remplace dans le dict
            # AVANT toute await pour qu'aucune autre tache ne voie un slot vide.
            old_ws = self.agent_connections.get(agent_uuid)
            self.agent_connections[agent_uuid] = websocket
            # Reinitialiser le mapping owner : si le nouveau JWT n'a pas
            # d'owner_id, on evite de conserver l'ancien propriétaire
            # (attributions erronées de tâches/notifications).
            self.agent_owners.pop(agent_uuid, None)
            if owner_id is not None:
                self.agent_owners[agent_uuid] = int(owner_id)

            await websocket.accept()

            if old_ws is not None:
                try:
                    await old_ws.close(code=1012, reason="Superseded by new connection")
                except Exception:
                    logger.debug("Failed to close superseded agent WS", exc_info=True)

        logger.info(f"WebSocket agent connected: owner={owner_id}")
        return agent_uuid

    def disconnect_agent(self, agent_uuid: str) -> None:
        self.agent_connections.pop(agent_uuid, None)
        self.agent_owners.pop(agent_uuid, None)
        logger.info("WebSocket agent disconnected")

    def get_agent_owner(self, agent_uuid: str) -> int | None:
        """Retourne l'owner_id de confiance (JWT) pour un agent connecte."""
        return self.agent_owners.get(agent_uuid)

    async def send_to_agent(self, agent_uuid: str, event_type: str, data: dict) -> None:
        """Envoie un evenement a un agent. Pas de buffer (l'agent gere sa reconnexion)."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        ws = self.agent_connections.get(agent_uuid)
        if ws is not None:
            try:
                await ws.send_json(event)
            except (WebSocketDisconnect, RuntimeError):
                self.disconnect_agent(agent_uuid)

    # ── Buffer management ─────────────────────────────────────────────

    def _buffer_event(self, user_id: int, event: dict) -> None:
        """Ajoute un evenement au buffer d'un user avec cleanup TTL + taille."""
        if user_id not in self.user_event_buffer:
            self.user_event_buffer[user_id] = []

        buf = self.user_event_buffer[user_id]

        # Cleanup TTL
        now = datetime.now(timezone.utc)
        buf[:] = [(ts, ev) for ts, ev in buf if (now - ts).total_seconds() < BUFFER_TTL_SECONDS]

        # Cleanup taille (garder les plus recents)
        if len(buf) >= BUFFER_MAX_SIZE:
            buf[:] = buf[-(BUFFER_MAX_SIZE - 1) :]

        buf.append((now, event))

    async def _replay_buffered_events(self, user_id: int, websocket: WebSocket) -> None:
        """Rejoue les evenements bufferises pour un user qui se reconnecte."""
        buf = self.user_event_buffer.pop(user_id, [])
        if not buf:
            return

        # Cleanup TTL avant replay
        now = datetime.now(timezone.utc)
        valid = [(ts, ev) for ts, ev in buf if (now - ts).total_seconds() < BUFFER_TTL_SECONDS]

        for idx, (_, event) in enumerate(valid):
            try:
                await websocket.send_json(event)
            except (WebSocketDisconnect, RuntimeError):
                # Re-bufferiser les non-envoyes
                self.user_event_buffer[user_id] = valid[idx:]
                return

        logger.info(f"Replayed {len(valid)} buffered events for user_id={user_id}")


# Instance globale
ws_manager = ConnectionManager()
