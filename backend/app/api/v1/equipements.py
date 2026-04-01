"""
Routes Equipements : CRUD des assets d'infrastructure.

Gère les 3 sous-types STI (réseau, serveur, firewall) via un champ type_equipement.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, get_current_admin, PaginationParams
from ...models.equipement import EQUIPEMENT_TYPE_VALUES
from ...models.user import User
from ...schemas.equipement import (
    EquipementCreate,
    EquipementRead,
    EquipementSummary,
    EquipementUpdate,
)
from ...schemas.common import PaginatedResponse, MessageResponse
from ...services.equipement_service import EquipementService, equipement_to_read

router = APIRouter()

TYPE_PATTERN = "^(" + "|".join(EQUIPEMENT_TYPE_VALUES) + ")$"


@router.get("", response_model=PaginatedResponse[EquipementSummary])
def list_equipements(
    site_id: Optional[int] = None,
    entreprise_id: Optional[int] = None,
    type_equipement: Optional[str] = Query(default=None, pattern=TYPE_PATTERN),
    status_audit: Optional[str] = Query(default=None, pattern=r"^(A_AUDITER|EN_COURS|CONFORME|NON_CONFORME)$"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les équipements (filtrable par site, entreprise, type, statut)"""
    items, total = EquipementService.list_equipements(
        db,
        site_id=site_id,
        entreprise_id=entreprise_id,
        type_equipement=type_equipement,
        status_audit=status_audit,
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


@router.post("", response_model=EquipementRead, status_code=status.HTTP_201_CREATED)
def create_equipement(
    body: EquipementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Crée un nouvel équipement dans un site"""
    equipement = EquipementService.create_equipement(
        db, body, user_id=current_user.id, is_admin=current_user.role == "admin",
    )
    return equipement_to_read(equipement)


@router.get("/{equipement_id}", response_model=EquipementRead)
def get_equipement(
    equipement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail d'un équipement"""
    equipement = EquipementService.get_equipement(
        db, equipement_id, user_id=current_user.id, is_admin=current_user.role == "admin",
    )
    return equipement_to_read(equipement)


@router.put("/{equipement_id}", response_model=EquipementRead)
def update_equipement(
    equipement_id: int,
    body: EquipementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Modifie un équipement"""
    equipement = EquipementService.update_equipement(
        db, equipement_id, body, user_id=current_user.id, is_admin=current_user.role == "admin",
    )
    return equipement_to_read(equipement)


@router.delete("/{equipement_id}", response_model=MessageResponse)
def delete_equipement(
    equipement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Supprime un équipement et ses assessments associés"""
    ip = EquipementService.delete_equipement(db, equipement_id)
    return MessageResponse(message=f"Équipement {ip} supprimé")
