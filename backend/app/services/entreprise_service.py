"""
Service Entreprise : CRUD pour les entreprises et contacts.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.helpers import get_or_404
from ..models.entreprise import Entreprise, Contact
from ..schemas.entreprise import EntrepriseCreate, EntrepriseUpdate


class EntrepriseService:

    @staticmethod
    def list_entreprises(
        db: Session, offset: int = 0, limit: int = 20,
    ) -> tuple[list[Entreprise], int]:
        """Liste les entreprises avec pagination."""
        total = db.query(Entreprise).count()
        items = (
            db.query(Entreprise)
            .order_by(Entreprise.nom)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def get_entreprise(db: Session, entreprise_id: int) -> Entreprise:
        """Recupere une entreprise par ID."""
        return get_or_404(db, Entreprise, entreprise_id)

    @staticmethod
    def create_entreprise(db: Session, data: EntrepriseCreate) -> Entreprise:
        """Cree une entreprise avec ses contacts. Verifie l'unicite du nom et du SIRET."""
        existing = db.query(Entreprise).filter(Entreprise.nom == data.nom).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"L'entreprise '{data.nom}' existe déjà")

        siret = data.siret.strip() if data.siret else None
        siret = siret or None

        if siret:
            dup = db.query(Entreprise).filter(Entreprise.siret == siret).first()
            if dup:
                raise HTTPException(
                    status_code=409,
                    detail=f"Une entreprise avec le SIRET '{siret}' existe déjà",
                )

        entreprise = Entreprise(
            nom=data.nom,
            adresse=data.adresse or None,
            secteur_activite=data.secteur_activite or None,
            siret=siret,
            presentation_desc=data.presentation_desc or None,
            contraintes_reglementaires=data.contraintes_reglementaires or None,
        )
        db.add(entreprise)
        db.flush()

        for contact_data in data.contacts:
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

    @staticmethod
    def update_entreprise(
        db: Session, entreprise_id: int, data: EntrepriseUpdate,
    ) -> Entreprise:
        """Met a jour une entreprise existante."""
        entreprise = get_or_404(db, Entreprise, entreprise_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entreprise, field, value)

        db.commit()
        db.refresh(entreprise)
        return entreprise

    @staticmethod
    def delete_entreprise(db: Session, entreprise_id: int) -> str:
        """Supprime une entreprise. Retourne le nom de l'entreprise supprimee."""
        entreprise = get_or_404(db, Entreprise, entreprise_id)
        nom = entreprise.nom
        db.delete(entreprise)
        db.commit()
        return nom
