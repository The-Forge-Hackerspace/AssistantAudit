"""
Routes WebSocket pour le streaming temps reel.

- /ws/user : connexion frontend (technicien)
- /ws/agent : connexion daemon Windows (agent)
"""

import hashlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.websocket_manager import ws_manager
from ...services.agent_service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# Taille max d'un message WS entrant. Une commande/heartbeat fait quelques Ko,
# mais un task_result d'une collecte WinRM/SSH peut contenir l'inventaire complet
# d'un poste (services, users, network) — facilement plusieurs dizaines de Ko.
_MAX_WS_MESSAGE_SIZE = 4 * 1024 * 1024


async def _receive_json_safe(websocket: WebSocket) -> dict | None:
    """Recoit un message JSON avec validation de taille."""
    raw = await websocket.receive_text()
    if len(raw) > _MAX_WS_MESSAGE_SIZE:
        logger.warning(f"WS message too large ({len(raw)} bytes), ignoring")
        return None
    import json

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None


@router.websocket("/ws/user")
async def ws_user(websocket: WebSocket, token: str = ""):
    """
    WebSocket pour les techniciens (frontend).
    Source du token JWT (par ordre de priorite) :
      1. Cookie httpOnly `aa_access_token` (auth principale via SameSite=Strict)
      2. Query param `?token=...` (compat clients legacy)
    """
    cookie_token = websocket.cookies.get("aa_access_token", "")
    token = cookie_token or token
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return

    user_id = await ws_manager.connect_user(websocket, token)
    if user_id is None:
        return  # connect_user a deja ferme le websocket

    try:
        while True:
            data = await _receive_json_safe(websocket)
            if data is None:
                continue
            # Commandes du frontend (cancel_scan, etc.)
            cmd = data.get("command")
            if cmd == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
            # Les autres commandes seront ajoutees dans les etapes suivantes
    except WebSocketDisconnect:
        ws_manager.disconnect_user(user_id)
    except Exception:
        logger.exception(f"WebSocket user error: user_id={user_id}")
        ws_manager.disconnect_user(user_id)


@router.websocket("/ws/agent")
async def ws_agent(websocket: WebSocket, token: str = ""):
    """
    WebSocket pour les agents (daemon Windows).
    Token JWT agent passe en query param : /ws/agent?token=xxx
    """
    if not token:
        await websocket.close(code=4001, reason="Agent token required")
        return

    agent_uuid = await ws_manager.connect_agent(websocket, token)
    if agent_uuid is None:
        return

    # Identifiant opaque pour les logs : SHA-256 tronque, casse la taint CodeQL
    # (agent_uuid derive du JWT et est traque comme secret par py/clear-text-logging-sensitive-data)
    agent_log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]

    # owner_id de confiance : extrait du JWT a la connexion, pas du message client
    trusted_owner_id = ws_manager.get_agent_owner(agent_uuid)

    # Resoudre agent.id depuis agent_uuid pour les checks d'ownership sur les taches.
    # Restaurer le status "active" si l'agent avait ete marque "offline" par le sweeper
    # (cas d'une reconnexion apres un timeout reseau).
    trusted_agent_id = AgentService.ws_resolve_and_activate(agent_uuid)
    if trusted_agent_id is None:
        logger.warning("Agent %s not found in DB, closing WS", agent_log_id)
        await websocket.close(code=4001, reason="Agent not found")
        return

    try:
        while True:
            data = await _receive_json_safe(websocket)
            if data is None:
                continue
            msg_type = data.get("type")

            if msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack", "data": {}})
                # Mettre a jour last_seen + metadonnees en base
                client_host = websocket.client.host if websocket.client else None
                AgentService.ws_record_heartbeat(
                    agent_uuid, data.get("data", {}), client_host
                )

            elif msg_type in ("task_status", "task_progress"):
                ws_data = data.get("data", {})
                # Persister le changement de status ou la progression en base
                if ws_data.get("task_uuid"):
                    AgentService.ws_persist_task_status_or_progress(
                        msg_type,
                        ws_data["task_uuid"],
                        trusted_agent_id,
                        agent_uuid,
                        ws_data,
                    )
                # Forward vers le owner
                if trusted_owner_id is not None:
                    await ws_manager.send_to_user(trusted_owner_id, msg_type, ws_data)

            elif msg_type == "task_result":
                ws_data = data.get("data", {})
                # Persister le result en base
                if ws_data.get("task_uuid"):
                    AgentService.ws_persist_task_result(
                        ws_data["task_uuid"],
                        trusted_agent_id,
                        agent_uuid,
                        ws_data,
                    )
                if trusted_owner_id is not None:
                    await ws_manager.send_to_user(trusted_owner_id, "task_result", ws_data)

    except WebSocketDisconnect:
        await _handle_agent_disconnect(agent_uuid, trusted_owner_id)
    except Exception:
        logger.exception("WebSocket agent error: agent=%s", agent_log_id)
        await _handle_agent_disconnect(agent_uuid, trusted_owner_id)


async def _handle_agent_disconnect(agent_uuid: str, owner_id: int | None) -> None:
    """Nettoie a la deconnexion : marque les taches running comme failed."""
    ws_manager.disconnect_agent(agent_uuid)

    events = AgentService.ws_handle_disconnect(
        agent_uuid, "Agent deconnecte pendant l'execution"
    )

    # Notifier le frontend hors du bloc DB
    if owner_id is not None:
        for ev in events:
            await ws_manager.send_to_user(owner_id, "task_status", ev)
