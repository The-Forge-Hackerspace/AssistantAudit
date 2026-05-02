"""Orchestration des collectes : création, dispatch agent, hydratation, CRUD et pré-remplissage."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ...core.errors import BusinessRuleError, NotFoundError
from ...models.agent_task import AgentTask
from ...models.assessment import Assessment, ComplianceStatus, ControlResult
from ...models.collect_result import CollectMethod, CollectResult, CollectStatus
from ...models.equipement import Equipement, EquipementServeur
from ...models.site import Site
from .evaluators import (
    LINUX_CONTROL_MAP,
    WINDOWS_CONTROL_MAP,
    _evaluate_linux_check,
    _evaluate_windows_check,
)
from .findings import _analyze_collect_findings, _generate_summary

logger = logging.getLogger(__name__)


def create_pending_collect(
    db: Session,
    equipement_id: int,
    method: str,
    target_host: str,
    target_port: int,
    username: str,
    device_profile: str = "linux_server",
) -> CollectResult:
    """Crée un enregistrement de collecte en statut 'running'."""
    equipement = db.get(Equipement, equipement_id)
    if not equipement:
        raise NotFoundError(f"Équipement {equipement_id} introuvable")

    collect = CollectResult(
        equipement_id=equipement_id,
        method=CollectMethod(method),
        status=CollectStatus.RUNNING,
        target_host=target_host,
        target_port=target_port,
        username=username,
        device_profile=device_profile,
    )
    db.add(collect)
    db.flush()
    db.refresh(collect)
    return collect


def dispatch_collect_to_agent(
    db: Session,
    collect_id: int,
    agent_uuid: str,
    current_user_id: int,
    *,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
    audit_id: Optional[int] = None,
) -> AgentTask:
    """Dispatche la collecte vers un agent on-prem via task_service.

    La collecte reste en statut 'running' jusqu'a reception du task_result
    (hydrate_collect_from_agent_result depuis le handler WebSocket).
    """
    from .. import task_service

    collect = db.get(CollectResult, collect_id)
    if collect is None:
        raise NotFoundError(f"CollectResult #{collect_id} introuvable")

    if collect.method == CollectMethod.SSH:
        tool = "ssh-collect"
        parameters: dict = {
            "host": collect.target_host,
            "port": collect.target_port,
            "username": collect.username,
            "device_profile": collect.device_profile or "linux_server",
        }
        if password:
            parameters["password"] = password
        if private_key:
            parameters["private_key"] = private_key
        if passphrase:
            parameters["passphrase"] = passphrase
    elif collect.method == CollectMethod.WINRM:
        tool = "winrm-collect"
        parameters = {
            "host": collect.target_host,
            "port": collect.target_port,
            "username": collect.username,
            "password": password or "",
            "use_ssl": use_ssl,
            "transport": transport,
        }
    else:
        raise BusinessRuleError(f"Methode de collecte non supportee : {collect.method}")

    task = task_service.dispatch_task(
        db=db,
        agent_uuid=agent_uuid,
        tool=tool,
        parameters=parameters,
        current_user_id=current_user_id,
        audit_id=audit_id,
    )
    collect.agent_task_id = task.id
    db.flush()
    logger.info(
        "Collecte #%s dispatchee vers agent (task_uuid=%s, tool=%s)",
        collect_id,
        task.task_uuid,
        tool,
    )
    return task


def dispatch_collect_and_commit(
    db: Session,
    collect_id: int,
    agent_uuid: str,
    current_user_id: int,
    *,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
    audit_id: Optional[int] = None,
) -> AgentTask:
    """Dispatche une collecte vers un agent puis commit la transaction.

    Rollback automatique sur PermissionError / ValueError pour que le routeur
    puisse retourner 403 ou 400 sans laisser la session dans un etat sale.
    """
    try:
        task = dispatch_collect_to_agent(
            db=db,
            collect_id=collect_id,
            agent_uuid=agent_uuid,
            current_user_id=current_user_id,
            password=password,
            private_key=private_key,
            passphrase=passphrase,
            use_ssl=use_ssl,
            transport=transport,
            audit_id=audit_id,
        )
        db.commit()
        return task
    except Exception:
        db.rollback()
        raise


def hydrate_collect_from_agent_result(
    db: Session,
    collect: CollectResult,
    result_summary: Optional[dict],
    error_message: Optional[str],
) -> None:
    """Applique le resultat renvoye par l'agent sur un CollectResult.

    Appele par le handler WebSocket task_result. result_summary est la sortie
    de SshCollectorTool / WinRMCollectorTool (asdict(SSHCollectResult|WinRMCollectResult)).
    """
    now = datetime.now(timezone.utc)
    start = collect.created_at
    if start is not None:
        start_tz = start if start.tzinfo is not None else start.replace(tzinfo=timezone.utc)
        collect.duration_seconds = max(0, int((now - start_tz).total_seconds()))
    collect.completed_at = now

    data = result_summary or {}
    agent_error = data.get("error") if isinstance(data, dict) else None

    is_failure = bool(error_message) or (
        isinstance(data, dict)
        and (data.get("success") is False or bool(agent_error))
    )
    if is_failure:
        collect.status = CollectStatus.FAILED
        collect.error_message = error_message or agent_error or "Collecte agent echouee"
        return

    collect.status = CollectStatus.SUCCESS
    collect.hostname_collected = data.get("hostname") or None
    collect.os_info = data.get("os_info") or {}
    collect.network = data.get("network") or {}
    collect.users = data.get("users") or {}
    collect.services = data.get("services") or {}
    collect.security = data.get("security") or {}
    collect.storage = data.get("storage") or {}
    collect.updates = data.get("updates") or {}

    findings = _analyze_collect_findings(collect)
    collect.findings = findings
    collect.summary = _generate_summary(collect, findings)

    eq = db.get(Equipement, collect.equipement_id)
    if eq is None:
        return
    if collect.hostname_collected and not eq.hostname:
        eq.hostname = collect.hostname_collected
    os_info = collect.os_info or {}
    if collect.method == CollectMethod.WINRM:
        os_name = os_info.get("caption", "")
    else:
        os_name = os_info.get("distro", "")
    if os_name and not eq.os_detected:
        eq.os_detected = os_name

    if isinstance(eq, EquipementServeur):
        if collect.method == CollectMethod.WINRM:
            detail = f"{os_info.get('caption', '')} Build {os_info.get('build', '')}"
        else:
            detail = (
                f"{os_info.get('distro', '')} {os_info.get('version_id', '')} "
                f"(kernel {os_info.get('kernel', '')})"
            )
        if not eq.os_version_detail:
            eq.os_version_detail = detail


def _check_equip_access(db: Session, equipement_id: int, user_id: int | None, is_admin: bool) -> bool:
    """Verifie l'acces a un equipement via la chaine Equipement → Site → Entreprise."""
    if user_id is None or is_admin:
        return True
    from ...core.helpers import user_has_access_to_entreprise

    equip = db.get(Equipement, equipement_id)
    if not equip:
        return False
    site = db.get(Site, equip.site_id)
    if not site:
        return False
    return user_has_access_to_entreprise(db, site.entreprise_id, user_id)


