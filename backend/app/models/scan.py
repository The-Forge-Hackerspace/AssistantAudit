"""
Modèles Scan Réseau — Nmap et analyse de découvertes.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from ..core.encryption import EncryptedText


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScanReseau(Base):
    __tablename__ = "scans_reseau"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str | None] = mapped_column(String(200))
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    # Isolation inter-techniciens
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    date_scan: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    raw_xml_output: Mapped[str | None] = mapped_column(EncryptedText)
    nmap_command: Mapped[str | None] = mapped_column(String(1000))
    type_scan: Mapped[str | None] = mapped_column(String(50))
    statut: Mapped[str] = mapped_column(String(20), default="running", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    nombre_hosts_trouves: Mapped[int] = mapped_column(Integer, default=0)
    nombre_ports_ouverts: Mapped[int] = mapped_column(Integer, default=0)
    duree_scan_secondes: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relations
    site: Mapped["Site"] = relationship(back_populates="scans")  # type: ignore[name-defined]
    hosts: Mapped[list["ScanHost"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ScanReseau(id={self.id}, site_id={self.site_id}, type='{self.type_scan}')>"


class ScanHost(Base):
    __tablename__ = "scan_hosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(Integer, ForeignKey("scans_reseau.id"), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    hostname: Mapped[str | None] = mapped_column(String(255))
    mac_address: Mapped[str | None] = mapped_column(String(17))
    vendor: Mapped[str | None] = mapped_column(String(200))
    os_guess: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(20))
    ports_open_count: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[str | None] = mapped_column(String(20))  # pending | kept | ignored
    chosen_type: Mapped[str | None] = mapped_column(String(50))
    equipement_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("equipements.id"), index=True)
    date_decouverte: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relations
    scan: Mapped["ScanReseau"] = relationship(back_populates="hosts")
    ports: Mapped[list["ScanPort"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ScanHost(id={self.id}, ip='{self.ip_address}', decision='{self.decision}')>"


class ScanPort(Base):
    __tablename__ = "scan_ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("scan_hosts.id"), nullable=False, index=True)
    port_number: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str | None] = mapped_column(String(10))
    state: Mapped[str | None] = mapped_column(String(20))
    service_name: Mapped[str | None] = mapped_column(String(100))
    product: Mapped[str | None] = mapped_column(String(200))
    version: Mapped[str | None] = mapped_column(String(100))
    extra_info: Mapped[str | None] = mapped_column(Text)

    # Relations
    host: Mapped["ScanHost"] = relationship(back_populates="ports")

    def __repr__(self) -> str:
        return f"<ScanPort(id={self.id}, port={self.port_number}/{self.protocol})>"
