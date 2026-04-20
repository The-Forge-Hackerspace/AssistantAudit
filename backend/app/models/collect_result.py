"""
Modèle CollectResult — Résultat de collecte WinRM/SSH lié à un équipement.

Stocke les données collectées automatiquement sur un serveur
(infos système, réseau, sécurité, services, etc.) pour
analyse et pré-remplissage des contrôles d'audit.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from ..core.encryption import EncryptedText


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CollectMethod(str, PyEnum):
    SSH = "ssh"
    WINRM = "winrm"


class CollectStatus(str, PyEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class CollectResult(Base):
    """Résultat d'une collecte système via SSH ou WinRM, lié à un équipement."""

    __tablename__ = "collect_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipement_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipements.id"), nullable=False, index=True)
    method: Mapped[CollectMethod] = mapped_column(Enum(CollectMethod), nullable=False)
    status: Mapped[CollectStatus] = mapped_column(Enum(CollectStatus), default=CollectStatus.RUNNING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Lien vers la tache agent qui execute la collecte (agent on-prem, TOS-16)
    agent_task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_tasks.id", ondelete="SET NULL"), index=True
    )

    # Connexion
    target_host: Mapped[str] = mapped_column(String(255), nullable=False)
    target_port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    device_profile: Mapped[str | None] = mapped_column(String(50), default="linux_server")

    # Données collectées (JSON)
    hostname_collected: Mapped[str | None] = mapped_column(String(255))
    os_info: Mapped[dict | None] = mapped_column(JSON)
    network: Mapped[dict | None] = mapped_column(JSON)
    users: Mapped[dict | None] = mapped_column(JSON)
    services: Mapped[dict | None] = mapped_column(JSON)
    security: Mapped[dict | None] = mapped_column(JSON)
    storage: Mapped[dict | None] = mapped_column(JSON)
    updates: Mapped[dict | None] = mapped_column(JSON)

    # Analyse des findings
    findings: Mapped[list | None] = mapped_column(JSON)
    summary: Mapped[dict | None] = mapped_column(JSON)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Relations
    equipement: Mapped["Equipement"] = relationship(back_populates="collect_results")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<CollectResult(id={self.id}, method='{self.method}', status='{self.status}', equip={self.equipement_id})>"
        )
