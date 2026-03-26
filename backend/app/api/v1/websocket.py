"""
Routes WebSocket pour le streaming temps reel.

- /ws/user : connexion frontend (technicien)
- /ws/agent : connexion daemon Windows (agent)
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


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
            data = await websocket.receive_json()
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

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack", "data": {}})

            elif msg_type in ("task_status", "task_progress"):
                # Forward vers le user proprietaire de l'agent
                owner_id = data.get("owner_id")
                if owner_id is not None:
                    await ws_manager.send_to_user(
                        int(owner_id), msg_type, data.get("data", {})
                    )

            elif msg_type == "task_result":
                owner_id = data.get("owner_id")
                if owner_id is not None:
                    await ws_manager.send_to_user(
                        int(owner_id), "task_result", data.get("data", {})
                    )

    except WebSocketDisconnect:
        ws_manager.disconnect_agent(agent_uuid)
    except Exception:
        logger.exception(f"WebSocket agent error: uuid={agent_uuid}")
        ws_manager.disconnect_agent(agent_uuid)