def list_collect_results(
    db: Session,
    equipement_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    is_admin: bool = False,
) -> list[CollectResult]:
    """Liste les collectes, optionnellement filtrées par équipement et ownership."""
    q = db.query(CollectResult)
    if equipement_id:
        q = q.filter(CollectResult.equipement_id == equipement_id)
    if user_id is not None and not is_admin:
        from ...models.audit import Audit

        accessible_ent_ids = (
            db.query(Audit.entreprise_id).filter(Audit.owner_id == user_id).distinct().scalar_subquery()
        )
        q = (
            q.join(Equipement, CollectResult.equipement_id == Equipement.id)
            .join(Site, Equipement.site_id == Site.id)
            .filter(Site.entreprise_id.in_(accessible_ent_ids))
        )
    return q.order_by(CollectResult.created_at.desc()).offset(skip).limit(limit).all()


def get_collect_result(
    db: Session,
    collect_id: int,
    user_id: int | None = None,
    is_admin: bool = False,
) -> Optional[CollectResult]:
    """Récupère une collecte par ID. Vérifie ownership."""
    collect = db.get(CollectResult, collect_id)
    if collect and not _check_equip_access(db, collect.equipement_id, user_id, is_admin):
        return None
    return collect


def delete_collect_result(
    db: Session,
    collect_id: int,
    user_id: int | None = None,
    is_admin: bool = False,
) -> bool:
    """Supprime une collecte. Vérifie ownership."""
    collect = db.get(CollectResult, collect_id)
    if not collect:
        return False
    if not _check_equip_access(db, collect.equipement_id, user_id, is_admin):
        return False
    db.delete(collect)
    db.flush()
    return True


