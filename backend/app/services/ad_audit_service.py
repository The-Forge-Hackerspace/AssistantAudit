"""
Service AD Audit — Orchestration des audits Active Directory,
persistance des résultats et pré-remplissage des contrôles d'audit.
"""

import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..core.audit_logger import log_access_denied
from ..core.database import get_db_session
from ..core.errors import BusinessRuleError, NotFoundError
from ..models.ad_audit_result import ADAuditResultModel, ADAuditStatus
from ..models.assessment import Assessment, ComplianceStatus, ControlResult
from ..models.equipement import Equipement
from ..tools.ad_auditor.auditor import ADAuditor

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Mappings findings AD → contrôles d'audit
# ══════════════════════════════════════════════════════════════

AD_CONTROL_MAP: list[dict] = [
    {
        "control_ref": "AD-001",
        "check": "AD-001",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
        "on_partial": "partial",
    },
    {
        "control_ref": "AD-002",
        "check": "AD-002",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
    },
    {
        "control_ref": "AD-010",
        "check": "AD-010",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
    },
    {
        "control_ref": "AD-012",
        "check": "AD-012",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
    },
    {
        "control_ref": "AD-013",
        "check": "AD-013",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
        "on_partial": "partial",
    },
    {
        "control_ref": "AD-020",
        "check": "AD-020",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
        "on_partial": "partial",
    },
    {
        "control_ref": "AD-021",
        "check": "AD-021",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
    },
    {
        "control_ref": "AD-022",
        "check": "AD-022",
        "on_compliant": "compliant",
        "on_non_compliant": "non_compliant",
    },
]


def create_pending_ad_audit(
    db: Session,
    equipement_id: Optional[int],
    target_host: str,
    target_port: int,
    username: str,
    domain: str,
    owner_id: int | None = None,
) -> ADAuditResultModel:
    """Crée un enregistrement d'audit AD en statut 'running'."""
    if equipement_id:
        equip = db.get(Equipement, equipement_id)
        if not equip:
            raise NotFoundError(f"Équipement #{equipement_id} introuvable")

    audit = ADAuditResultModel(
        equipement_id=equipement_id,
        status=ADAuditStatus.RUNNING,
        target_host=target_host,
        target_port=target_port,
        username=username,
        domain=domain,
        owner_id=owner_id,
    )
    db.add(audit)
    db.flush()
    db.refresh(audit)
    return audit


def execute_ad_audit_background(
    audit_id: int,
    password: str,
    use_ssl: bool = False,
    auth_method: str = "ntlm",
) -> None:
    """
    Exécute l'audit AD en arrière-plan.
    Appelé dans un thread séparé.
    """
    try:
        with get_db_session() as db:
            audit = db.get(ADAuditResultModel, audit_id)
            if not audit:
                logger.error(f"[AD_AUDIT] Audit #{audit_id} introuvable en BDD")
                return

            start_time = time.time()

            auditor = ADAuditor(
                host=audit.target_host,
                port=audit.target_port,
                use_ssl=use_ssl,
                username=audit.username,
                password=password,
                domain=audit.domain,
                auth_method=auth_method,
            )

            result = auditor.audit()
            elapsed = int(time.time() - start_time)

            # Persister les résultats
            if result.success:
                audit.status = ADAuditStatus.SUCCESS
                audit.domain_name = result.domain_name
                audit.domain_functional_level = result.domain_functional_level
                audit.forest_functional_level = result.forest_functional_level
                audit.total_users = result.total_users
                audit.enabled_users = result.enabled_users
                audit.disabled_users = result.disabled_users
                audit.dc_list = [dict(dc) for dc in result.dc_list]
                audit.domain_admins = [dict(m) for m in result.domain_admins]
                audit.enterprise_admins = [dict(m) for m in result.enterprise_admins]
                audit.schema_admins = [dict(m) for m in result.schema_admins]
                audit.inactive_users = [dict(u) for u in result.inactive_users[:50]]  # limiter
                audit.never_expire_password = [dict(u) for u in result.never_expire_password[:50]]
                audit.never_logged_in = [dict(u) for u in result.never_logged_in[:50]]
                audit.admin_account_status = dict(result.admin_account_status) if result.admin_account_status else None
                audit.password_policy = dict(result.password_policy) if result.password_policy else None
                audit.fine_grained_policies = [dict(p) for p in result.fine_grained_policies]
                audit.gpo_list = [dict(g) for g in result.gpo_list]
                audit.laps_deployed = result.laps_deployed
                audit.findings = [asdict(f) for f in result.findings]
                audit.summary = result.summary
            else:
                audit.status = ADAuditStatus.FAILED
                audit.error_message = result.error

            audit.completed_at = datetime.now(timezone.utc)
            audit.duration_seconds = elapsed

            logger.info(f"[AD_AUDIT] Audit #{audit_id} terminé en {elapsed}s (status={audit.status.value})")

    except Exception as e:
        logger.exception(f"[AD_AUDIT] Erreur fatale audit #{audit_id}")
        try:
            with get_db_session() as db:
                audit = db.get(ADAuditResultModel, audit_id)
                if audit:
                    audit.status = ADAuditStatus.FAILED
                    audit.error_message = str(e)
                    audit.completed_at = datetime.now(timezone.utc)
        except Exception:
            pass


