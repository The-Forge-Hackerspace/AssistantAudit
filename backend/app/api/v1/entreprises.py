"""
Routes Entreprises : CRUD.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, get_current_admin, PaginationParams
from ...models.entreprise import Entreprise, Contact
from ...models.user import User
from ...schemas.entreprise import (
    EntrepriseCreate,
    EntrepriseRead,
    EntrepriseUpdate,
)
from ...schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[EntrepriseRead])
def list_entreprises(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les entreprises (paginé)"""
    total = db.query(Entreprise).count()
    items = (
        db.query(Entreprise)
        .order_by(Entreprise.nom)
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
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
    _: User = Depends(get_current_auditeur),
):
    """Crée une entreprise avec ses contacts"""
    existing = db.query(Entreprise).filter(Entreprise.nom == body.nom).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"L'entreprise '{body.nom}' existe déjà")

    # Convertir les chaînes vides en None pour éviter les conflits UNIQUE
    siret = body.siret.strip() if body.siret else None
    siret = siret or None  # "" -> None

    if siret:
        dup = db.query(Entreprise).filter(Entreprise.siret == siret).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Une entreprise avec le SIRET '{siret}' existe déjà")

    entreprise = Entreprise(
        nom=body.nom,
        adresse=body.adresse or None,
        secteur_activite=body.secteur_activite or None,
        siret=siret,
        presentation_desc=body.presentation_desc or None,
        contraintes_reglementaires=body.contraintes_reglementaires or None,
    )
    db.add(entreprise)
    db.flush()

    for contact_data in body.contacts:
        contact = Contact(
            entreprise_id=entreprise.id,
            nom=contact_data.nom,
            role=contact_data.role,
            email=contact_data.email,
            telephone=contact_data.telephone,
            is_main_contact=contact_data.is_main_contact,
        )
        db.add(contact)

    db.commit()
    db.refresh(entreprise)
    return entreprise


@router.get("/{entreprise_id}", response_model=EntrepriseRead)
def get_entreprise(
    entreprise_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Détail d'une entreprise"""
    entreprise = db.get(Entreprise, entreprise_id)
    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")
    return entreprise


@router.put("/{entreprise_id}", response_model=EntrepriseRead)
def update_entreprise(
    entreprise_id: int,
    body: EntrepriseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Met à jour une entreprise"""
    entreprise = db.get(Entreprise, entreprise_id)
    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entreprise, field, value)

    db.commit()
    db.refresh(entreprise)
    return entreprise


@router.delete("/{entreprise_id}", response_model=MessageResponse)
def delete_entreprise(
    entreprise_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Supprime une entreprise"""
    entreprise = db.get(Entreprise, entreprise_id)
    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")
    db.delete(entreprise)
    db.commit()
    return MessageResponse(message=f"Entreprise '{entreprise.nom}' supprimée")
