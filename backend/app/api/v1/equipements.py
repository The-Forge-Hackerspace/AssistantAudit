"""
Routes Equipements : CRUD des assets d'infrastructure.

Gère les 3 sous-types STI (réseau, serveur, firewall) via un champ type_equipement.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, PaginationParams
from ...models.equipement import (
    Equipement,
    EquipementReseau,
    EquipementServeur,
    EquipementFirewall,
    EquipementAuditStatus,
)
from ...models.site import Site
from ...models.user import User
from ...schemas.equipement import (
    EquipementCreate,
    EquipementRead,
    EquipementSummary,
    EquipementUpdate,
)
from ...schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()

# Mapping type → classe SQLAlchemy
_TYPE_MAP = {
    "reseau": EquipementReseau,
    "serveur": EquipementServeur,
    "firewall": EquipementFirewall,
    "equipement": Equipement,
}

# Champs spécifiques par type
_TYPE_FIELDS = {
    "reseau": ["vlan_config", "ports_status", "firmware_version"],
    "serveur": ["os_version_detail", "modele_materiel", "role_list", "cpu_ram_info"],
    "firewall": ["license_status", "vpn_users_count", "rules_count"],
}


def _equipement_to_read(eq: Equipement) -> EquipementRead:
    """Convertit un objet Equipement (ou sous-type) en EquipementRead."""
    data = {
        "id": eq.id,
        "site_id": eq.site_id,
        "type_equipement": eq.type_equipement,
        "ip_address": eq.ip_address,
        "mac_address": eq.mac_address,
        "hostname": eq.hostname,
        "fabricant": eq.fabricant,
        "os_detected": eq.os_detected,
        "status_audit": eq.status_audit.value,
        "date_decouverte": eq.date_decouverte,
        "date_derniere_maj": eq.date_derniere_maj,
        "notes_audit": eq.notes_audit,
    }
    # Ajouter les champs spécifiques selon le type
    for type_name, fields in _TYPE_FIELDS.items():
        if eq.type_equipement == type_name:
            for field in fields:
                data[field] = getattr(eq, field, None)
    return EquipementRead(**data)


@router.get("", response_model=PaginatedResponse[EquipementSummary])
async def list_equipements(
    site_id: int = None,
    type_equipement: str = Query(default=None, pattern=r"^(reseau|serveur|firewall|equipement)$"),
    status_audit: str = Query(default=None, pattern=r"^(A_AUDITER|EN_COURS|CONFORME|NON_CONFORME)$"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les équipements (filtrable par site, type, statut)"""
    query = db.query(Equipement)
    if site_id:
        query = query.filter(Equipement.site_id == site_id)
    if type_equipement:
        query = query.filter(Equipement.type_equipement == type_equipement)
    if status_audit:
        query = query.filter(Equipement.status_audit == EquipementAuditStatus(status_audit))

    total = query.count()
    items = (
        query.order_by(Equipement.ip_address)
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


@router.post("", response_model=EquipementRead, status_code=status.HTTP_201_CREATED)
async def create_equipement(
    body: EquipementCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Crée un nouvel équipement dans un site"""
    # Vérifier que le site existe
    site = db.get(Site, body.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    # Vérifier unicité site+IP
    existing = (
        db.query(Equipement)
        .filter(Equipement.site_id == body.site_id, Equipement.ip_address == body.ip_address)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"L'IP '{body.ip_address}' existe déjà pour ce site",
        )

    # Créer le bon sous-type selon type_equipement
    cls = _TYPE_MAP.get(body.type_equipement, Equipement)
    common_fields = {
        "site_id": body.site_id,
        "ip_address": body.ip_address,
        "mac_address": body.mac_address,
        "hostname": body.hostname,
        "fabricant": body.fabricant,
        "os_detected": body.os_detected,
        "notes_audit": body.notes_audit,
    }

    # Ajouter les champs spécifiques
    specific_fields = _TYPE_FIELDS.get(body.type_equipement, [])
    for field in specific_fields:
        value = getattr(body, field, None)
        if value is not None:
            common_fields[field] = value

    equipement = cls(**common_fields)
    db.add(equipement)
    db.commit()
    db.refresh(equipement)
    return _equipement_to_read(equipement)


@router.get("/{equipement_id}", response_model=EquipementRead)
async def get_equipement(
    equipement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Détail d'un équipement"""
    equipement = db.get(Equipement, equipement_id)
    if not equipement:
        raise HTTPException(status_code=404, detail="Équipement introuvable")
    return _equipement_to_read(equipement)


@router.put("/{equipement_id}", response_model=EquipementRead)
async def update_equipement(
    equipement_id: int,
    body: EquipementUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Modifie un équipement"""
    equipement = db.get(Equipement, equipement_id)
    if not equipement:
        raise HTTPException(status_code=404, detail="Équipement introuvable")

    update_data = body.model_dump(exclude_unset=True)

    # Gérer le champ status_audit (conversion str → enum)
    if "status_audit" in update_data:
        update_data["status_audit"] = EquipementAuditStatus(update_data["status_audit"])

    # Ne mettre à jour que les champs valides pour ce type
    valid_specific = _TYPE_FIELDS.get(equipement.type_equipement, [])
    all_specific = set()
    for fields in _TYPE_FIELDS.values():
        all_specific.update(fields)

    for field, value in update_data.items():
        # Bloquer les champs spécifiques d'un autre type
        if field in all_specific and field not in valid_specific:
            continue
        setattr(equipement, field, value)

    db.commit()
    db.refresh(equipement)
    return _equipement_to_read(equipement)


@router.delete("/{equipement_id}", response_model=MessageResponse)
async def delete_equipement(
    equipement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Supprime un équipement et ses assessments associés"""
    equipement = db.get(Equipement, equipement_id)
    if not equipement:
        raise HTTPException(status_code=404, detail="Équipement introuvable")

    db.delete(equipement)
    db.commit()
    return MessageResponse(message=f"Équipement {equipement.ip_address} supprimé")
