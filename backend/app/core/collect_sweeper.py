"""
Sweeper de collectes orphelines (TOS-16).

Detecte les `CollectResult` au statut `running` dont la creation est anterieure
au timeout configure (`COLLECT_TIMEOUT_SECONDS`). Sans ce sweeper, une collecte
dispatchee sur un agent qui disparait avant de repondre resterait `running`
indefiniment. Symetrique du `heartbeat_sweeper`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .config import get_settings
from .database import SessionLocal
from .websocket_manager import ws_manager

logger = logging.getLogger(__name__)


async def _sweep_once() -> None:
    """Marque FAILED toute collecte running depassant le timeout."""
    from ..models.agent_task import AgentTask
    from ..models.collect_result import CollectResult, CollectStatus

    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.COLLECT_TIMEOUT_SECONDS)

    db = SessionLocal()
    notifications: list[tuple[int, dict]] = []
    try:
        stale = (
            db.query(CollectResult)
            .filter(
                CollectResult.status == CollectStatus.RUNNING,
                CollectResult.created_at < cutoff,
            )
            .all()
        )

        for collect in stale:
            now = datetime.now(timezone.utc)
            start = collect.created_at
            if start is not None:
                start_tz = start if start.tzinfo is not None else start.replace(tzinfo=timezone.utc)
                collect.duration_seconds = max(0, int((now - start_tz).total_seconds()))
            collect.status = CollectStatus.FAILED
            collect.error_message = "Timeout de la collecte agent"
            collect.completed_at = now

            owner_id: int | None = None
            if collect.agent_task_id is not None:
                task = db.get(AgentTask, collect.agent_task_id)
                if task is not None:
                    owner_id = task.owner_id

            logger.warning(
                "Sweep: collecte #%s timeout (created_at=%s)",
                collect.id,
                collect.created_at.isoformat() if collect.created_at else "none",
            )
            if owner_id is not None:
                notifications.append((owner_id, {"collect_id": collect.id, "status": "failed"}))

        db.commit()
    except Exception:
        logger.exception("Collect sweeper iteration failed")
        db.rollback()
        return
    finally:
        db.close()

    for owner_id, ev in notifications:
        try:
            await ws_manager.send_to_user(owner_id, "collect_status", ev)
        except Exception:
            logger.exception("Failed to notify owner %s of collect timeout", owner_id)


async def run_collect_sweeper() -> None:
    """Boucle principale du sweeper. A lancer via asyncio.create_task()."""
    settings = get_settings()
    interval = max(1, settings.COLLECT_SWEEP_INTERVAL_SECONDS)
    logger.info(
        "Collect sweeper started (interval=%ss, timeout=%ss)",
        interval,
        settings.COLLECT_TIMEOUT_SECONDS,
    )
    try:
        while True:
            await _sweep_once()
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Collect sweeper stopped")
        raise
