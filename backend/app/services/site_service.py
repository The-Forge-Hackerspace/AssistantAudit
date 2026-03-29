"""
Service Site : CRUD des emplacements physiques.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.helpers import get_or_404
from ..models.entreprise import Entreprise
from ..models.site import Site
from ..schemas.site import SiteCreate, SiteUpdate


class SiteService:

    @staticmethod
    def list_sites(
        db: Session,
        entreprise_id: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Site], int]:
        """Liste les sites avec pagination et filtre optionnel par entreprise."""
        query = db.query(Site)
        if entreprise_id is not None:
            query = query.filter(Site.entreprise_id == entreprise_id)
        total = query.count()
        items = query.order_by(Site.nom).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def get_site(db: Session, site_id: int) -> Site:
        """Recupere un site par ID."""
        return get_or_404(db, Site, site_id)

    @staticmethod
    def create_site(db: Session, data: SiteCreate) -> Site:
        """Cree un site. Verifie l'existence de l'entreprise et l'unicite nom+entreprise."""
        get_or_404(db, Entreprise, data.entreprise_id)

        existing = (
            db.query(Site)
            .filter(Site.entreprise_id == data.entreprise_id, Site.nom == data.nom)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Le site '{data.nom}' existe déjà pour cette entreprise",
            )

        site = Site(
            nom=data.nom,
            description=data.description,
            adresse=data.adresse,
            entreprise_id=data.entreprise_id,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return site

    @staticmethod
    def update_site(db: Session, site_id: int, data: SiteUpdate) -> Site:
        """Met a jour un site existant."""
        site = get_or_404(db, Site, site_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(site, field, value)

        db.commit()
        db.refresh(site)
        return site

    @staticmethod
    def delete_site(db: Session, site_id: int) -> str:
        """Supprime un site. Retourne le nom du site supprime."""
        site = get_or_404(db, Site, site_id)
        nom = site.nom
        db.delete(site)
        db.commit()
        return nom
