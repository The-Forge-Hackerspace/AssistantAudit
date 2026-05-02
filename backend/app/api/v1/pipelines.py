"""
Routes Pipelines — Orchestration multi-étapes scan → équipements → collectes.

TOS-13 / US009 : un pipeline est lancé de manière asynchrone via LocalTaskRunner.
Les endpoints GET permettent de suivre la progression (compteurs par étape)
en attendant les notifications WebSocket.
"""

import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import PaginationParams, get_current_auditeur, get_current_user
from ...core.task_runner import get_task_runner
from ...models.user import User
from ...schemas.common import PaginatedResponse
from ...schemas.pipeline import PipelineCreate, PipelineRead
from ...schemas.scan import PrefillResult
from ...services import pipeline_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=PipelineRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Lancer un pipeline de collecte (asynchrone)",
)
def launch_pipeline(
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """
    Crée un pipeline en statut 'pending' et planifie son exécution
    en arrière-plan. Les identifiants fournis sont transmis au job
    mais ne sont pas persistés.
    """
    pipeline = pipeline_service.create_pending_pipeline(
        db=db,
        site_id=payload.site_id,
        agent_id=payload.agent_id,
        target=payload.target,
        created_by=current_user.id,
        is_admin=current_user.role == "admin",
    )

    task_runner = get_task_runner()
    task_runner.submit(
        pipeline_service.execute_pipeline_background,
        pipeline_id=pipeline.id,
        agent_uuid=None,  # résolu depuis pipeline.agent
        current_user_id=current_user.id,
        username=payload.username,
        password=payload.password,
        private_key=payload.private_key,
        passphrase=payload.passphrase,
        use_ssl=payload.use_ssl,
        transport=payload.transport,
    )
    return pipeline


@router.get(
    "",
    response_model=PaginatedResponse[PipelineRead],
    summary="Lister les pipelines",
)
def list_pipelines(
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les pipelines accessibles à l'utilisateur (non-admin : les siens)."""
    items, total = pipeline_service.list_pipelines(
        db,
        site_id=site_id,
        skip=pagination.offset,
        limit=pagination.page_size,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=math.ceil(total / pagination.page_size) if total > 0 else 1,
    )


@router.get(
    "/{pipeline_id}",
    response_model=PipelineRead,
    summary="Détails d'un pipeline",
)
def get_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne l'état complet d'un pipeline (compteurs par étape)."""
    pipeline = pipeline_service.get_pipeline(
        db,
        pipeline_id,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline introuvable")
    return pipeline


@router.post(
    "/{pipeline_id}/prefill/{assessment_id}",
    response_model=PrefillResult,
    summary="Pré-remplir un assessment depuis les résultats du pipeline (Nmap)",
)
def prefill_from_pipeline(
    pipeline_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Mappe les ports ouverts détectés par le scan en findings non-conformes."""
    del current_user
    return pipeline_service.prefill_assessment_from_pipeline(
        db, pipeline_id, assessment_id
    )
