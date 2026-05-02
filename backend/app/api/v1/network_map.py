from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import RbacContext, get_rbac_context, get_rbac_context_auditeur
from ...schemas.common import MessageResponse
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
from ...schemas.vlan import VlanDefinitionCreate, VlanDefinitionRead, VlanDefinitionUpdate
from ...services.network_map_service import NetworkMapService

router = APIRouter()


@router.get("/links", response_model=list[NetworkLinkRead])
def list_network_links(
    site_id: int = Query(...),
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.list_links(db, site_id, user_id=uid, is_admin=adm)


@router.get("/links/{link_id}", response_model=NetworkLinkRead)
def get_network_link(
    link_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.get_link(db, link_id, user_id=uid, is_admin=adm)


@router.post("/links", response_model=NetworkLinkRead, status_code=status.HTTP_201_CREATED)
def create_network_link(
    body: NetworkLinkCreate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.create_link(db, body, user_id=uid, is_admin=adm)


@router.put("/links/{link_id}", response_model=NetworkLinkRead)
def update_network_link(
    link_id: int,
    body: NetworkLinkUpdate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.update_link(db, link_id, body, user_id=uid, is_admin=adm)


@router.delete("/links/{link_id}", response_model=MessageResponse)
def delete_network_link(
    link_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    NetworkMapService.delete_link(db, link_id, user_id=uid, is_admin=adm)
    return MessageResponse(message="Lien supprimé")


@router.get("/site/{site_id}", response_model=NetworkMapRead)
def get_site_network_map(
    site_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    data = NetworkMapService.get_site_map_data(db, site_id, user_id=uid, is_admin=adm)
    equipements = data["equipements"]
    links = data["links"]
    layout_data = data["layout_data"]

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
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    NetworkMapService.save_layout(db, site_id, body.layout_data, user_id=uid, is_admin=adm)
    return MessageResponse(message="Layout sauvegardé")


@router.get("/overview/{entreprise_id}", response_model=MultiSiteOverviewRead)
def get_multi_site_overview(
    entreprise_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    data = NetworkMapService.get_overview_data(db, entreprise_id, user_id=uid, is_admin=adm)

    nodes = [
        MultiSiteNode(
            id=f"site-{site.id}",
            site_id=site.id,
            site_name=site.nom,
            equipement_count=len(site.equipements) if site.equipements else 0,
        )
        for site in data["sites"]
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
        for conn in data["connections"]
    ]

    return MultiSiteOverviewRead(entreprise_id=entreprise_id, nodes=nodes, edges=edges)


@router.get("/site-connections", response_model=list[SiteConnectionRead])
def list_site_connections(
    entreprise_id: int = Query(...),
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.list_connections(db, entreprise_id, user_id=uid, is_admin=adm)


@router.get("/site-connections/{connection_id}", response_model=SiteConnectionRead)
def get_site_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.get_connection(db, connection_id, user_id=uid, is_admin=adm)


@router.post("/site-connections", response_model=SiteConnectionRead, status_code=status.HTTP_201_CREATED)
def create_site_connection(
    body: SiteConnectionCreate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.create_connection(db, body, user_id=uid, is_admin=adm)


@router.put("/site-connections/{connection_id}", response_model=SiteConnectionRead)
def update_site_connection(
    connection_id: int,
    body: SiteConnectionUpdate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.update_connection(db, connection_id, body, user_id=uid, is_admin=adm)


@router.delete("/site-connections/{connection_id}", response_model=MessageResponse)
def delete_site_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    NetworkMapService.delete_connection(db, connection_id, user_id=uid, is_admin=adm)
    return MessageResponse(message="Connexion inter-site supprimée")


# ── VLAN Definitions ──


@router.get("/vlans", response_model=list[VlanDefinitionRead])
def list_vlans(
    site_id: int = Query(...),
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.list_vlans(db, site_id, user_id=uid, is_admin=adm)


@router.get("/vlans/{vlan_def_id}", response_model=VlanDefinitionRead)
def get_vlan(
    vlan_def_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.get_vlan(db, vlan_def_id, user_id=uid, is_admin=adm)


@router.post("/vlans", response_model=VlanDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_vlan(
    body: VlanDefinitionCreate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.create_vlan(db, body, user_id=uid, is_admin=adm)


@router.put("/vlans/{vlan_def_id}", response_model=VlanDefinitionRead)
def update_vlan(
    vlan_def_id: int,
    body: VlanDefinitionUpdate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    return NetworkMapService.update_vlan(db, vlan_def_id, body, user_id=uid, is_admin=adm)


@router.delete("/vlans/{vlan_def_id}", response_model=MessageResponse)
def delete_vlan(
    vlan_def_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    uid, adm = rbac.user_id, rbac.is_admin
    NetworkMapService.delete_vlan(db, vlan_def_id, user_id=uid, is_admin=adm)
    return MessageResponse(message="Définition VLAN supprimée")
