"""
Service Equipement : CRUD des assets d'infrastructure.

Gere les sous-types STI (reseau, serveur, firewall) via polymorphisme.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.helpers import get_or_404, user_has_access_to_entreprise
from ..models.audit import Audit
from ..models.equipement import (
    Equipement,
    EquipementAuditStatus,
    EQUIPEMENT_TYPE_CLASS_MAP,
)
from ..models.site import Site
from ..schemas.equipement import EquipementCreate, EquipementRead, EquipementUpdate

# Mapping type → classe SQLAlchemy
_TYPE_MAP = EQUIPEMENT_TYPE_CLASS_MAP

# Champs specifiques par type
_TYPE_FIELDS = {
    "reseau": ["vlan_config", "ports_status", "firmware_version"],
    "switch": ["vlan_config", "ports_status", "firmware_version"],
    "router": ["vlan_config", "ports_status", "firmware_version"],
    "access_point": ["vlan_config", "ports_status", "firmware_version"],
    "serveur": ["os_version_detail", "modele_materiel", "role_list", "cpu_ram_info", "ports_status"],
    "hyperviseur": ["os_version_detail", "modele_materiel", "role_list", "cpu_ram_info", "ports_status"],
    "nas": ["os_version_detail", "modele_materiel", "role_list", "cpu_ram_info", "ports_status"],
    "firewall": ["license_status", "vpn_users_count", "rules_count", "ports_status"],
    "printer": ["ports_status"],
    "camera": ["ports_status"],
    "telephone": ["ports_status"],
    "iot": ["ports_status"],
    "cloud_gateway": ["ports_status"],
    "equipement": ["ports_status"],
}


def equipement_to_read(eq: Equipement) -> EquipementRead:
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
    for type_name, fields in _TYPE_FIELDS.items():
        if eq.type_equipement == type_name:
            for field in fields:
                data[field] = getattr(eq, field, None)
    return EquipementRead(**data)


def _check_site_access(
    db: Session, site_id: int, user_id: int | None, is_admin: bool,
) -> None:
    """Verifie l'acces au site via la chaine Site → Entreprise → Audit."""
    if user_id is not None and not is_admin:
        site = db.get(Site, site_id)
        if not site or not user_has_access_to_entreprise(db, site.entreprise_id, user_id):
            raise HTTPException(status_code=404, detail="Equipement introuvable")


class EquipementService:

    @staticmethod
    def list_equipements(
        db: Session,
        site_id: int | None = None,
        entreprise_id: int | None = None,
        type_equipement: str | None = None,
        status_audit: str | None = None,
        offset: int = 0,
        limit: int = 20,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> tuple[list[Equipement], int]:
        """Liste les equipements avec filtres et pagination. Non-admin filtre par ownership."""
        query = db.query(Equipement)

        if user_id is not None and not is_admin:
            accessible_ent_ids = (
                db.query(Audit.entreprise_id)
                .filter(Audit.owner_id == user_id)
                .distinct()
                .scalar_subquery()
            )
            query = query.join(Site, Equipement.site_id == Site.id).filter(
                Site.entreprise_id.in_(accessible_ent_ids)
            )
            if site_id is not None:
                query = query.filter(Equipement.site_id == site_id)
            if entreprise_id is not None:
                query = query.filter(Site.entreprise_id == entreprise_id)
        else:
            if site_id is not None:
                query = query.filter(Equipement.site_id == site_id)
            if entreprise_id is not None:
                query = query.join(Site, Equipement.site_id == Site.id).filter(
                    Site.entreprise_id == entreprise_id
                )

        if type_equipement is not None:
            query = query.filter(Equipement.type_equipement == type_equipement)
        if status_audit is not None:
            query = query.filter(
                Equipement.status_audit == EquipementAuditStatus(status_audit)
            )
        total = query.count()
        items = (
            query.order_by(Equipement.ip_address)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def get_equipement(
        db: Session, equipement_id: int,
        user_id: int | None = None, is_admin: bool = False,
    ) -> Equipement:
        """Recupere un equipement par ID. Non-admin doit avoir acces via la chaine."""
        equipement = get_or_404(db, Equipement, equipement_id)
        _check_site_access(db, equipement.site_id, user_id, is_admin)
        return equipement

    @staticmethod
    def create_equipement(
        db: Session, data: EquipementCreate,
        user_id: int | None = None, is_admin: bool = False,
    ) -> Equipement:
        """Cree un equipement dans un site. Verifie l'acces et l'unicite site+IP."""
        get_or_404(db, Site, data.site_id)
        _check_site_access(db, data.site_id, user_id, is_admin)

        existing = (
            db.query(Equipement)
            .filter(Equipement.site_id == data.site_id, Equipement.ip_address == data.ip_address)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"L'IP '{data.ip_address}' existe déjà pour ce site",
            )

        cls = _TYPE_MAP.get(data.type_equipement, Equipement)
        common_fields = {
            "site_id": data.site_id,
            "ip_address": data.ip_address,
            "mac_address": data.mac_address,
            "hostname": data.hostname,
            "fabricant": data.fabricant,
            "os_detected": data.os_detected,
            "notes_audit": data.notes_audit,
        }

        specific_fields = _TYPE_FIELDS.get(data.type_equipement, [])
        for field in specific_fields:
            value = getattr(data, field, None)
            if value is not None:
                common_fields[field] = value

        equipement = cls(**common_fields)
        db.add(equipement)
        db.flush()
        db.refresh(equipement)
        return equipement

    @staticmethod
    def update_equipement(
        db: Session, equipement_id: int, data: EquipementUpdate,
        user_id: int | None = None, is_admin: bool = False,
    ) -> Equipement:
        """Met a jour un equipement. Verifie l'acces via la chaine."""
        equipement = get_or_404(db, Equipement, equipement_id)
        _check_site_access(db, equipement.site_id, user_id, is_admin)

        update_data = data.model_dump(exclude_unset=True)

        if "status_audit" in update_data:
            update_data["status_audit"] = EquipementAuditStatus(update_data["status_audit"])

        valid_specific = _TYPE_FIELDS.get(equipement.type_equipement, [])
        all_specific = set()
        for fields in _TYPE_FIELDS.values():
            all_specific.update(fields)

        for field, value in update_data.items():
            if field in all_specific and field not in valid_specific:
                continue
            setattr(equipement, field, value)

        db.flush()
        db.refresh(equipement)
        return equipement

    @staticmethod
    def delete_equipement(db: Session, equipement_id: int) -> str:
        """Supprime un equipement. Retourne l'IP de l'equipement supprime."""
        equipement = get_or_404(db, Equipement, equipement_id)
        ip = equipement.ip_address
        db.delete(equipement)
        db.flush()
        return ip
