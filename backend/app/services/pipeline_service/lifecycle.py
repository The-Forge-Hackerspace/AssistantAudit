"""Orchestration top-level du pipeline (TOS-13 / TOS-81).

Enchaine init → scan → equipements → collectes → finalize, en ouvrant une
session courte par phase (TOS-81). Les phases et helpers (`_run_scan_phase`,
`_notify`, `get_db_session`, ...) sont résolus via le package parent
``pipeline_service`` pour préserver la possibilité de monkeypatcher
ces symboles depuis les tests existants.
"""

from __future__ import annotations

import logging
from typing import Optional

from ...models.agent import Agent
from ...models.collect_pipeline import CollectPipeline, PipelineStatus, PipelineStepStatus

from . import _pkg
from .crud import _utcnow

logger = logging.getLogger(__name__)


def execute_pipeline_background(
    pipeline_id: int,
    *,
    agent_uuid: Optional[str] = None,  # conserve pour compat : non utilise (agent lu depuis pipeline.agent_id)
    current_user_id: int,
    username: str,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
) -> None:
    """Orchestre scan agent → equipements → collectes pour un pipeline.

    Execute de maniere synchrone dans un thread dedie (LocalTaskRunner). Chaque
    etape est isolee : un echec de collecte individuelle n'arrete pas la boucle.
    """
    del agent_uuid  # l'agent est lu depuis pipeline.agent_id
    pkg = _pkg.get()
    try:
        # --- Init : session courte 1 ---
        logger.debug("Pipeline #%s : open init session", pipeline_id)
        with pkg.get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                logger.error("Pipeline #%s introuvable", pipeline_id)
                return
            pipeline.status = PipelineStatus.RUNNING
            pipeline.started_at = _utcnow()
            db.commit()
            init_event = pkg._pipeline_event(pipeline)
            init_user = pipeline.created_by
        pkg._notify(init_user, "pipeline_started", init_event)

        # --- Phase 1 — Scan agent (session courte interne) ---
        hosts = pkg._run_scan_phase(pipeline_id, current_user_id)
        with pkg.get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            progress_event = pkg._pipeline_event(pipeline)
            progress_user = pipeline.created_by
        pkg._notify(progress_user, "pipeline_progress", progress_event)
        if hosts is None:
            with pkg.get_db_session() as db:
                pipeline = db.get(CollectPipeline, pipeline_id)
                if pipeline is None:
                    return
                pipeline.status = PipelineStatus.FAILED
                pipeline.completed_at = _utcnow()
                db.commit()
                done_event = pkg._pipeline_event(pipeline)
                done_user = pipeline.created_by
            pkg._notify(done_user, "pipeline_completed", done_event)
            return

        # --- Phase 2 — Equipements (session courte interne) ---
        targets = pkg._run_equipments_phase(pipeline_id, hosts)
        with pkg.get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            progress_event = pkg._pipeline_event(pipeline)
            progress_user = pipeline.created_by
        pkg._notify(progress_user, "pipeline_progress", progress_event)

        # --- Phase 3 — Collectes ---
        # Resoudre l'agent dans une session courte avant de lancer les collectes.
        with pkg.get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            agent = db.get(Agent, pipeline.agent_id) if pipeline.agent_id else None
            if agent is None:
                logger.error("Pipeline #%s : agent introuvable pour la phase collectes", pipeline_id)
                pipeline.collects_status = PipelineStepStatus.FAILED
                pipeline.error_message = pipeline.error_message or "Agent introuvable pour collectes"
                db.commit()
                agent_uuid_local = None
            else:
                agent_uuid_local = agent.agent_uuid

        if agent_uuid_local is not None:
            pkg._run_collects_phase(
                pipeline_id,
                targets,
                agent_uuid=agent_uuid_local,
                current_user_id=current_user_id,
                username=username,
                password=password,
                private_key=private_key,
                passphrase=passphrase,
                use_ssl=use_ssl,
                transport=transport,
            )

        # --- Finalisation : session courte ---
        logger.debug("Pipeline #%s : open finalize session", pipeline_id)
        with pkg.get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            if pipeline.collects_status == PipelineStepStatus.FAILED:
                pipeline.status = PipelineStatus.FAILED
            else:
                pipeline.status = PipelineStatus.COMPLETED
            pipeline.completed_at = _utcnow()
            db.commit()
            created_by = pipeline.created_by
            event_payload = pkg._pipeline_event(pipeline)
        pkg._notify(created_by, "pipeline_completed", event_payload)

    except Exception as exc:
        logger.exception("Pipeline #%s : erreur inattendue", pipeline_id)
        try:
            with pkg.get_db_session() as db:
                pipeline = db.get(CollectPipeline, pipeline_id)
                if pipeline is not None:
                    pipeline.status = PipelineStatus.FAILED
                    pipeline.error_message = str(exc)
                    pipeline.completed_at = _utcnow()
                    db.commit()
                    created_by = pipeline.created_by
                    event_payload = pkg._pipeline_event(pipeline)
                else:
                    created_by = None
                    event_payload = None
            if created_by is not None and event_payload is not None:
                pkg._notify(created_by, "pipeline_completed", event_payload)
        except Exception:
            logger.exception("Impossible de marquer le pipeline #%s comme failed", pipeline_id)
