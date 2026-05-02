"""Helpers WebSocket pour /ws/agent : resolve, heartbeat, persist task events.

Ces fonctions ouvrent/ferment leur propre session DB (utilisees depuis
le handler WS qui n'a pas de session injectee).

Style B : fonctions module-level (pas de classe statique).
"""

import hashlib
import logging
from datetime import datetime, timezone

from ...core.database import get_db_session
from ...models.agent import Agent
from ...models.agent_task import AgentTask
from .lifecycle import mark_agent_offline_and_fail_tasks

logger = logging.getLogger(__name__)


def ws_resolve_and_activate(agent_uuid: str) -> int | None:
    """Resout agent.id depuis agent_uuid pour les checks d'ownership WS.

    Si l'agent etait "offline" (sweeper), restaure status=active +
    last_seen pour signaler la reconnexion. Ouvre/ferme sa propre session.
    """

    trusted_agent_id: int | None = None
    try:
        with get_db_session() as db:
            agent = db.query(Agent).filter(Agent.agent_uuid == agent_uuid).first()
            if agent is not None:
                trusted_agent_id = agent.id
                if agent.status == "offline":
                    agent.status = "active"
                    agent.last_seen = datetime.now(timezone.utc)
                    log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]
                    logger.info(
                        "Agent %s reconnected — session restored (offline → active)",
                        log_id,
                    )
    except Exception:
        log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]
        logger.exception("Failed to resolve agent_id for %s", log_id)
    return trusted_agent_id


def ws_record_heartbeat(
    agent_uuid: str,
    hb_data: dict,
    client_host: str | None,
) -> None:
    """Persiste le heartbeat WS (last_seen, agent_version, os_info, last_ip)."""

    try:
        with get_db_session() as db:
            agent = db.query(Agent).filter(Agent.agent_uuid == agent_uuid).first()
            if agent:
                agent.last_seen = datetime.now(timezone.utc)
                if hb_data.get("agent_version"):
                    agent.agent_version = hb_data["agent_version"]
                if hb_data.get("os_info"):
                    agent.os_info = hb_data["os_info"]
                if client_host:
                    agent.last_ip = client_host
    except Exception:
        log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]
        logger.exception("Failed to update last_seen for agent %s", log_id)


def ws_persist_task_status_or_progress(
    msg_type: str,
    task_uuid: str,
    trusted_agent_id: int,
    agent_uuid: str,
    ws_data: dict,
) -> None:
    """Persiste un message task_status ou task_progress recu par WS.

    Pour task_progress, mute ws_data['progress'] avec la valeur recalculee
    par compute_progress (afin que le forward au front utilise la valeur
    corrigee).
    """

    try:
        with get_db_session() as db:
            task = (
                db.query(AgentTask)
                .filter(
                    AgentTask.task_uuid == task_uuid,
                    AgentTask.agent_id == trusted_agent_id,
                )
                .first()
            )
            if not task:
                log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]
                logger.warning(
                    "Agent %s attempted %s on task %s — not owned or not found",
                    log_id,
                    msg_type,
                    task_uuid,
                )
                return

            if msg_type == "task_status":
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
                # Sur echec d'une collecte SSH/WinRM, l'agent envoie
                # uniquement task_status (sans task_result). Hydrater la
                # CollectResult liee pour ne pas la laisser en RUNNING.
                if new_status in ("failed", "cancelled") and task.tool in (
                    "ssh-collect",
                    "winrm-collect",
                ):
                    from ...models.collect_result import CollectResult
                    from .. import collect_service

                    collect = (
                        db.query(CollectResult)
                        .filter(CollectResult.agent_task_id == task.id)
                        .first()
                    )
                    if collect is not None:
                        collect_service.hydrate_collect_from_agent_result(
                            db,
                            collect,
                            None,
                            ws_data.get("error_message")
                            or f"Tache agent {new_status}",
                        )
            else:  # task_progress
                from ..scan_progress import compute_progress

                pct = ws_data.get("progress")
                if pct is None:
                    pct = ws_data.get("percent")
                raw_pct = int(pct) if isinstance(pct, (int, float)) else None
                lines = ws_data.get("output_lines") or []
                new_pct = compute_progress(task.task_uuid, lines, raw_pct)
                task.progress = new_pct
                ws_data["progress"] = new_pct
    except Exception:
        logger.exception("Failed to persist %s for %s", msg_type, task_uuid)


def ws_persist_task_result(
    task_uuid: str,
    trusted_agent_id: int,
    agent_uuid: str,
    ws_data: dict,
) -> None:
    """Persiste un message task_result recu par WS (status, result, hydrate collect)."""

    try:
        task_uuid_to_reset: str | None = None
        with get_db_session() as db:
            task = (
                db.query(AgentTask)
                .filter(
                    AgentTask.task_uuid == task_uuid,
                    AgentTask.agent_id == trusted_agent_id,
                )
                .first()
            )
            if not task:
                log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]
                logger.warning(
                    "Agent %s attempted task_result on task %s — not owned or not found",
                    log_id,
                    task_uuid,
                )
                return

            task.status = "completed"
            task.progress = 100
            task.completed_at = datetime.now(timezone.utc)
            if ws_data.get("result_summary"):
                task.result_summary = ws_data["result_summary"]
            if ws_data.get("error_message"):
                task.error_message = ws_data["error_message"]
                task.status = "failed"
            # Hydrater le CollectResult lie a cette tache si c'est une collecte agent
            if task.tool in ("ssh-collect", "winrm-collect"):
                from ...models.collect_result import CollectResult
                from .. import collect_service

                collect = (
                    db.query(CollectResult)
                    .filter(CollectResult.agent_task_id == task.id)
                    .first()
                )
                if collect is not None:
                    collect_service.hydrate_collect_from_agent_result(
                        db,
                        collect,
                        ws_data.get("result_summary"),
                        ws_data.get("error_message"),
                    )
            task_uuid_to_reset = task.task_uuid

        if task_uuid_to_reset:
            from ..scan_progress import reset_task

            reset_task(task_uuid_to_reset)
    except Exception:
        logger.exception("Failed to persist task_result for %s", task_uuid)


def ws_handle_disconnect(agent_uuid: str, reason: str) -> list[dict]:
    """Marque l'agent offline et fail ses taches actives sur deconnexion WS.

    Retourne la liste d'evenements task_status a forwarder vers le owner.
    """

    events: list[dict] = []
    try:
        with get_db_session() as db:
            agent = db.query(Agent).filter(Agent.agent_uuid == agent_uuid).first()
            if not agent:
                return events
            events = mark_agent_offline_and_fail_tasks(db, agent, reason)
            log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]
            for ev in events:
                logger.warning(
                    "Orphan task marked failed: %s (agent %s)",
                    ev["task_uuid"],
                    log_id,
                )
    except Exception:
        log_id = hashlib.sha256(agent_uuid.encode("utf-8")).hexdigest()[:12]
        logger.exception("Failed to handle orphan tasks for agent %s", log_id)
    return events
