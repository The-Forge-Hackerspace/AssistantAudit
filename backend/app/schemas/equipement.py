"""
Schémas Equipement — Assets d'infrastructure.

Supporte le polymorphisme STI avec des champs optionnels par type.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from .validators import IPAddress, MACAddress, Hostname, Description
from ..models.equipement import EQUIPEMENT_TYPE_VALUES


EQUIPEMENT_TYPE_PATTERN = "^(" + "|".join(EQUIPEMENT_TYPE_VALUES) + ")$"


class EquipementBase(BaseModel):
    ip_address: IPAddress = Field(...)
    mac_address: Optional[MACAddress] = Field(default=None)
    hostname: Optional[Hostname] = Field(default=None)
    fabricant: Optional[str] = Field(default=None, max_length=200)
    os_detected: Optional[str] = Field(default=None, max_length=255)
    notes_audit: Optional[Description] = None


class EquipementCreate(EquipementBase):
    site_id: int
    type_equipement: str = Field(
        ...,
        pattern=EQUIPEMENT_TYPE_PATTERN,
        description="Type d'équipement réseau/infrastructure",
    )
    # Champs spécifiques réseau
    vlan_config: Optional[dict] = None
    ports_status: Optional[list] = None
    firmware_version: Optional[str] = Field(default=None, max_length=100)
    # Champs spécifiques serveur
    os_version_detail: Optional[str] = Field(default=None, max_length=500)
    modele_materiel: Optional[str] = Field(default=None, max_length=200)
    role_list: Optional[dict] = None
    cpu_ram_info: Optional[dict] = None
    # Champs spécifiques firewall
    license_status: Optional[str] = Field(default=None, max_length=100)
    vpn_users_count: Optional[int] = None
    rules_count: Optional[int] = None


class EquipementUpdate(BaseModel):
    hostname: Optional[str] = Field(default=None, max_length=255)
    fabricant: Optional[str] = Field(default=None, max_length=200)
    os_detected: Optional[str] = Field(default=None, max_length=255)
    notes_audit: Optional[str] = None
    status_audit: Optional[str] = Field(
        default=None,
        pattern=r"^(A_AUDITER|EN_COURS|CONFORME|NON_CONFORME)$",
    )
    # Champs spécifiques réseau
    vlan_config: Optional[dict] = None
    ports_status: Optional[list] = None
    firmware_version: Optional[str] = Field(default=None, max_length=100)
    # Champs spécifiques serveur
    os_version_detail: Optional[str] = Field(default=None, max_length=500)
    modele_materiel: Optional[str] = Field(default=None, max_length=200)
    role_list: Optional[dict] = None
    cpu_ram_info: Optional[dict] = None
    # Champs spécifiques firewall
    license_status: Optional[str] = Field(default=None, max_length=100)
    vpn_users_count: Optional[int] = None
    rules_count: Optional[int] = None


class EquipementRead(EquipementBase):
    id: int
    site_id: int
    type_equipement: str
    status_audit: str
    date_decouverte: datetime
    date_derniere_maj: datetime
    # Champs spécifiques (présents selon le type)
    vlan_config: Optional[dict] = None
    ports_status: Optional[list] = None
    firmware_version: Optional[str] = None
    os_version_detail: Optional[str] = None
    modele_materiel: Optional[str] = None
    role_list: Optional[dict] = None
    cpu_ram_info: Optional[dict] = None
    license_status: Optional[str] = None
    vpn_users_count: Optional[int] = None
    rules_count: Optional[int] = None

    model_config = {"from_attributes": True}


class EquipementSummary(BaseModel):
    """Version allégée pour les listes"""
    id: int
    site_id: int
    type_equipement: str
    ip_address: str
    hostname: Optional[str] = None
    fabricant: Optional[str] = None
    os_detected: Optional[str] = None
    status_audit: str

    model_config = {"from_attributes": True}
