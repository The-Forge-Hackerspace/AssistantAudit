import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_auditeur
from ....models.user import User
from ....schemas.scan import PingCastleCreate, PingCastleResultSummary, PingCastleResultRead, PrefillResult
from ....schemas.common import MessageResponse
from ....core.task_runner import get_task_runner
from ....services.pingcastle_service import (
    create_pending_pingcastle,
    execute_pingcastle_background,
    list_pingcastle_results,
    get_pingcastle_result,
    delete_pingcastle_result,
    prefill_assessment_from_pingcastle,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/pingcastle", response_model=PingCastleResultSummary)
def launch_pingcastle(
    params: PingCastleCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Lance un audit PingCastle (healthcheck) sur un contrôleur de domaine AD.
    L'audit s'exécute en arrière-plan.
    """
    try:
        pc_result = create_pending_pingcastle(
            db=db,
            equipement_id=params.equipement_id,
            target_host=params.target_host,
            domain=params.domain,
            username=params.username,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    task_runner = get_task_runner()
    task_runner.submit(
        execute_pingcastle_background,
        result_id=pc_result.id,
        password=params.password,
    )

    logger.info(
        f"PingCastle #{pc_result.id} lancé en background "
        f"(DC={params.target_host}, domain={params.domain})"
    )
    return pc_result


@router.get("/pingcastle-results", response_model=list[PingCastleResultSummary])
def list_pingcastle(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les audits PingCastle, optionnellement filtrés par équipement."""
    return list_pingcastle_results(
        db,
        equipement_id=equipement_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )


@router.get("/pingcastle-results/{result_id}", response_model=PingCastleResultRead)
def get_pingcastle(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Récupère le détail d'un audit PingCastle."""
    result = get_pingcastle_result(db, result_id)
    if not result:
        raise HTTPException(404, f"Audit PingCastle #{result_id} introuvable")
    return result


@router.delete("/pingcastle-results/{result_id}", response_model=MessageResponse)
def delete_pingcastle(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime un audit PingCastle."""
    if not delete_pingcastle_result(db, result_id):
        raise HTTPException(404, f"Audit PingCastle #{result_id} introuvable")
    return MessageResponse(message=f"Audit PingCastle #{result_id} supprimé")


@router.post("/pingcastle-results/{result_id}/prefill/{assessment_id}", response_model=PrefillResult)
def prefill_from_pingcastle(
    result_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Pré-remplit un assessment à partir des résultats d'un audit PingCastle."""
    try:
        result = prefill_assessment_from_pingcastle(db, result_id, assessment_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result
