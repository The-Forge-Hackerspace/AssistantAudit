from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur
from ...models.entreprise import Entreprise
from ...models.equipement import Equipement, VlanDefinition
from ...models.network_map import NetworkLink, NetworkMapLayout, SiteConnection
from ...models.site import Site
from ...models.user import User
from ...schemas.common import MessageResponse
from ...schemas.vlan import VlanDefinitionCreate, VlanDefinitionRead, VlanDefinitionUpdate
from ...schemas.network_map import (
    MultiSiteEdge,
    MultiSiteNode,
    MultiSiteOverviewRead,
    NetworkLayoutSaveRequest,
    NetworkLinkCreate,
    NetworkLinkRead,
    NetworkLinkUpdate,
    NetworkMapEdge,
    NetworkMapNode,
    NetworkMapRead,
    SiteConnectionCreate,
    SiteConnectionRead,
    SiteConnectionUpdate,
)

router = APIRouter()


def _validate_link_endpoints_same_site(db: Session, site_id: int, source_id: int, target_id: int) -> None:
    source = db.get(Equipement, source_id)
    target = db.get(Equipement, target_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Équipement source/cible introuvable")
    if source.site_id != site_id or target.site_id != site_id:
        raise HTTPException(status_code=400, detail="Les équipements doivent appartenir au site demandé")
    if source_id == target_id:
        raise HTTPException(status_code=400, detail="Un lien ne peut pas relier un équipement à lui-même")


@router.get("/links", response_model=list[NetworkLinkRead])
def list_network_links(
    site_id: int = Query(...),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(200, ge=1, le=500, description="Éléments par page"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    links = (
        db.query(NetworkLink)
        .filter(NetworkLink.site_id == site_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return links


@router.get("/links/{link_id}", response_model=NetworkLinkRead)
def get_network_link(
    link_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    link = db.get(NetworkLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    return link


@router.post("/links", response_model=NetworkLinkRead, status_code=status.HTTP_201_CREATED)
def create_network_link(
    body: NetworkLinkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    site = db.get(Site, body.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    _validate_link_endpoints_same_site(
        db,
        body.site_id,
        body.source_equipement_id,
        body.target_equipement_id,
    )

    link = NetworkLink(**body.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.put("/links/{link_id}", response_model=NetworkLinkRead)
def update_network_link(
    link_id: int,
    body: NetworkLinkUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    link = db.get(NetworkLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(link, field, value)

    db.commit()
    db.refresh(link)
    return link


@router.delete("/links/{link_id}", response_model=MessageResponse)
def delete_network_link(
    link_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    link = db.get(NetworkLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    db.delete(link)
    db.commit()
    return MessageResponse(message="Lien supprimé")


@router.get("/site/{site_id}", response_model=NetworkMapRead)
def get_site_network_map(
    site_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    equipements = db.query(Equipement).filter(Equipement.site_id == site_id).all()
    links = db.query(NetworkLink).filter(NetworkLink.site_id == site_id).all()
    layout = db.query(NetworkMapLayout).filter(NetworkMapLayout.site_id == site_id).first()
    layout_data = layout.layout_data if layout else {}
    position_index = {
        str(item.get("id")): item
        for item in layout_data.get("nodes", [])
        if isinstance(item, dict) and item.get("id") is not None
    }

    nodes = [
        NetworkMapNode(
            id=f"eq-{eq.id}",
            equipement_id=eq.id,
            site_id=eq.site_id,
            type_equipement=eq.type_equipement,
            ip_address=eq.ip_address,
            hostname=eq.hostname,
            label=eq.hostname or eq.ip_address,
            metadata={
                "fabricant": eq.fabricant,
                "os_detected": eq.os_detected,
                "status_audit": eq.status_audit.value,
            },
            position=position_index.get(f"eq-{eq.id}"),
        )
        for eq in equipements
    ]

    edges = [
        NetworkMapEdge(
            id=f"link-{link.id}",
            link_id=link.id,
            source=f"eq-{link.source_equipement_id}",
            target=f"eq-{link.target_equipement_id}",
            metadata={
                "source_interface": link.source_interface,
                "target_interface": link.target_interface,
                "link_type": link.link_type,
                "bandwidth": link.bandwidth,
                "vlan": link.vlan,
                "network_segment": link.network_segment,
                "description": link.description,
            },
        )
        for link in links
    ]

    return NetworkMapRead(site_id=site_id, nodes=nodes, edges=edges, layout_data=layout_data)


@router.put("/site/{site_id}/layout", response_model=MessageResponse)
def save_site_network_layout(
    site_id: int,
    body: NetworkLayoutSaveRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    layout = db.query(NetworkMapLayout).filter(NetworkMapLayout.site_id == site_id).first()
    if not layout:
        layout = NetworkMapLayout(site_id=site_id, layout_data=body.layout_data)
        db.add(layout)
    else:
        layout.layout_data = body.layout_data

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflit lors de la sauvegarde du layout")
    return MessageResponse(message="Layout sauvegardé")


@router.get("/overview/{entreprise_id}", response_model=MultiSiteOverviewRead)
def get_multi_site_overview(
    entreprise_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entreprise = db.get(Entreprise, entreprise_id)
    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    sites = db.query(Site).filter(Site.entreprise_id == entreprise_id).all()
    connections = db.query(SiteConnection).filter(SiteConnection.entreprise_id == entreprise_id).all()

    nodes = [
        MultiSiteNode(
            id=f"site-{site.id}",
            site_id=site.id,
            site_name=site.nom,
            equipement_count=len(site.equipements) if site.equipements else 0,
        )
        for site in sites
    ]

    edges = [
        MultiSiteEdge(
            id=f"conn-{conn.id}",
            connection_id=conn.id,
            source=f"site-{conn.source_site_id}",
            target=f"site-{conn.target_site_id}",
            metadata={
                "link_type": conn.link_type,
                "bandwidth": conn.bandwidth,
                "description": conn.description,
            },
        )
        for conn in connections
    ]

    return MultiSiteOverviewRead(entreprise_id=entreprise_id, nodes=nodes, edges=edges)


@router.get("/site-connections", response_model=list[SiteConnectionRead])
def list_site_connections(
    entreprise_id: int = Query(...),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(200, ge=1, le=500, description="Éléments par page"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entreprise = db.get(Entreprise, entreprise_id)
    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")
    return (
        db.query(SiteConnection)
        .filter(SiteConnection.entreprise_id == entreprise_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.get("/site-connections/{connection_id}", response_model=SiteConnectionRead)
def get_site_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    connection = db.get(SiteConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connexion inter-site introuvable")
    return connection


@router.post("/site-connections", response_model=SiteConnectionRead, status_code=status.HTTP_201_CREATED)
def create_site_connection(
    body: SiteConnectionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    entreprise = db.get(Entreprise, body.entreprise_id)
    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    source_site = db.get(Site, body.source_site_id)
    target_site = db.get(Site, body.target_site_id)
    if not source_site or not target_site:
        raise HTTPException(status_code=404, detail="Site source/cible introuvable")
    if source_site.entreprise_id != body.entreprise_id or target_site.entreprise_id != body.entreprise_id:
        raise HTTPException(status_code=400, detail="Les deux sites doivent appartenir à la même entreprise")
    if body.source_site_id == body.target_site_id:
        raise HTTPException(status_code=400, detail="Une connexion inter-site doit relier deux sites différents")

    existing = (
        db.query(SiteConnection)
        .filter(
            SiteConnection.entreprise_id == body.entreprise_id,
            SiteConnection.source_site_id == body.source_site_id,
            SiteConnection.target_site_id == body.target_site_id,
            SiteConnection.link_type == body.link_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Cette connexion inter-site existe déjà")

    connection = SiteConnection(**body.model_dump())
    db.add(connection)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette connexion inter-site existe déjà (contrainte d'unicité)")
    db.refresh(connection)
    return connection


@router.put("/site-connections/{connection_id}", response_model=SiteConnectionRead)
def update_site_connection(
    connection_id: int,
    body: SiteConnectionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    connection = db.get(SiteConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connexion inter-site introuvable")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(connection, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflit de contrainte d'unicité")
    db.refresh(connection)
    return connection


@router.delete("/site-connections/{connection_id}", response_model=MessageResponse)
def delete_site_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    connection = db.get(SiteConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connexion inter-site introuvable")
    db.delete(connection)
    db.commit()
    return MessageResponse(message="Connexion inter-site supprimée")


# ── VLAN Definitions ──

@router.get("/vlans", response_model=list[VlanDefinitionRead])
def list_vlans(
    site_id: int = Query(...),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(200, ge=1, le=500, description="Éléments par page"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    return (
        db.query(VlanDefinition)
        .filter(VlanDefinition.site_id == site_id)
        .order_by(VlanDefinition.vlan_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.get("/vlans/{vlan_def_id}", response_model=VlanDefinitionRead)
def get_vlan(
    vlan_def_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    vlan = db.get(VlanDefinition, vlan_def_id)
    if not vlan:
        raise HTTPException(status_code=404, detail="Définition VLAN introuvable")
    return vlan


@router.post("/vlans", response_model=VlanDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_vlan(
    body: VlanDefinitionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    site = db.get(Site, body.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    vlan = VlanDefinition(**body.model_dump())
    db.add(vlan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Un VLAN avec l'ID {body.vlan_id} existe déjà pour ce site",
        )
    db.refresh(vlan)
    return vlan


@router.put("/vlans/{vlan_def_id}", response_model=VlanDefinitionRead)
def update_vlan(
    vlan_def_id: int,
    body: VlanDefinitionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    vlan = db.get(VlanDefinition, vlan_def_id)
    if not vlan:
        raise HTTPException(status_code=404, detail="Définition VLAN introuvable")

    for field, value in body.model_dump(exclude_unset=True).items():
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


@router.delete("/vlans/{vlan_def_id}", response_model=MessageResponse)
def delete_vlan(
    vlan_def_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    vlan = db.get(VlanDefinition, vlan_def_id)
    if not vlan:
        raise HTTPException(status_code=404, detail="Définition VLAN introuvable")
    db.delete(vlan)
    db.commit()
    return MessageResponse(message="Définition VLAN supprimée")
