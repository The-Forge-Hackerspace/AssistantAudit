"""
Modèle ConfigAnalysis — Résultat de parsing de configuration lié à un équipement.

Permet de stocker les analyses de configuration (Fortinet, OPNsense, etc.)
et de les utiliser pour pré-remplir les contrôles d'audit.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConfigAnalysis(Base):
    """Résultat d'analyse d'une configuration, lié à un équipement."""

    __tablename__ = "config_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipement_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipements.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    vendor: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), default="firewall")

    # Infos extraites
    hostname: Mapped[str | None] = mapped_column(String(255))
    firmware_version: Mapped[str | None] = mapped_column(String(200))
    serial_number: Mapped[str | None] = mapped_column(String(200))

    # Données JSON complètes
    interfaces: Mapped[dict | None] = mapped_column(JSON)
    firewall_rules: Mapped[dict | None] = mapped_column(JSON)
    findings: Mapped[dict | None] = mapped_column(JSON)
    summary: Mapped[dict | None] = mapped_column(JSON)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    raw_config: Mapped[str | None] = mapped_column(Text)  # Config source optionnelle

    # Relations
    equipement: Mapped["Equipement"] = relationship(back_populates="config_analyses")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ConfigAnalysis(id={self.id}, vendor='{self.vendor}', equip={self.equipement_id})>"
