"""
Routes Entreprises : CRUD.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import PaginationParams, get_current_admin, get_current_auditeur, get_current_user
from ...models.user import User
from ...schemas.common import MessageResponse, PaginatedResponse
from ...schemas.entreprise import (
    EntrepriseCreate,
    EntrepriseRead,
    EntrepriseUpdate,
)
from ...services.entreprise_service import EntrepriseService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[EntrepriseRead])
def list_entreprises(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les entreprises (paginé)"""
    items, total = EntrepriseService.list_entreprises(
        db,
        offset=pagination.offset,
        limit=pagination.page_size,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("", response_model=EntrepriseRead, status_code=status.HTTP_201_CREATED)
def create_entreprise(
    body: EntrepriseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Crée une entreprise avec ses contacts"""
    return EntrepriseService.create_entreprise(db, body, owner_id=current_user.id)


@router.get("/{entreprise_id}", response_model=EntrepriseRead)
def get_entreprise(
    entreprise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail d'une entreprise"""
    return EntrepriseService.get_entreprise(
        db,
        entreprise_id,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )


@router.put("/{entreprise_id}", response_model=EntrepriseRead)
def update_entreprise(
    entreprise_id: int,
    body: EntrepriseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Met à jour une entreprise"""
    return EntrepriseService.update_entreprise(
        db,
        entreprise_id,
        body,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )


@router.delete("/{entreprise_id}", response_model=MessageResponse)
def delete_entreprise(
    entreprise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Supprime une entreprise"""
    nom = EntrepriseService.delete_entreprise(db, entreprise_id)
    return MessageResponse(message=f"Entreprise '{nom}' supprimée")
