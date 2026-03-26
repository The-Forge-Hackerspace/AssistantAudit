import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_auditeur
from ....models.user import User
from ....schemas.scan import ADAuditCreate, ADAuditResultSummary, ADAuditResultRead, PrefillResult
from ....schemas.common import MessageResponse
from ....services.ad_audit_service import (
    create_pending_ad_audit,
    execute_ad_audit_background,
    list_ad_audit_results,
    get_ad_audit_result,
    delete_ad_audit_result,
    prefill_assessment_from_ad_audit,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ad-audit", response_model=ADAuditResultSummary)
def launch_ad_audit(
    params: ADAuditCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Lance un audit Active Directory via LDAP.
    L'audit s'exécute en arrière-plan.
    """
    try:
        audit = create_pending_ad_audit(
            db=db,
            equipement_id=params.equipement_id,
            target_host=params.target_host,
            target_port=params.target_port,
            username=params.username,
            domain=params.domain,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    background_tasks.add_task(
        execute_ad_audit_background,
        audit_id=audit.id,
        password=params.password,
        use_ssl=params.use_ssl,
        auth_method=params.auth_method,
    )

    logger.info(
        f"AD Audit #{audit.id} lancé en background "
        f"(LDAP → {params.target_host}:{params.target_port})"
    )
    return audit


@router.get("/ad-audits", response_model=list[ADAuditResultSummary])
def list_ad_audits(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les audits AD, optionnellement filtrés par équipement."""
    return list_ad_audit_results(
        db,
        equipement_id=equipement_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )


@router.get("/ad-audits/{audit_id}", response_model=ADAuditResultRead)
def get_ad_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Récupère le détail d'un audit AD."""
    audit = get_ad_audit_result(db, audit_id)
    if not audit:
        raise HTTPException(404, f"Audit AD #{audit_id} introuvable")
    return audit


@router.delete("/ad-audits/{audit_id}", response_model=MessageResponse)
def delete_ad_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime un audit AD."""
    if not delete_ad_audit_result(db, audit_id):
        raise HTTPException(404, f"Audit AD #{audit_id} introuvable")
    return MessageResponse(message=f"Audit AD #{audit_id} supprimé")


@router.post("/ad-audits/{audit_id}/prefill/{assessment_id}", response_model=PrefillResult)
def prefill_from_ad_audit(
    audit_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Pré-remplit un assessment à partir des résultats d'un audit AD."""
    try:
        result = prefill_assessment_from_ad_audit(db, audit_id, assessment_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result
