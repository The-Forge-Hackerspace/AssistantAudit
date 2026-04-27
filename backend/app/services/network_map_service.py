"""
Service NetworkMap : liens reseau, layouts, connexions inter-site, VLANs.
"""

from ..core.errors import BusinessRuleError, ConflictError, NotFoundError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.helpers import get_or_404, user_has_access_to_entreprise
from ..models.entreprise import Entreprise
from ..models.equipement import Equipement, VlanDefinition
from ..models.network_map import NetworkLink, NetworkMapLayout, SiteConnection
from ..models.site import Site


def _check_site_access(
    db: Session,
    site_id: int,
    user_id: int | None,
    is_admin: bool,
) -> None:
    if user_id is not None and not is_admin:
        site = db.get(Site, site_id)
        if not site or not user_has_access_to_entreprise(db, site.entreprise_id, user_id):
            raise NotFoundError("Ressource introuvable")


def _check_ent_access(
    db: Session,
    entreprise_id: int,
    user_id: int | None,
    is_admin: bool,
) -> None:
    if user_id is not None and not is_admin:
        if not user_has_access_to_entreprise(db, entreprise_id, user_id):
            raise NotFoundError("Ressource introuvable")


class NetworkMapService:
    # ── Links ────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_link_endpoints_same_site(
        db: Session,
        site_id: int,
        source_id: int,
        target_id: int,
    ) -> None:
        source = db.get(Equipement, source_id)
        target = db.get(Equipement, target_id)
        if not source or not target:
            raise NotFoundError("Équipement source/cible introuvable")
        if source.site_id != site_id or target.site_id != site_id:
            raise BusinessRuleError("Les équipements doivent appartenir au site demandé")
        if source_id == target_id:
            raise BusinessRuleError("Un lien ne peut pas relier un équipement à lui-même")

    @staticmethod
    def list_links(
        db: Session,
        site_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> list[NetworkLink]:
        get_or_404(db, Site, site_id)
        _check_site_access(db, site_id, user_id, is_admin)
        return db.query(NetworkLink).filter(NetworkLink.site_id == site_id).all()

    @staticmethod
    def get_link(
        db: Session,
        link_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> NetworkLink:
        link = get_or_404(db, NetworkLink, link_id, detail="Lien introuvable")
        _check_site_access(db, link.site_id, user_id, is_admin)
        return link

    @staticmethod
    def create_link(
        db: Session,
        data,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> NetworkLink:
        get_or_404(db, Site, data.site_id)
        _check_site_access(db, data.site_id, user_id, is_admin)
        NetworkMapService._validate_link_endpoints_same_site(
            db,
            data.site_id,
            data.source_equipement_id,
            data.target_equipement_id,
        )
        link = NetworkLink(**data.model_dump())
        db.add(link)
        db.flush()
        db.refresh(link)
        return link

    @staticmethod
    def update_link(
        db: Session,
        link_id: int,
        data,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> NetworkLink:
        link = get_or_404(db, NetworkLink, link_id, detail="Lien introuvable")
        _check_site_access(db, link.site_id, user_id, is_admin)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(link, field, value)
        db.flush()
        db.refresh(link)
        return link

    @staticmethod
    def delete_link(
        db: Session,
        link_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        link = get_or_404(db, NetworkLink, link_id, detail="Lien introuvable")
        _check_site_access(db, link.site_id, user_id, is_admin)
        db.delete(link)
        db.flush()

    # ── Site map & layout ────────────────────────────────────────────────

    @staticmethod
    def get_site_map_data(
        db: Session,
        site_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> dict:
        """Recupere equipements, liens et layout pour un site."""
        get_or_404(db, Site, site_id)
        _check_site_access(db, site_id, user_id, is_admin)
        equipements = db.query(Equipement).filter(Equipement.site_id == site_id).all()
        links = db.query(NetworkLink).filter(NetworkLink.site_id == site_id).all()
        layout = db.query(NetworkMapLayout).filter(NetworkMapLayout.site_id == site_id).first()
        layout_data = layout.layout_data if layout else {}
        return {
            "equipements": equipements,
            "links": links,
            "layout_data": layout_data,
        }

    @staticmethod
    def save_layout(
        db: Session,
        site_id: int,
        layout_data: dict,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        get_or_404(db, Site, site_id)
        _check_site_access(db, site_id, user_id, is_admin)
        layout = db.query(NetworkMapLayout).filter(NetworkMapLayout.site_id == site_id).first()
        if not layout:
            layout = NetworkMapLayout(site_id=site_id, layout_data=layout_data)
            db.add(layout)
        else:
            layout.layout_data = layout_data
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ConflictError("Conflit lors de la sauvegarde du layout")

    # ── Multi-site overview ──────────────────────────────────────────────

    @staticmethod
    def get_overview_data(
        db: Session,
        entreprise_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> dict:
        """Recupere sites et connexions pour une vue multi-site."""
        get_or_404(db, Entreprise, entreprise_id)
        _check_ent_access(db, entreprise_id, user_id, is_admin)
        sites = db.query(Site).filter(Site.entreprise_id == entreprise_id).all()
        connections = db.query(SiteConnection).filter(SiteConnection.entreprise_id == entreprise_id).all()
        return {"sites": sites, "connections": connections}

    # ── Site connections ─────────────────────────────────────────────────

    @staticmethod
    def list_connections(
        db: Session,
        entreprise_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> list[SiteConnection]:
        get_or_404(db, Entreprise, entreprise_id)
        _check_ent_access(db, entreprise_id, user_id, is_admin)
        return db.query(SiteConnection).filter(SiteConnection.entreprise_id == entreprise_id).all()

    @staticmethod
    def get_connection(
        db: Session,
        connection_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> SiteConnection:
        conn = get_or_404(db, SiteConnection, connection_id, detail="Connexion inter-site introuvable")
        _check_ent_access(db, conn.entreprise_id, user_id, is_admin)
        return conn

    @staticmethod
    def create_connection(
        db: Session,
        data,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> SiteConnection:
        get_or_404(db, Entreprise, data.entreprise_id)
        _check_ent_access(db, data.entreprise_id, user_id, is_admin)

        source_site = db.get(Site, data.source_site_id)
        target_site = db.get(Site, data.target_site_id)
        if not source_site or not target_site:
            raise NotFoundError("Site source/cible introuvable")
        if source_site.entreprise_id != data.entreprise_id or target_site.entreprise_id != data.entreprise_id:
            raise BusinessRuleError("Les deux sites doivent appartenir à la même entreprise")
        if data.source_site_id == data.target_site_id:
            raise BusinessRuleError("Une connexion inter-site doit relier deux sites différents")

        existing = (
            db.query(SiteConnection)
            .filter(
                SiteConnection.entreprise_id == data.entreprise_id,
                SiteConnection.source_site_id == data.source_site_id,
                SiteConnection.target_site_id == data.target_site_id,
                SiteConnection.link_type == data.link_type,
            )
            .first()
        )
        if existing:
            raise ConflictError("Cette connexion inter-site existe déjà")

        connection = SiteConnection(**data.model_dump())
        db.add(connection)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ConflictError("Cette connexion inter-site existe déjà (contrainte d'unicité)")
        db.refresh(connection)
        return connection

    @staticmethod
    def update_connection(
        db: Session,
        connection_id: int,
        data,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> SiteConnection:
        connection = get_or_404(
            db,
            SiteConnection,
            connection_id,
            detail="Connexion inter-site introuvable",
        )
        _check_ent_access(db, connection.entreprise_id, user_id, is_admin)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(connection, field, value)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ConflictError("Conflit de contrainte d'unicité")
        db.refresh(connection)
        return connection

    @staticmethod
    def delete_connection(
        db: Session,
        connection_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        connection = get_or_404(
            db,
            SiteConnection,
            connection_id,
            detail="Connexion inter-site introuvable",
        )
        _check_ent_access(db, connection.entreprise_id, user_id, is_admin)
        db.delete(connection)
        db.flush()

    # ── VLANs ────────────────────────────────────────────────────────────

    @staticmethod
    def list_vlans(
        db: Session,
        site_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> list[VlanDefinition]:
        get_or_404(db, Site, site_id)
        _check_site_access(db, site_id, user_id, is_admin)
        return db.query(VlanDefinition).filter(VlanDefinition.site_id == site_id).order_by(VlanDefinition.vlan_id).all()

    @staticmethod
    def get_vlan(
        db: Session,
        vlan_def_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> VlanDefinition:
        vlan = get_or_404(db, VlanDefinition, vlan_def_id, detail="Définition VLAN introuvable")
        _check_site_access(db, vlan.site_id, user_id, is_admin)
        return vlan

    @staticmethod
    def create_vlan(
        db: Session,
        data,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> VlanDefinition:
        get_or_404(db, Site, data.site_id)
        _check_site_access(db, data.site_id, user_id, is_admin)
        vlan = VlanDefinition(**data.model_dump())
        db.add(vlan)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ConflictError(f"Un VLAN avec l'ID {data.vlan_id} existe déjà pour ce site")
        db.refresh(vlan)
        return vlan

    @staticmethod
    def update_vlan(
        db: Session,
        vlan_def_id: int,
        data,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> VlanDefinition:
        vlan = get_or_404(db, VlanDefinition, vlan_def_id, detail="Définition VLAN introuvable")
        _check_site_access(db, vlan.site_id, user_id, is_admin)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(vlan, field, value)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ConflictError("Conflit : un VLAN avec cet ID existe déjà pour ce site")
        db.refresh(vlan)
        return vlan

    @staticmethod
    def delete_vlan(
        db: Session,
        vlan_def_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        vlan = get_or_404(db, VlanDefinition, vlan_def_id, detail="Définition VLAN introuvable")
        _check_site_access(db, vlan.site_id, user_id, is_admin)
        db.delete(vlan)
        db.flush()
