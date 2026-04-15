"""
Sweeper de heartbeat agents (TOS-12).

Detecte les agents dont `last_seen` est anterieur au timeout configure, les
marque `offline` et transforme leurs taches `running`/`dispatched`/`pending`
en `failed` avec le motif "Agent timeout". Notifie le frontend du owner via
le WebSocket manager.

Le sweeper tourne en tache asyncio pendant toute la duree de vie de l'app
(start/stop via le lifespan FastAPI). Il est concu pour :
- tolerer les erreurs (une exception loggee n'interrompt pas la boucle),
- respecter l'ordonnancement du reste de l'event loop (sleep entre passes),
- utiliser une session SQLAlchemy dediee par iteration.
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
    """Effectue une passe de detection des agents timeout."""
    # Imports locaux pour eviter les cycles au chargement.
    from ..models.agent import Agent
    from ..services.agent_service import AgentService

    settings = get_settings()
    timeout = timedelta(seconds=settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS)
    cutoff = datetime.now(timezone.utc) - timeout

    db = SessionLocal()
    try:
        stale = (
            db.query(Agent)
            .filter(
                Agent.status == "active",
                Agent.last_seen.isnot(None),
                Agent.last_seen < cutoff,
            )
            .all()
        )

        notifications: list[tuple[int, dict]] = []
        for agent in stale:
            # La connexion WS est-elle encore vivante ? Si oui, on laisse le
            # handler gerer — ca evite les faux-positifs en debut de boucle.
            if agent.agent_uuid in ws_manager.agent_connections:
                continue

            owner_id = agent.user_id
            events = AgentService.mark_agent_offline_and_fail_tasks(
                db, agent, reason="Agent timeout"
            )
            for ev in events:
                logger.warning(
                    "Sweep: agent timeout, task %s marked failed",
                    ev["task_uuid"],
                )
                if owner_id is not None:
                    notifications.append((owner_id, ev))
            logger.info(
                "Sweep: agent marked offline (last_seen=%s)",
                agent.last_seen.isoformat() if agent.last_seen else "none",
            )

        db.commit()
    except Exception:
        logger.exception("Heartbeat sweeper iteration failed")
        db.rollback()
        return
    finally:
        db.close()

    # Notifications hors du bloc DB.
    for owner_id, ev in notifications:
        try:
            await ws_manager.send_to_user(owner_id, "task_status", ev)
        except Exception:
            logger.exception("Failed to notify owner %s of sweep failure", owner_id)


async def run_heartbeat_sweeper() -> None:
    """Boucle principale du sweeper. A lancer via asyncio.create_task()."""
    settings = get_settings()
    interval = max(1, settings.AGENT_HEARTBEAT_SWEEP_INTERVAL_SECONDS)
    logger.info("Heartbeat sweeper started (interval=%ss, timeout=%ss)", interval, settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS)
    try:
        while True:
            await _sweep_once()
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Heartbeat sweeper stopped")
        raise