def prefill_assessment_from_collect(
    db: Session,
    collect_id: int,
    assessment_id: int,
) -> dict:
    """
    Pré-remplit les contrôles d'un assessment à partir d'une collecte.

    Logique :
    - Pour chaque mapping (check → control_ref), on évalue le check
    - Si passe → compliant
    - Si échoue → non_compliant avec preuve détaillée
    """
    collect = db.get(CollectResult, collect_id)
    if not collect:
        raise NotFoundError(f"Collecte #{collect_id} introuvable")
    if collect.status != CollectStatus.SUCCESS:
        raise BusinessRuleError(f"Collecte #{collect_id} n'est pas en succès (status={collect.status.value})")

    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise NotFoundError(f"Assessment #{assessment_id} introuvable")

    # Déterminer le jeu de mappings
    is_windows = collect.method == CollectMethod.WINRM
    control_map = WINDOWS_CONTROL_MAP if is_windows else LINUX_CONTROL_MAP

    # Récupérer les control_results de l'assessment
    control_results = db.query(ControlResult).filter(ControlResult.assessment_id == assessment_id).all()
    ref_to_result: dict[str, ControlResult] = {}
    for cr in control_results:
        if cr.control and cr.control.ref_id:
            ref_to_result[cr.control.ref_id] = cr

    prefilled = 0
    compliant_count = 0
    non_compliant_count = 0
    details = []

    for mapping in control_map:
        control_ref = mapping["control_ref"]
        cr = ref_to_result.get(control_ref)
        if not cr:
            continue

        check_name = mapping["check"]
        if is_windows:
            passed, detail = _evaluate_windows_check(check_name, collect)
        else:
            passed, detail = _evaluate_linux_check(check_name, collect)

        source = "WinRM" if is_windows else "SSH"

        if passed:
            cr.status = ComplianceStatus.COMPLIANT
            cr.evidence = f"[Collecte {source}] {mapping['evidence_pass']}\n\nDétail : {detail}"
            cr.auto_result = f"Collecte {source}: conforme"
            compliant_count += 1
            status_label = "compliant"
        else:
            cr.status = ComplianceStatus.NON_COMPLIANT
            cr.evidence = f"[Collecte {source}] {mapping['evidence_fail']}\n\nDétail : {detail}"
            cr.auto_result = f"Collecte {source}: non conforme"
            non_compliant_count += 1
            status_label = "non_compliant"

        cr.is_auto_assessed = True
        cr.assessed_at = datetime.now(timezone.utc)
        cr.assessed_by = f"collect_{source.lower()}"
        prefilled += 1

        details.append(
            {
                "control_ref": control_ref,
                "control_title": cr.control.title if cr.control else "",
                "status": status_label,
                "findings_count": 0 if passed else 1,
            }
        )

    db.flush()
    logger.info(
        f"Pré-remplissage collecte #{collect_id}: {prefilled} contrôles "
        f"({compliant_count} conformes, {non_compliant_count} non-conformes)"
    )

    return {
        "controls_prefilled": prefilled,
        "controls_compliant": compliant_count,
        "controls_non_compliant": non_compliant_count,
        "controls_partial": 0,
        "details": details,
    }
