"""Modèles Equipement — Équipements d'infrastructure avec héritage STI."""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EquipementAuditStatus(str, PyEnum):
    A_AUDITER = "A_AUDITER"
    EN_COURS = "EN_COURS"
    CONFORME = "CONFORME"
    NON_CONFORME = "NON_CONFORME"


EQUIPEMENT_TYPE_VALUES: tuple[str, ...] = (
    "reseau",
    "serveur",
    "firewall",
    "equipement",
    "switch",
    "router",
    "access_point",
    "printer",
    "camera",
    "nas",
    "hyperviseur",
    "telephone",
    "iot",
    "cloud_gateway",
)


class Equipement(Base):
    """Modèle de base : équipement réseau / infrastructure (héritage STI)."""
    __tablename__ = "equipements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type_equipement: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Champs communs
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), index=True)
    fabricant: Mapped[str | None] = mapped_column(String(200))
    os_detected: Mapped[str | None] = mapped_column(String(255))

    # Audit
    status_audit: Mapped[EquipementAuditStatus] = mapped_column(
        Enum(EquipementAuditStatus), default=EquipementAuditStatus.A_AUDITER, nullable=False
    )

    # Métadonnées
    date_decouverte: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    date_derniere_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    notes_audit: Mapped[str | None] = mapped_column(Text)

    # Ports (commun à tous les équipements)
    ports_status: Mapped[list | None] = mapped_column(JSON)

    # Relations
    site: Mapped["Site"] = relationship(back_populates="equipements")  # type: ignore[name-defined]
    assessments: Mapped[list["Assessment"]] = relationship(  # type: ignore[name-defined]
        back_populates="equipement", cascade="all, delete-orphan", lazy="selectin"
    )
    config_analyses: Mapped[list["ConfigAnalysis"]] = relationship(  # type: ignore[name-defined]
        back_populates="equipement", cascade="all, delete-orphan", lazy="selectin"
    )
    collect_results: Mapped[list["CollectResult"]] = relationship(  # type: ignore[name-defined]
        back_populates="equipement", cascade="all, delete-orphan", lazy="selectin"
    )
    ad_audit_results: Mapped[list["ADAuditResultModel"]] = relationship(  # type: ignore[name-defined]
        back_populates="equipement", cascade="all, delete-orphan", lazy="selectin"
    )
    source_links: Mapped[list["NetworkLink"]] = relationship(  # type: ignore[name-defined]
        back_populates="source_equipement",
        foreign_keys="NetworkLink.source_equipement_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    target_links: Mapped[list["NetworkLink"]] = relationship(  # type: ignore[name-defined]
        back_populates="target_equipement",
        foreign_keys="NetworkLink.target_equipement_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("site_id", "ip_address", name="uq_site_ip"),
    )
    __mapper_args__ = {
        "polymorphic_identity": "equipement",
        "polymorphic_on": type_equipement,
    }

    def __repr__(self) -> str:
        return f"<Equipement(id={self.id}, type='{self.type_equipement}', ip='{self.ip_address}')>"


class EquipementReseau(Equipement):
    """Switch, routeur, borne WiFi, etc."""
    __tablename__ = "equipements_reseau"

    id: Mapped[int] = mapped_column(Integer, ForeignKey("equipements.id"), primary_key=True)
    vlan_config: Mapped[dict | None] = mapped_column(JSON)
    firmware_version: Mapped[str | None] = mapped_column(String(100))

    __mapper_args__ = {"polymorphic_identity": "reseau"}


class EquipementServeur(Equipement):
    """Serveur Windows, Linux, Hyperviseur."""
    __tablename__ = "equipements_serveur"

    id: Mapped[int] = mapped_column(Integer, ForeignKey("equipements.id"), primary_key=True)
    os_version_detail: Mapped[str | None] = mapped_column(String(500))
    modele_materiel: Mapped[str | None] = mapped_column(String(200))
    role_list: Mapped[dict | None] = mapped_column(JSON)
    cpu_ram_info: Mapped[dict | None] = mapped_column(JSON)

    __mapper_args__ = {"polymorphic_identity": "serveur"}


class EquipementFirewall(Equipement):
    """Firewall : FortiGate, PaloAlto, pfSense, etc."""
    __tablename__ = "equipements_firewall"

    id: Mapped[int] = mapped_column(Integer, ForeignKey("equipements.id"), primary_key=True)
    license_status: Mapped[str | None] = mapped_column(String(100))
    vpn_users_count: Mapped[int] = mapped_column(Integer, default=0)
    rules_count: Mapped[int] = mapped_column(Integer, default=0)

    __mapper_args__ = {"polymorphic_identity": "firewall"}


class EquipementSwitch(EquipementReseau):
    """Switch réseau — hérite de EquipementReseau pour accéder à ports_status, vlan_config, firmware_version."""
    __mapper_args__ = {"polymorphic_identity": "switch"}


class EquipementRouter(EquipementReseau):
    """Routeur — hérite de EquipementReseau pour accéder à ports_status, vlan_config, firmware_version."""
    __mapper_args__ = {"polymorphic_identity": "router"}


class EquipementAccessPoint(EquipementReseau):
    """Borne WiFi — hérite de EquipementReseau pour accéder à ports_status, vlan_config, firmware_version."""
    __mapper_args__ = {"polymorphic_identity": "access_point"}


class EquipementPrinter(Equipement):
    __mapper_args__ = {"polymorphic_identity": "printer"}


class EquipementCamera(Equipement):
    __mapper_args__ = {"polymorphic_identity": "camera"}


class EquipementNAS(Equipement):
    __mapper_args__ = {"polymorphic_identity": "nas"}


class EquipementHyperviseur(Equipement):
    __mapper_args__ = {"polymorphic_identity": "hyperviseur"}


class EquipementTelephone(Equipement):
    __mapper_args__ = {"polymorphic_identity": "telephone"}


class EquipementIoT(Equipement):
    __mapper_args__ = {"polymorphic_identity": "iot"}


class EquipementCloudGateway(Equipement):
    __mapper_args__ = {"polymorphic_identity": "cloud_gateway"}


class VlanDefinition(Base):
    """VLAN definition scoped to a site."""
    __tablename__ = "vlan_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    vlan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subnet: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6b7280")
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationship
    site: Mapped["Site"] = relationship(back_populates="vlan_definitions")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("site_id", "vlan_id", name="uq_site_vlan_id"),
    )

    def __repr__(self) -> str:
        return f"<VlanDefinition(id={self.id}, site_id={self.site_id}, vlan_id={self.vlan_id}, name='{self.name}')>"


EQUIPEMENT_TYPE_CLASS_MAP: dict[str, type[Equipement]] = {
    "reseau": EquipementReseau,
    "serveur": EquipementServeur,
    "firewall": EquipementFirewall,
    "equipement": Equipement,
    "switch": EquipementSwitch,
    "router": EquipementRouter,
    "access_point": EquipementAccessPoint,
    "printer": EquipementPrinter,
    "camera": EquipementCamera,
    "nas": EquipementNAS,
    "hyperviseur": EquipementHyperviseur,
    "telephone": EquipementTelephone,
    "iot": EquipementIoT,
    "cloud_gateway": EquipementCloudGateway,
}
