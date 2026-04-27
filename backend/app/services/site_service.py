"""
Service Site : CRUD des emplacements physiques.
"""

from ..core.errors import ConflictError, NotFoundError
from sqlalchemy.orm import Session

from ..core.helpers import get_or_404, user_has_access_to_entreprise
from ..models.audit import Audit
from ..models.entreprise import Entreprise
from ..models.site import Site
from ..schemas.site import SiteCreate, SiteUpdate


class SiteService:
    @staticmethod
    def _check_entreprise_access(
        db: Session,
        entreprise_id: int,
        user_id: int | None,
        is_admin: bool,
    ) -> None:
        """Verifie l'acces a l'entreprise pour un non-admin."""
        if user_id is not None and not is_admin:
            if not user_has_access_to_entreprise(db, entreprise_id, user_id):
                raise NotFoundError("Site introuvable")

    @staticmethod
    def list_sites(
        db: Session,
        entreprise_id: int | None = None,
        offset: int = 0,
        limit: int = 20,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> tuple[list[Site], int]:
        """Liste les sites avec pagination. Non-admin voit uniquement ceux lies a ses entreprises."""
        if user_id is not None and not is_admin:
            accessible_ent_ids = (
                db.query(Audit.entreprise_id).filter(Audit.owner_id == user_id).distinct().scalar_subquery()
            )
            query = db.query(Site).filter(Site.entreprise_id.in_(accessible_ent_ids))
            if entreprise_id is not None:
                query = query.filter(Site.entreprise_id == entreprise_id)
        else:
            query = db.query(Site)
            if entreprise_id is not None:
                query = query.filter(Site.entreprise_id == entreprise_id)
        total = query.count()
        items = query.order_by(Site.nom).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def get_site(
        db: Session,
        site_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> Site:
        """Recupere un site par ID. Non-admin doit avoir acces a l'entreprise."""
        site = get_or_404(db, Site, site_id)
        SiteService._check_entreprise_access(db, site.entreprise_id, user_id, is_admin)
        return site

    @staticmethod
    def create_site(
        db: Session,
        data: SiteCreate,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> Site:
        """Cree un site. Verifie l'acces a l'entreprise, l'existence et l'unicite nom+entreprise."""
        get_or_404(db, Entreprise, data.entreprise_id)
        SiteService._check_entreprise_access(db, data.entreprise_id, user_id, is_admin)

        existing = db.query(Site).filter(Site.entreprise_id == data.entreprise_id, Site.nom == data.nom).first()
        if existing:
            raise ConflictError(f"Le site '{data.nom}' existe déjà pour cette entreprise")

        site = Site(
            nom=data.nom,
            description=data.description,
            adresse=data.adresse,
            entreprise_id=data.entreprise_id,
        )
        db.add(site)
        db.flush()
        db.refresh(site)
        return site

    @staticmethod
    def update_site(
        db: Session,
        site_id: int,
        data: SiteUpdate,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> Site:
        """Met a jour un site existant. Verifie l'acces."""
        site = get_or_404(db, Site, site_id)
        SiteService._check_entreprise_access(db, site.entreprise_id, user_id, is_admin)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(site, field, value)

        db.flush()
        db.refresh(site)
        return site

    @staticmethod
    def delete_site(db: Session, site_id: int) -> str:
        """Supprime un site. Retourne le nom du site supprime."""
        site = get_or_404(db, Site, site_id)
        nom = site.nom
        db.delete(site)
        db.flush()
        return nom
