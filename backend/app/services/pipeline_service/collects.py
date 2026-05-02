"""Phase 3 : exécution des collectes SSH/WinRM (TOS-13 / TOS-81).

Sessions courtes par etape (TOS-81) : dispatch dans une session, polling
avec sessions courtes par iteration via _poll_agent_task, finalisation
dans une nouvelle session courte. ``get_db_session`` est résolu via le
package parent pour rester monkeypatchable.
"""

from __future__ import annotations

import logging
from typing import Optional

from ...models.collect_pipeline import CollectPipeline, PipelineStepStatus
from ...models.collect_result import CollectResult, CollectStatus
from ...models.equipement import Equipement

from . import _pkg
from .crud import _utcnow
from .profile import AutoCollectProfile, _PROFILE_METHOD

logger = logging.getLogger(__name__)


# Polling des collectes SSH/WinRM agent
_COLLECT_POLL_INTERVAL_SEC = 5
_COLLECT_TIMEOUT_SEC = 15 * 60  # 15 minutes par collecte


def _run_collects_phase(
    pipeline_id: int,
    targets: list[tuple[int, AutoCollectProfile]],
    *,
    agent_uuid: str,
    current_user_id: int,
    username: str,
    password: Optional[str],
    private_key: Optional[str],
    passphrase: Optional[str],
    use_ssl: bool,
    transport: str,
) -> None:
    """Phase 3 : dispatcher une collecte par equipement vers l'agent et poller le resultat."""
    from .. import collect_service
    from .. import task_service
    pkg = _pkg.get()

    if not targets:
        logger.debug("Pipeline #%s : open collects-skip session", pipeline_id)
        with pkg.get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is not None:
                pipeline.collects_status = PipelineStepStatus.SKIPPED
                db.commit()
        return

    logger.debug("Pipeline #%s : open collects-init session", pipeline_id)
    with pkg.get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return
        pipeline.collects_status = PipelineStepStatus.RUNNING
        db.commit()

    for equip_id, profile in targets:
        method, default_port, _ = _PROFILE_METHOD[profile]
        target_port = default_port
        if profile == "windows_server" and use_ssl:
            target_port = 5986

        # 1) Dispatch (session courte)
        collect_id: Optional[int] = None
        task_id: Optional[int] = None
        dispatched_task = None
        try:
            logger.debug("Pipeline #%s : open collect-dispatch session (equip=%s)", pipeline_id, equip_id)
            with pkg.get_db_session() as db:
                equip = db.get(Equipement, equip_id)
                if equip is None:
                    raise RuntimeError(f"Equipement #{equip_id} introuvable")

                collect = collect_service.create_pending_collect(
                    db=db,
                    equipement_id=equip.id,
                    method=method,
                    target_host=equip.ip_address,
                    target_port=target_port,
                    username=username,
                    device_profile=profile,
                )
                db.commit()
                collect_id = collect.id

                dispatched_task = collect_service.dispatch_collect_to_agent(
                    db=db,
                    collect_id=collect_id,
                    agent_uuid=agent_uuid,
                    current_user_id=current_user_id,
                    password=password,
                    private_key=private_key,
                    passphrase=passphrase,
                    use_ssl=use_ssl,
                    transport=transport,
                )
                db.commit()
                task_id = dispatched_task.id
                # Detacher la task pour la passer hors session
                db.expunge(dispatched_task)
        except Exception:
            logger.exception(
                "Pipeline #%s : dispatch collecte echoue (equipement=%s)",
                pipeline_id,
                equip_id,
            )
            with pkg.get_db_session() as db:
                pipeline = db.get(CollectPipeline, pipeline_id)
                if pipeline is not None:
                    pipeline.collects_failed += 1
                    db.commit()
                    pkg._notify(pipeline.created_by, "pipeline_progress", pkg._pipeline_event(pipeline))
            continue

        # Notification hors session
        if dispatched_task is not None:
            task_service.notify_agent_new_task(agent_uuid, dispatched_task)

        # 2) Polling : sessions courtes par iteration
        final_task = pkg._poll_agent_task(task_id, _COLLECT_TIMEOUT_SEC, _COLLECT_POLL_INTERVAL_SEC)
        timed_out = final_task is None or (
            final_task.status not in ("completed", "failed", "cancelled")
        )

        # 3) Finalisation (session courte)
        logger.debug("Pipeline #%s : open collect-finalize session (collect=%s)", pipeline_id, collect_id)
        with pkg.get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                continue
            try:
                final = db.get(CollectResult, collect_id) if collect_id else None
                if timed_out and final is not None and final.status == CollectStatus.RUNNING:
                    final.status = CollectStatus.FAILED
                    final.error_message = "Timeout de la collecte agent"
                    final.completed_at = _utcnow()
                    logger.warning(
                        "Pipeline #%s : collecte #%s timeout (task #%s)",
                        pipeline_id,
                        collect_id,
                        task_id,
                    )
                if final is not None and final.status == CollectStatus.SUCCESS:
                    pipeline.collects_done += 1
                else:
                    pipeline.collects_failed += 1
            finally:
                db.commit()
                pkg._notify(pipeline.created_by, "pipeline_progress", pkg._pipeline_event(pipeline))

    # Statut final de la phase : session courte de cloture
    logger.debug("Pipeline #%s : open collects-final session", pipeline_id)
    with pkg.get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return
        if pipeline.collects_failed == pipeline.collects_total and pipeline.collects_total > 0:
            pipeline.collects_status = PipelineStepStatus.FAILED
        else:
            pipeline.collects_status = PipelineStepStatus.COMPLETED
        db.commit()
