import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_auditeur
from ....models.user import User
from ....schemas.scan import CollectCreate, CollectResultSummary, CollectResultRead, PrefillResult
from ....schemas.common import MessageResponse
from ....services.collect_service import (
    create_pending_collect,
    execute_collect_background,
    list_collect_results,
    get_collect_result,
    delete_collect_result,
    prefill_assessment_from_collect,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/collect", response_model=CollectResultSummary)
def launch_collect(
    params: CollectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Lance une collecte d'informations système via SSH ou WinRM.
    La collecte s'exécute en arrière-plan.
    """
    if params.method not in ("ssh", "winrm"):
        raise HTTPException(400, "Méthode invalide. Utilisez 'ssh' ou 'winrm'.")

    try:
        collect = create_pending_collect(
            db=db,
            equipement_id=params.equipement_id,
            method=params.method,
            target_host=params.target_host,
            target_port=params.target_port,
            username=params.username,
            device_profile=params.device_profile,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    # Lancer la collecte en arrière-plan
    background_tasks.add_task(
        execute_collect_background,
        collect_id=collect.id,
        password=params.password,
        private_key=params.private_key,
        passphrase=params.passphrase,
        use_ssl=params.use_ssl,
        transport=params.transport,
    )

    logger.info(f"Collecte #{collect.id} lancée en background ({params.method} → {params.target_host})")
    return collect


@router.get("/collects", response_model=list[CollectResultSummary])
def list_collects(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les collectes, optionnellement filtrées par équipement."""
    return list_collect_results(
        db,
        equipement_id=equipement_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )


@router.get("/collects/{collect_id}", response_model=CollectResultRead)
def get_collect(
    collect_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Récupère le détail d'une collecte."""
    collect = get_collect_result(db, collect_id)
    if not collect:
        raise HTTPException(404, f"Collecte #{collect_id} introuvable")
    return collect


@router.delete("/collects/{collect_id}", response_model=MessageResponse)
def delete_collect(
    collect_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime une collecte."""
    if not delete_collect_result(db, collect_id):
        raise HTTPException(404, f"Collecte #{collect_id} introuvable")
    return MessageResponse(message=f"Collecte #{collect_id} supprimée")


@router.post("/collects/{collect_id}/prefill/{assessment_id}", response_model=PrefillResult)
def prefill_from_collect(
    collect_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Pré-remplit un assessment à partir des résultats d'une collecte."""
    try:
        result = prefill_assessment_from_collect(db, collect_id, assessment_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result
