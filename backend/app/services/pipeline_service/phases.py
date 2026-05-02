"""Phases scan & équipements du pipeline (TOS-13 / TOS-81).

Chaque phase ouvre/ferme ses propres sessions courtes (TOS-81) pour ne pas
saturer le pool SQLAlchemy. ``get_db_session`` est résolu via le package
parent pour rester monkeypatchable depuis ``pipeline_service``.
"""

from __future__ import annotations

import logging

from ...models.agent import Agent
from ...models.collect_pipeline import CollectPipeline, PipelineStepStatus
from ...models.equipement import Equipement
from . import _pkg
from .profile import (
    _PROFILE_METHOD,
    AutoCollectProfile,
    NmapHost,
    _normalize_host,
)

logger = logging.getLogger(__name__)


# Polling du scan agent
_SCAN_POLL_INTERVAL_SEC = 5
_SCAN_TIMEOUT_SEC = 30 * 60  # 30 minutes


def _run_scan_phase(
    pipeline_id: int,
    current_user_id: int,
) -> list[NmapHost] | None:
    """Phase 1 : dispatch du scan Nmap vers l'agent, polling jusqu'au résultat.

    Ouvre/ferme sa propre session courte (TOS-81). Retourne la liste des
    hôtes normalisés (ou None si échec/timeout).
    """
    from .. import task_service
    pkg = _pkg.get()

    logger.debug("Pipeline #%s : open scan-phase session", pipeline_id)
    with pkg.get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return None
        agent = db.get(Agent, pipeline.agent_id) if pipeline.agent_id else None
        if agent is None:
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = "Agent introuvable"
            db.commit()
            return None

        try:
            task = task_service.dispatch_task(
                db=db,
                agent_uuid=agent.agent_uuid,
                tool="nmap",
                parameters={
                    "target": pipeline.target,
                    "scan_type": "port_scan",
                },
                current_user_id=current_user_id,
            )
        except Exception as exc:
            logger.exception("Pipeline #%s : dispatch nmap échoué", pipeline_id)
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = f"Dispatch nmap échoué : {exc}"
            db.commit()
            return None

        pipeline.scan_task_uuid = task.task_uuid
        pipeline.scan_status = PipelineStepStatus.RUNNING
        db.commit()
        agent_uuid_local = agent.agent_uuid
        task_id_local = task.id

    # Notification hors session (pas de DB I/O dans le notify).
    task_service.notify_agent_new_task(agent_uuid_local, task)
    logger.debug("Pipeline #%s : scan-phase session closed before polling", pipeline_id)

    # Polling : sessions courtes, une par iteration.
    final_task = pkg._poll_agent_task(task_id_local, _SCAN_TIMEOUT_SEC, _SCAN_POLL_INTERVAL_SEC)

    logger.debug("Pipeline #%s : open scan-phase finalize session", pipeline_id)
    with pkg.get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return None

        if final_task is None:
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = "Timeout du scan agent ou tâche agent introuvable"
            db.commit()
            return None

        if final_task.status != "completed":
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = final_task.error_message or f"Scan {final_task.status}"
            db.commit()
            return None

        raw_hosts = (final_task.result_summary or {}).get("hosts") or []
        hosts: list[NmapHost] = [_normalize_host(h) for h in raw_hosts if isinstance(h, dict)]
        pipeline.hosts_discovered = len(hosts)
        pipeline.scan_status = PipelineStepStatus.COMPLETED
        db.commit()
        return hosts


def _run_equipments_phase(
    pipeline_id: int,
    hosts: list[NmapHost],
) -> list[tuple[int, AutoCollectProfile]]:
    """Phase 2 : pour chaque host, detecter le profil et creer/dedupliquer l'equipement.

    Ouvre/ferme sa propre session courte (TOS-81). Retourne la liste
    (equipement_id, profile) a collecter ensuite — on renvoie les ids
    plutôt que des objets pour eviter qu'ils survivent a la session.
    """
    pkg = _pkg.get()
    logger.debug("Pipeline #%s : open equipments-phase session", pipeline_id)
    with pkg.get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return []

        pipeline.equipments_status = PipelineStepStatus.RUNNING
        db.commit()

        to_collect: list[tuple[int, AutoCollectProfile]] = []

        for host in hosts:
            profile = pkg.detect_collect_profile(host)
            ip = host.get("ip") or ""
            if profile is None or not ip:
                pipeline.hosts_skipped += 1
                continue

            equip_type = _PROFILE_METHOD[profile][2]
            existing = (
                db.query(Equipement)
                .filter(
                    Equipement.site_id == pipeline.site_id,
                    Equipement.ip_address == ip,
                )
                .first()
            )
            if existing is not None:
                equip = existing
            else:
                equip = Equipement(
                    site_id=pipeline.site_id,
                    type_equipement=equip_type,
                    ip_address=ip,
                    hostname=host.get("hostname") or None,
                    mac_address=host.get("mac") or None,
                    fabricant=host.get("vendor") or None,
                    os_detected=host.get("os") or None,
                )
                db.add(equip)
                db.flush()
                pipeline.equipments_created += 1

            to_collect.append((equip.id, profile))

        pipeline.equipments_status = PipelineStepStatus.COMPLETED
        pipeline.collects_total = len(to_collect)
        db.commit()
        logger.debug("Pipeline #%s : equipments-phase session closed", pipeline_id)
        return to_collect
