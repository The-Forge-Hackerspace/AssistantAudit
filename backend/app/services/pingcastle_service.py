"""
Service PingCastle — Orchestration des audits PingCastle,
persistance des résultats et pré-remplissage des contrôles d'audit AD.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.pingcastle_result import PingCastleResult, PingCastleStatus
from ..models.equipement import Equipement
from ..models.assessment import Assessment, ControlResult, ComplianceStatus
from ..core.config import get_settings
from ..core.database import SessionLocal
from ..tools.pingcastle_runner.runner import PingCastleRunner

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Mapping PingCastle → contrôles du framework AD
# ══════════════════════════════════════════════════════════════
# TODO: Enrichir ce mapping avec les correspondances fines entre
# les catégories/règles PingCastle et les contrôles du framework
# active_directory_audit.yaml. Un fichier YAML de mapping dédié
# pourrait être ajouté dans frameworks/ pour plus de flexibilité.

PINGCASTLE_CONTROL_MAP: list[dict] = [
    {
        "control_ref": "AD-001",
        "pingcastle_ref": "PC-PRIV",
        "description": "Comptes privilégiés – score PingCastle",
    },
    {
        "control_ref": "AD-002",
        "pingcastle_ref": "PC-STALE",
        "description": "Objets obsolètes – score PingCastle",
    },
    {
        "control_ref": "AD-010",
        "pingcastle_ref": "PC-TRUST",
        "description": "Relations d'approbation – score PingCastle",
    },
    {
        "control_ref": "AD-012",
        "pingcastle_ref": "PC-ANOMALY",
        "description": "Anomalies – score PingCastle",
    },
    {
        "control_ref": "AD-020",
        "pingcastle_ref": "PC-GLOBAL",
        "description": "Score global PingCastle",
    },
]


def create_pending_pingcastle(
    db: Session,
    equipement_id: Optional[int],
    target_host: str,
    domain: str,
    username: str,
) -> PingCastleResult:
    """Crée un enregistrement PingCastle en statut 'running'."""
    if equipement_id:
        equip = db.get(Equipement, equipement_id)
        if not equip:
            raise ValueError(f"Équipement #{equipement_id} introuvable")

    result = PingCastleResult(
        equipement_id=equipement_id,
        status=PingCastleStatus.RUNNING,
        target_host=target_host,
        domain=domain,
        username=username,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def execute_pingcastle_background(
    result_id: int,
    password: str,
) -> None:
    """
    Exécute l'audit PingCastle en arrière-plan.
    Appelé dans un thread séparé.
    """
    db = SessionLocal()
    try:
        pc_result = db.get(PingCastleResult, result_id)
        if not pc_result:
            logger.error(f"[PINGCASTLE] Résultat #{result_id} introuvable en BDD")
            return

        settings = get_settings()
        start_time = time.time()

        runner = PingCastleRunner(
            pingcastle_path=settings.PINGCASTLE_PATH,
            target_host=pc_result.target_host,
            domain=pc_result.domain,
            username=pc_result.username,
            password=password,
            output_dir=settings.PINGCASTLE_OUTPUT_DIR,
            timeout=settings.PINGCASTLE_TIMEOUT,
        )

        run_result = runner.run_healthcheck()
        elapsed = int(time.time() - start_time)

        # Persister les résultats
        if run_result.success:
            pc_result.status = PingCastleStatus.SUCCESS
            pc_result.global_score = run_result.global_score
            pc_result.stale_objects_score = run_result.stale_objects_score
            pc_result.privileged_accounts_score = run_result.privileged_accounts_score
            pc_result.trust_score = run_result.trust_score
            pc_result.anomaly_score = run_result.anomaly_score
            pc_result.maturity_level = run_result.maturity_level
            pc_result.risk_rules = run_result.risk_rules
            pc_result.domain_info = run_result.domain_info
            pc_result.raw_report = run_result.raw_report
            pc_result.findings = run_result.findings
            pc_result.summary = run_result.summary
            pc_result.report_html_path = run_result.report_html_path
        else:
            pc_result.status = PingCastleStatus.FAILED
            pc_result.error_message = run_result.error

        pc_result.completed_at = datetime.now(timezone.utc)
        pc_result.duration_seconds = elapsed
        db.commit()

        logger.info(
            f"[PINGCASTLE] Audit #{result_id} terminé en {elapsed}s "
            f"(status={pc_result.status.value}, score={pc_result.global_score})"
        )

    except Exception as e:
        logger.exception(f"[PINGCASTLE] Erreur fatale audit #{result_id}")
        try:
            pc_result = db.get(PingCastleResult, result_id)
            if pc_result:
                pc_result.status = PingCastleStatus.FAILED
                pc_result.error_message = str(e)
                pc_result.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def list_pingcastle_results(
    db: Session,
    equipement_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
) -> list[PingCastleResult]:
    """Liste les audits PingCastle, optionnellement filtrés par équipement."""
    q = db.query(PingCastleResult)
    if equipement_id:
        q = q.filter(PingCastleResult.equipement_id == equipement_id)
    return q.order_by(PingCastleResult.created_at.desc()).offset(skip).limit(limit).all()


def get_pingcastle_result(db: Session, result_id: int) -> Optional[PingCastleResult]:
    """Récupère le détail d'un audit PingCastle."""
    return db.get(PingCastleResult, result_id)


