"""
Routes WebSocket pour le streaming temps reel.

- /ws/user : connexion frontend (technicien)
- /ws/agent : connexion daemon Windows (agent)
"""

import hashlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# Taille max d'un message WS entrant (16 Ko — largement suffisant pour des commandes JSON)
_MAX_WS_MESSAGE_SIZE = 16 * 1024


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
    Token JWT passe en query param : /ws/user?token=xxx
    """
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

    # Pour les updates en base (heartbeat last_seen + task status)
    from datetime import datetime, timezone

    from ...core.database import SessionLocal
    from ...models.agent import Agent
    from ...models.agent_task import AgentTask

    # Resoudre agent.id depuis agent_uuid pour les checks d'ownership sur les taches.
    # Restaurer le status "active" si l'agent avait ete marque "offline" par le sweeper
    # (cas d'une reconnexion apres un timeout reseau).
    trusted_agent_id: int | None = None
    try:
        db = SessionLocal()
        _agent = db.query(Agent).filter(Agent.agent_uuid == agent_uuid).first()
        if _agent:
            trusted_agent_id = _agent.id
            if _agent.status == "offline":
                _agent.status = "active"
                _agent.last_seen = datetime.now(timezone.utc)
                db.commit()
                logger.info("Agent %s reconnected — session restored (offline → active)", agent_log_id)
    except Exception:
        logger.exception("Failed to resolve agent_id for %s", agent_log_id)
    finally:
        db.close()

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
                # Mettre a jour last_seen en base
                try:
                    db = SessionLocal()
                    agent = db.query(Agent).filter(Agent.agent_uuid == agent_uuid).first()
                    if agent:
                        agent.last_seen = datetime.now(timezone.utc)
                        hb_data = data.get("data", {})
                        if hb_data.get("agent_version"):
                            agent.agent_version = hb_data["agent_version"]
                        if hb_data.get("os_info"):
                            agent.os_info = hb_data["os_info"]
                        client_host = websocket.client.host if websocket.client else None
                        if client_host:
                            agent.last_ip = client_host
                        db.commit()
                except Exception:
                    logger.exception("Failed to update last_seen for agent %s", agent_log_id)
                finally:
                    db.close()

            elif msg_type in ("task_status", "task_progress"):
                ws_data = data.get("data", {})
                # Persister le changement de status en base
                if msg_type == "task_status" and ws_data.get("task_uuid"):
                    try:
                        db = SessionLocal()
                        task = (
                            db.query(AgentTask)
                            .filter(
                                AgentTask.task_uuid == ws_data["task_uuid"],
                                AgentTask.agent_id == trusted_agent_id,
                            )
                            .first()
                        )
                        if not task:
                            logger.warning(
                                "Agent %s attempted task_status on task %s — not owned or not found",
                                agent_log_id,
                                ws_data["task_uuid"],
                            )
                        if task:
                            new_status = ws_data.get("status")
                            if new_status:
                                task.status = new_status
                            if new_status == "running" and task.started_at is None:
                                task.started_at = datetime.now(timezone.utc)
                            if new_status in ("completed", "failed", "cancelled"):
                                task.completed_at = datetime.now(timezone.utc)
                                if new_status == "completed":
                                    task.progress = 100
                            if ws_data.get("error_message"):
                                task.error_message = ws_data["error_message"]
                            db.commit()
                    except Exception:
                        logger.exception("Failed to persist task_status for %s", ws_data.get("task_uuid"))
                    finally:
                        db.close()
                # Forward vers le owner
                if trusted_owner_id is not None:
                    await ws_manager.send_to_user(trusted_owner_id, msg_type, ws_data)

            elif msg_type == "task_result":
                ws_data = data.get("data", {})
                # Persister le result en base
                if ws_data.get("task_uuid"):
                    try:
                        db = SessionLocal()
                        task = (
                            db.query(AgentTask)
                            .filter(
                                AgentTask.task_uuid == ws_data["task_uuid"],
                                AgentTask.agent_id == trusted_agent_id,
                            )
                            .first()
                        )
                        if not task:
                            logger.warning(
                                "Agent %s attempted task_result on task %s — not owned or not found",
                                agent_log_id,
                                ws_data["task_uuid"],
                            )
                        if task:
                            task.status = "completed"
                            task.progress = 100
                            task.completed_at = datetime.now(timezone.utc)
                            if ws_data.get("result_summary"):
                                task.result_summary = ws_data["result_summary"]
                            if ws_data.get("error_message"):
                                task.error_message = ws_data["error_message"]
                                task.status = "failed"
                            db.commit()
                    except Exception:
                        logger.exception("Failed to persist task_result for %s", ws_data.get("task_uuid"))
                    finally:
                        db.close()
                if trusted_owner_id is not None:
                    await ws_manager.send_to_user(trusted_owner_id, "task_result", ws_data)

    except WebSocketDisconnect:
        await _handle_agent_disconnect(agent_uuid, trusted_owner_id)
    except Exception:
        logger.exception("WebSocket agent error: agent=%s", agent_log_id)
        await _handle_agent_disconnect(agent_uuid, trusted_owner_id)


async def _handle_agent_disconnect(agent_uuid: str, owner_id: int | None) -> None:
    """Nettoie a la deconnexion : marque les taches running comme failed."""
    agent_log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]

    from ...core.database import SessionLocal
    from ...models.agent import Agent
    from ...services.agent_service import AgentService

    ws_manager.disconnect_agent(agent_uuid)

    reason = "Agent deconnecte pendant l'execution"
    events: list[dict] = []
    try:
        db = SessionLocal()
        agent = db.query(Agent).filter(Agent.agent_uuid == agent_uuid).first()
        if not agent:
            return

        events = AgentService.mark_agent_offline_and_fail_tasks(db, agent, reason)
        db.commit()

        for ev in events:
            logger.warning("Orphan task marked failed: %s (agent %s)", ev["task_uuid"], agent_log_id)
    except Exception:
        logger.exception("Failed to handle orphan tasks for agent %s", agent_log_id)
    finally:
        db.close()

    # Notifier le frontend hors du bloc DB
    if owner_id is not None:
        for ev in events:
            await ws_manager.send_to_user(owner_id, "task_status", ev)
