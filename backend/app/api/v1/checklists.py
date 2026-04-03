"""Routes API checklists terrain (brief §4.2, §7.2)."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...models.user import User
from ...schemas.checklist import (
    ChecklistInstanceCreate,
    ChecklistInstanceDetail,
    ChecklistInstanceRead,
    ChecklistResponseRead,
    ChecklistResponseUpdate,
    ChecklistTemplateList,
    ChecklistTemplateRead,
)
from ...schemas.common import MessageResponse
from ...services.checklist_service import ChecklistService

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Templates ---


@router.get("/templates", response_model=list[ChecklistTemplateList])
def list_templates(
    category: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les templates de checklist disponibles."""
    return ChecklistService.list_templates(db, category=category)


@router.get("/templates/{template_id}", response_model=ChecklistTemplateRead)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère un template avec ses sections et items."""
    return ChecklistService.get_template(db, template_id)


# --- Instances ---


@router.post("/instances", response_model=ChecklistInstanceRead, status_code=201)
def create_instance(
    body: ChecklistInstanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crée une instance de checklist pour un audit."""
    return ChecklistService.create_instance(db, body, user_id=current_user.id, is_admin=current_user.role == "admin")


@router.get("/instances", response_model=list[ChecklistInstanceRead])
def list_instances(
    audit_id: int = Query(..., description="ID de l'audit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les instances de checklist pour un audit."""
    return ChecklistService.list_instances(db, audit_id, user_id=current_user.id, is_admin=current_user.role == "admin")


@router.get("/instances/{instance_id}", response_model=ChecklistInstanceDetail)
def get_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère une instance avec toutes ses réponses."""
    instance = ChecklistService.get_instance(
        db, instance_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )
    from ...models.checklist import ChecklistTemplate

    tpl = db.query(ChecklistTemplate).filter(ChecklistTemplate.id == instance.template_id).first()
    return ChecklistInstanceDetail(
        **ChecklistInstanceRead.model_validate(instance).model_dump(),
        responses=[ChecklistResponseRead.model_validate(r) for r in instance.responses],
        template_name=tpl.name if tpl else "",
    )


@router.delete("/instances/{instance_id}", response_model=MessageResponse)
def delete_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprime une instance et ses réponses."""
    msg = ChecklistService.delete_instance(
        db, instance_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )
    return MessageResponse(message=msg)


@router.post("/instances/{instance_id}/complete", response_model=ChecklistInstanceRead)
def complete_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marque une instance comme complétée."""
    return ChecklistService.complete_instance(
        db, instance_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )


# --- Réponses ---


@router.put("/instances/{instance_id}/items/{item_id}", response_model=ChecklistResponseRead)
def respond_to_item(
    instance_id: int,
    item_id: int,
    body: ChecklistResponseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Répond à un item de checklist (upsert)."""
    return ChecklistService.respond_to_item(
        db, instance_id, item_id, body, user_id=current_user.id, is_admin=current_user.role == "admin"
    )


@router.get("/instances/{instance_id}/progress")
def get_progress(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère la progression d'une checklist."""
    # Vérifier accès
    ChecklistService.get_instance(db, instance_id, user_id=current_user.id, is_admin=current_user.role == "admin")
    return ChecklistService.get_progress(db, instance_id)
