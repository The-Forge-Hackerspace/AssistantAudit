"""Notifications WS et helpers de polling pour le pipeline (TOS-13 / TOS-81).

Les références à ``get_db_session`` et ``time`` sont résolues via le module
package (``_pkg.get()``) pour que les tests puissent monkeypatcher
``pipeline_service.get_db_session`` / ``pipeline_service.time.sleep``
sans avoir à viser ce sous-module en particulier.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ...models.agent_task import AgentTask
from ...models.collect_pipeline import CollectPipeline

from . import _pkg

logger = logging.getLogger(__name__)


def _notify(user_id: int | None, event_type: str, data: dict) -> None:
    """Envoie un evenement WS au owner du pipeline, tolerant aux erreurs.

    Comme on tourne dans un thread dedie (LocalTaskRunner), on instancie un
    event loop dedie a l'appel. Les erreurs sont loguees mais n'interrompent
    jamais le pipeline — les clients peuvent aussi poller GET /pipelines/{id}.
    """
    if user_id is None:
        return
    try:
        from ...core.event_loop import get_app_loop
        from ...core.websocket_manager import ws_manager

        loop = get_app_loop()
        if loop is None:
            logger.warning("app_loop not available, skipping WS notification")
            return
        asyncio.run_coroutine_threadsafe(
            ws_manager.send_to_user(user_id, event_type, data), loop
        )
    except Exception:
        logger.exception("Pipeline WS notify failed (event=%s)", event_type)


def _pipeline_event(pipeline: CollectPipeline) -> dict:
    """Serialise l'etat courant d'un pipeline pour une notif WS."""
    return {
        "pipeline_id": pipeline.id,
        "status": pipeline.status.value if hasattr(pipeline.status, "value") else str(pipeline.status),
        "scan_status": pipeline.scan_status.value,
        "equipments_status": pipeline.equipments_status.value,
        "collects_status": pipeline.collects_status.value,
        "hosts_discovered": pipeline.hosts_discovered,
        "equipments_created": pipeline.equipments_created,
        "hosts_skipped": pipeline.hosts_skipped,
        "collects_total": pipeline.collects_total,
        "collects_done": pipeline.collects_done,
        "collects_failed": pipeline.collects_failed,
        "error_message": pipeline.error_message,
    }


def _poll_agent_task(task_id: int, timeout_sec: int, poll_interval_sec: int) -> Optional[AgentTask]:
    """Poll l'AgentTask via une session courte par iteration (TOS-81).

    Retourne l'AgentTask en etat terminal (`completed`/`failed`/`cancelled`),
    ou None si introuvable / timeout. Aucune session n'est tenue entre deux
    iterations : chaque tick ouvre/ferme un `get_db_session()` pour ne pas
    saturer le pool SQLAlchemy ni geler un snapshot REPEATABLE READ.
    """
    pkg = _pkg.get()
    deadline = pkg.time.monotonic() + timeout_sec
    while pkg.time.monotonic() < deadline:
        pkg.time.sleep(poll_interval_sec)
        with pkg.get_db_session() as poll_db:
            logger.debug("Pipeline polling : open short session for AgentTask #%s", task_id)
            task_reloaded = poll_db.get(AgentTask, task_id)
            if task_reloaded is None:
                return None
            if task_reloaded.status in ("completed", "failed", "cancelled"):
                # Detacher : la session se ferme apres ce bloc
                poll_db.expunge(task_reloaded)
                return task_reloaded
            # Forcer la fin de transaction implicite avant fermeture
            poll_db.rollback()
    return None  # timeout
