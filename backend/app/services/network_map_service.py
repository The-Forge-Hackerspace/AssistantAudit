"""
Service NetworkMap : liens reseau, layouts, connexions inter-site, VLANs.
"""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.helpers import get_or_404
from ..models.entreprise import Entreprise
from ..models.equipement import Equipement, VlanDefinition
from ..models.network_map import NetworkLink, NetworkMapLayout, SiteConnection
from ..models.site import Site


class NetworkMapService:

    # ── Links ────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_link_endpoints_same_site(
        db: Session, site_id: int, source_id: int, target_id: int,
    ) -> None:
        source = db.get(Equipement, source_id)
        target = db.get(Equipement, target_id)
        if not source or not target:
            raise HTTPException(status_code=404, detail="Équipement source/cible introuvable")
        if source.site_id != site_id or target.site_id != site_id:
            raise HTTPException(status_code=400, detail="Les équipements doivent appartenir au site demandé")
        if source_id == target_id:
            raise HTTPException(status_code=400, detail="Un lien ne peut pas relier un équipement à lui-même")

    @staticmethod
    def list_links(db: Session, site_id: int) -> list[NetworkLink]:
        get_or_404(db, Site, site_id)
        return db.query(NetworkLink).filter(NetworkLink.site_id == site_id).all()

    @staticmethod
    def get_link(db: Session, link_id: int) -> NetworkLink:
        return get_or_404(db, NetworkLink, link_id, detail="Lien introuvable")

    @staticmethod
    def create_link(db: Session, data) -> NetworkLink:
        get_or_404(db, Site, data.site_id)
        NetworkMapService._validate_link_endpoints_same_site(
            db, data.site_id, data.source_equipement_id, data.target_equipement_id,
        )
        link = NetworkLink(**data.model_dump())
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def update_link(db: Session, link_id: int, data) -> NetworkLink:
        link = get_or_404(db, NetworkLink, link_id, detail="Lien introuvable")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(link, field, value)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def delete_link(db: Session, link_id: int) -> None:
        link = get_or_404(db, NetworkLink, link_id, detail="Lien introuvable")
        db.delete(link)
        db.commit()

    # ── Site map & layout ────────────────────────────────────────────────

    @staticmethod
    def get_site_map_data(db: Session, site_id: int) -> dict:
        """Recupere equipements, liens et layout pour un site."""
        get_or_404(db, Site, site_id)
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
    def save_layout(db: Session, site_id: int, layout_data: dict) -> None:
        get_or_404(db, Site, site_id)
        layout = db.query(NetworkMapLayout).filter(NetworkMapLayout.site_id == site_id).first()
        if not layout:
            layout = NetworkMapLayout(site_id=site_id, layout_data=layout_data)
            db.add(layout)
        else:
            layout.layout_data = layout_data
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Conflit lors de la sauvegarde du layout")

    # ── Multi-site overview ──────────────────────────────────────────────

    @staticmethod
    def get_overview_data(db: Session, entreprise_id: int) -> dict:
        """Recupere sites et connexions pour une vue multi-site."""
        get_or_404(db, Entreprise, entreprise_id)
        sites = db.query(Site).filter(Site.entreprise_id == entreprise_id).all()
        connections = db.query(SiteConnection).filter(
            SiteConnection.entreprise_id == entreprise_id
        ).all()
        return {"sites": sites, "connections": connections}

    # ── Site connections ─────────────────────────────────────────────────

    @staticmethod
    def list_connections(db: Session, entreprise_id: int) -> list[SiteConnection]:
        get_or_404(db, Entreprise, entreprise_id)
        return db.query(SiteConnection).filter(
            SiteConnection.entreprise_id == entreprise_id
        ).all()

    @staticmethod
    def get_connection(db: Session, connection_id: int) -> SiteConnection:
        return get_or_404(db, SiteConnection, connection_id, detail="Connexion inter-site introuvable")

    @staticmethod
    def create_connection(db: Session, data) -> SiteConnection:
        get_or_404(db, Entreprise, data.entreprise_id)

        source_site = db.get(Site, data.source_site_id)
        target_site = db.get(Site, data.target_site_id)
        if not source_site or not target_site:
            raise HTTPException(status_code=404, detail="Site source/cible introuvable")
        if source_site.entreprise_id != data.entreprise_id or target_site.entreprise_id != data.entreprise_id:
            raise HTTPException(status_code=400, detail="Les deux sites doivent appartenir à la même entreprise")
        if data.source_site_id == data.target_site_id:
            raise HTTPException(status_code=400, detail="Une connexion inter-site doit relier deux sites différents")

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
            raise HTTPException(status_code=409, detail="Cette connexion inter-site existe déjà")

        connection = SiteConnection(**data.model_dump())
        db.add(connection)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Cette connexion inter-site existe déjà (contrainte d'unicité)")
        db.refresh(connection)
        return connection

    @staticmethod
    def update_connection(db: Session, connection_id: int, data) -> SiteConnection:
        connection = get_or_404(
            db, SiteConnection, connection_id, detail="Connexion inter-site introuvable",
        )
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(connection, field, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Conflit de contrainte d'unicité")
        db.refresh(connection)
        return connection

    @staticmethod
    def delete_connection(db: Session, connection_id: int) -> None:
        connection = get_or_404(
            db, SiteConnection, connection_id, detail="Connexion inter-site introuvable",
        )
        db.delete(connection)
        db.commit()

    # ── VLANs ────────────────────────────────────────────────────────────

    @staticmethod
    def list_vlans(db: Session, site_id: int) -> list[VlanDefinition]:
        get_or_404(db, Site, site_id)
        return (
            db.query(VlanDefinition)
            .filter(VlanDefinition.site_id == site_id)
            .order_by(VlanDefinition.vlan_id)
            .all()
        )

    @staticmethod
    def get_vlan(db: Session, vlan_def_id: int) -> VlanDefinition:
        return get_or_404(db, VlanDefinition, vlan_def_id, detail="Définition VLAN introuvable")

    @staticmethod
    def create_vlan(db: Session, data) -> VlanDefinition:
        get_or_404(db, Site, data.site_id)
        vlan = VlanDefinition(**data.model_dump())
        db.add(vlan)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Un VLAN avec l'ID {data.vlan_id} existe déjà pour ce site",
            )
        db.refresh(vlan)
        return vlan

    @staticmethod
    def update_vlan(db: Session, vlan_def_id: int, data) -> VlanDefinition:
        vlan = get_or_404(db, VlanDefinition, vlan_def_id, detail="Définition VLAN introuvable")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(vlan, field, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Conflit : un VLAN avec cet ID existe déjà pour ce site",
            )
        db.refresh(vlan)
        return vlan

    @staticmethod
    def delete_vlan(db: Session, vlan_def_id: int) -> None:
        vlan = get_or_404(db, VlanDefinition, vlan_def_id, detail="Définition VLAN introuvable")
        db.delete(vlan)
        db.commit()