def delete_pingcastle_result(db: Session, result_id: int) -> bool:
    """Supprime un audit PingCastle."""
    result = db.get(PingCastleResult, result_id)
    if not result:
        return False
    db.delete(result)
    db.commit()
    return True


def prefill_assessment_from_pingcastle(
    db: Session,
    result_id: int,
    assessment_id: int,
) -> dict:
    """
    Pré-remplit un assessment à partir des résultats d'un audit PingCastle.
    Mappe les findings PingCastle vers les contrôles du framework AD.
    """
    pc_result = db.get(PingCastleResult, result_id)
    if not pc_result:
        raise ValueError(f"Audit PingCastle #{result_id} introuvable")
    if pc_result.status != PingCastleStatus.SUCCESS:
        raise ValueError(f"Audit PingCastle #{result_id} n'est pas terminé avec succès")

    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise ValueError(f"Assessment #{assessment_id} introuvable")

    # Charger les control results de l'assessment
    control_results = (
        db.query(ControlResult)
        .filter(ControlResult.assessment_id == assessment_id)
        .all()
    )

    # Index par ref_id
    cr_by_ref: dict[str, ControlResult] = {}
    for cr in control_results:
        if cr.control and cr.control.ref_id:
            cr_by_ref[cr.control.ref_id] = cr

    # Index findings PingCastle par control_ref
    findings_by_ref: dict[str, dict] = {}
    if pc_result.findings:
        for f in pc_result.findings:
            findings_by_ref[f.get("control_ref", "")] = f

    prefilled = 0
    compliant_count = 0
    non_compliant_count = 0
    partial_count = 0
    details = []

    for mapping in PINGCASTLE_CONTROL_MAP:
        ad_ref = mapping["control_ref"]
        pc_ref = mapping["pingcastle_ref"]

        finding = findings_by_ref.get(pc_ref)
        cr = cr_by_ref.get(ad_ref)

        if not finding or not cr:
            continue

        finding_status = finding.get("status", "info")

        # Ne pas prefill les "info"
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
            new_status = ComplianceStatus.PARTIALLY_COMPLIANT
            partial_count += 1
        else:
            continue

        cr.status = new_status
        cr.evidence = (
            f"[PingCastle] {finding.get('evidence', '')} | "
            f"{finding.get('description', '')}"
        )
        cr.remediation_note = finding.get("remediation", "")
        prefilled += 1

        details.append({
            "control_ref": ad_ref,
            "pingcastle_ref": pc_ref,
            "title": finding.get("title", ""),
            "status": new_status.value,
            "evidence": finding.get("evidence", ""),
        })

    db.commit()

    return {
        "controls_prefilled": prefilled,
        "controls_compliant": compliant_count,
        "controls_non_compliant": non_compliant_count,
        "controls_partial": partial_count,
        "details": details,
    }
