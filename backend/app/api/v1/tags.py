"""Routes API pour le système de tags (brief §5)."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import PaginationParams, get_current_user
from ...models.user import User
from ...schemas.common import MessageResponse, PaginatedResponse
from ...schemas.tag import (
    TagAssociationCreate,
    TagAssociationRead,
    TagCreate,
    TagRead,
    TagUpdate,
)
from ...services.tag_service import TagService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=PaginatedResponse[TagRead])
def list_tags(
    audit_id: int | None = Query(None, description="Filtrer par audit"),
    scope: str | None = Query(None, pattern="^(global|audit)$"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les tags visibles par l'utilisateur."""
    tags, total = TagService.list_tags(
        db,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
        audit_id=audit_id,
        scope=scope,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse(
        items=[TagRead.model_validate(t) for t in tags],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("", response_model=TagRead, status_code=201)
def create_tag(
    body: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crée un tag (global ou lié à un audit)."""
    tag = TagService.create_tag(db, body, user_id=current_user.id, is_admin=current_user.role == "admin")
    return TagRead.model_validate(tag)


@router.post("/associate", response_model=TagAssociationRead, status_code=201)
def associate_tag(
    body: TagAssociationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Associe un tag à une entité (équipement, finding, etc.)."""
    assoc = TagService.associate_tag(
        db,
        body.tag_id,
        body.taggable_type,
        body.taggable_id,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return TagAssociationRead.model_validate(assoc)


@router.delete("/associate", response_model=MessageResponse)
def dissociate_tag(
    tag_id: int = Query(...),
    taggable_type: str = Query(...),
    taggable_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retire un tag d'une entité."""
    TagService.dissociate_tag(
        db,
        tag_id,
        taggable_type,
        taggable_id,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return MessageResponse(message="Tag dissocié")


@router.get("/entity/{taggable_type}/{taggable_id}", response_model=list[TagRead])
def get_entity_tags(
    taggable_type: str,
    taggable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère tous les tags d'une entité."""
    tags = TagService.get_tags_for_entity(db, taggable_type, taggable_id)
    return [TagRead.model_validate(t) for t in tags]


@router.put("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: int,
    body: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Met à jour un tag."""
    tag = TagService.update_tag(
        db,
        tag_id,
        body,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return TagRead.model_validate(tag)


@router.delete("/{tag_id}", response_model=MessageResponse)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprime un tag et toutes ses associations."""
    name = TagService.delete_tag(
        db,
        tag_id,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return MessageResponse(message=f"Tag '{name}' supprimé")