def list_ad_audit_results(
    db: Session,
    equipement_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    owner_id: int | None = None,
    is_admin: bool = False,
) -> list[ADAuditResultModel]:
    """Liste les audits AD, optionnellement filtrés par équipement et owner."""
    q = db.query(ADAuditResultModel)
    if owner_id is not None and not is_admin:
        q = q.filter(ADAuditResultModel.owner_id == owner_id)
    if equipement_id:
        q = q.filter(ADAuditResultModel.equipement_id == equipement_id)
    return q.order_by(ADAuditResultModel.created_at.desc()).offset(skip).limit(limit).all()


def get_ad_audit_result(
    db: Session,
    audit_id: int,
    owner_id: int | None = None,
    is_admin: bool = False,
) -> Optional[ADAuditResultModel]:
    """Récupère le détail d'un audit AD. Vérifie ownership si owner_id fourni."""
    audit = db.get(ADAuditResultModel, audit_id)
    if audit and owner_id is not None and not is_admin and audit.owner_id != owner_id:
        log_access_denied(owner_id, "ADAuditResult", audit_id)
        return None
    return audit


def delete_ad_audit_result(
    db: Session,
    audit_id: int,
    owner_id: int | None = None,
    is_admin: bool = False,
) -> bool:
    """Supprime un audit AD. Vérifie ownership."""
    audit = db.get(ADAuditResultModel, audit_id)
    if not audit:
        return False
    if owner_id is not None and not is_admin and audit.owner_id != owner_id:
        log_access_denied(owner_id, "ADAuditResult", audit_id, action="delete")
        return False
    db.delete(audit)
    db.flush()
    return True


def prefill_assessment_from_ad_audit(
    db: Session,
    audit_id: int,
    assessment_id: int,
) -> dict:
    """
    Pré-remplit un assessment à partir des résultats d'un audit AD.
    Mappe les findings AD vers les contrôles du framework AD.
    """
    audit = db.get(ADAuditResultModel, audit_id)
    if not audit:
        raise NotFoundError(f"Audit AD #{audit_id} introuvable")
    if audit.status != ADAuditStatus.SUCCESS:
        raise BusinessRuleError(f"Audit AD #{audit_id} n'est pas terminé avec succès")

    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise NotFoundError(f"Assessment #{assessment_id} introuvable")

    # Charger les control results de l'assessment
    control_results = db.query(ControlResult).filter(ControlResult.assessment_id == assessment_id).all()

    # Index par ref_id
    cr_by_ref: dict[str, ControlResult] = {}
    for cr in control_results:
        if cr.control and cr.control.ref_id:
            cr_by_ref[cr.control.ref_id] = cr

    # Index findings par control_ref
    findings_by_ref: dict[str, dict] = {}
    if audit.findings:
        for f in audit.findings:
            findings_by_ref[f.get("control_ref", "")] = f

    prefilled = 0
    compliant_count = 0
    non_compliant_count = 0
    partial_count = 0
    details = []

    for mapping in AD_CONTROL_MAP:
        ref = mapping["control_ref"]
        finding = findings_by_ref.get(ref)
        cr = cr_by_ref.get(ref)

        if not finding or not cr:
            continue

        finding_status = finding.get("status", "info")

        # Ne pas prefill les "info" (vérification manuelle requise)
        if finding_status == "info":
            continue

        # Mapper le status
        if finding_status == "compliant":
            new_status = ComplianceStatus.COMPLIANT
            compliant_count += 1
        elif finding_status == "non_compliant":
            new_status = ComplianceStatus.NON_COMPLIANT
            non_compliant_count += 1
        elif finding_status == "partial":
            new_status = ComplianceStatus.PARTIAL
            partial_count += 1
        else:
            continue

        cr.status = new_status
        cr.evidence = finding.get("evidence", "")
        cr.recommendation = finding.get("remediation", "")
        prefilled += 1

        details.append(
            {
                "control_ref": ref,
                "title": finding.get("title", ""),
                "status": new_status.value,
                "evidence": finding.get("evidence", ""),
            }
        )

    return {
        "controls_prefilled": prefilled,
        "controls_compliant": compliant_count,
        "controls_non_compliant": non_compliant_count,
        "controls_partial": partial_count,
        "details": details,
    }
