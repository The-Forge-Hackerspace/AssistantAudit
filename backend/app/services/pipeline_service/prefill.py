"""Pré-remplissage d'assessment depuis les résultats d'un pipeline (TOS-15)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ...core.errors import BusinessRuleError, NotFoundError
from ...models.agent_task import AgentTask
from ...models.assessment import Assessment, ComplianceStatus, ControlResult
from ...models.collect_pipeline import CollectPipeline, PipelineStatus

from .profile import NmapHost, _normalize_host

logger = logging.getLogger(__name__)


# Mapping signaux Nmap → contrôles d'audit existants (référentiels YAML).
# Logique : la présence d'un port "sensible" déclenche un finding NON_COMPLIANT
# sur le contrôle ciblé. L'absence de signal NE prouve PAS la conformité, donc
# on ne marque jamais COMPLIANT depuis un scan Nmap.
NMAP_CONTROL_MAP: list[dict] = [
    {"port": 23, "proto": "tcp", "control_ref": "SW-004", "service": "Telnet",
     "reason": "Protocole non chiffré, à désactiver"},
    {"port": 23, "proto": "tcp", "control_ref": "LSRV-021", "service": "Telnet",
     "reason": "Service inutile détecté sur le serveur"},
    {"port": 21, "proto": "tcp", "control_ref": "SW-004", "service": "FTP",
     "reason": "Protocole non chiffré, à désactiver"},
    {"port": 69, "proto": "udp", "control_ref": "SW-004", "service": "TFTP",
     "reason": "Protocole non chiffré"},
    {"port": 161, "proto": "udp", "control_ref": "SW-030", "service": "SNMP",
     "reason": "Vérifier que SNMP v3 est utilisé exclusivement"},
    {"port": 3389, "proto": "tcp", "control_ref": "WSRV-031", "service": "RDP",
     "reason": "RDP exposé, vérifier NLA et restriction par IP source"},
]


def prefill_assessment_from_pipeline(
    db: Session,
    pipeline_id: int,
    assessment_id: int,
) -> dict:
    """Pré-remplit un assessment à partir des résultats d'un pipeline Nmap.

    Pour chaque hôte découvert, on confronte les ports ouverts au
    ``NMAP_CONTROL_MAP``. Chaque correspondance déclenche un finding
    ``NON_COMPLIANT`` sur le contrôle ciblé, avec la liste des hôtes concernés
    en preuve. On ne marque jamais ``COMPLIANT`` : l'absence d'un service
    dans le scan ne prouve pas qu'il est désactivé.

    Lève ``ValueError`` si pipeline ou assessment introuvable, si le pipeline
    n'est pas terminé, ou si le scan n'a produit aucun hôte exploitable.
    """
    pipeline = db.get(CollectPipeline, pipeline_id)
    if pipeline is None:
        raise NotFoundError(f"Pipeline #{pipeline_id} introuvable")
    if pipeline.status != PipelineStatus.COMPLETED:
        raise BusinessRuleError(
            f"Pipeline #{pipeline_id} n'est pas terminé (status={pipeline.status.value})"
        )

    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise NotFoundError(f"Assessment #{assessment_id} introuvable")

    if not pipeline.scan_task_uuid:
        raise BusinessRuleError("Aucun résultat à exploiter — scan vide")
    task = db.query(AgentTask).filter(AgentTask.task_uuid == pipeline.scan_task_uuid).first()
    if task is None:
        raise BusinessRuleError("Aucun résultat à exploiter — scan vide")

    raw_hosts = (task.result_summary or {}).get("hosts") or []
    hosts: list[NmapHost] = [_normalize_host(h) for h in raw_hosts if isinstance(h, dict)]
    if not hosts:
        raise BusinessRuleError("Aucun résultat à exploiter — scan vide")

    control_results = (
        db.query(ControlResult).filter(ControlResult.assessment_id == assessment_id).all()
    )
    ref_to_result: dict[str, ControlResult] = {}
    for cr in control_results:
        if cr.control and cr.control.ref_id:
            ref_to_result[cr.control.ref_id] = cr

    findings: dict[str, list[str]] = {}
    for host in hosts:
        ip = host.get("ip") or "?"
        open_ports = {
            (int(p.get("port") or 0), str(p.get("protocol") or "").lower())
            for p in host.get("ports") or []
            if p.get("state") == "open" and p.get("port")
        }
        for mapping in NMAP_CONTROL_MAP:
            key = (mapping["port"], mapping["proto"])
            if key not in open_ports:
                continue
            line = (
                f"  - {ip} : {mapping['service']} "
                f"({mapping['port']}/{mapping['proto']}) — {mapping['reason']}"
            )
            findings.setdefault(mapping["control_ref"], []).append(line)

    prefilled = 0
    non_compliant_count = 0
    details: list[dict] = []
    now = datetime.now(timezone.utc)

    for control_ref, lines in findings.items():
        cr = ref_to_result.get(control_ref)
        if cr is None:
            continue
        evidence = "[Pipeline Nmap] Services exposés détectés :\n" + "\n".join(lines)
        cr.status = ComplianceStatus.NON_COMPLIANT
        cr.evidence = evidence
        cr.auto_result = f"Pipeline Nmap : {len(lines)} finding(s)"
        cr.is_auto_assessed = True
        cr.assessed_at = now
        cr.assessed_by = "pipeline_nmap"
        prefilled += 1
        non_compliant_count += 1
        details.append(
            {
                "control_ref": control_ref,
                "control_title": cr.control.title if cr.control else "",
                "status": "non_compliant",
                "findings_count": len(lines),
            }
        )

    db.flush()
    logger.info(
        "Pré-remplissage pipeline #%s → assessment #%s : %s contrôles non-conformes",
        pipeline_id,
        assessment_id,
        non_compliant_count,
    )

    return {
        "controls_prefilled": prefilled,
        "controls_compliant": 0,
        "controls_non_compliant": non_compliant_count,
        "controls_partial": 0,
        "details": details,
    }
