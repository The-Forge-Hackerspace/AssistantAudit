"""
Modèle ADAuditResult — Résultat d'un audit Active Directory via LDAP.

Stocke les données collectées sur un domaine AD (comptes, groupes,
GPO, politique de MdP, LAPS…) pour analyse et pré-remplissage des
contrôles d'audit.
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ADAuditStatus(str, PyEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ADAuditResultModel(Base):
    """Résultat d'un audit Active Directory, lié à un équipement (serveur DC)."""
    __tablename__ = "ad_audit_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipement_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("equipements.id"), nullable=True, index=True
    )
    status: Mapped[ADAuditStatus] = mapped_column(
        Enum(ADAuditStatus), default=ADAuditStatus.RUNNING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # Connexion
    target_host: Mapped[str] = mapped_column(String(255), nullable=False)
    target_port: Mapped[int] = mapped_column(Integer, nullable=False, default=389)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)

    # Données domaine
    domain_name: Mapped[str | None] = mapped_column(String(255))
    domain_functional_level: Mapped[str | None] = mapped_column(String(50))
    forest_functional_level: Mapped[str | None] = mapped_column(String(50))

    # Stats
    total_users: Mapped[int | None] = mapped_column(Integer)
    enabled_users: Mapped[int | None] = mapped_column(Integer)
    disabled_users: Mapped[int | None] = mapped_column(Integer)

    # Données collectées (JSON)
    dc_list: Mapped[list | None] = mapped_column(JSON)
    domain_admins: Mapped[list | None] = mapped_column(JSON)
    enterprise_admins: Mapped[list | None] = mapped_column(JSON)
    schema_admins: Mapped[list | None] = mapped_column(JSON)
    inactive_users: Mapped[list | None] = mapped_column(JSON)
    never_expire_password: Mapped[list | None] = mapped_column(JSON)
    never_logged_in: Mapped[list | None] = mapped_column(JSON)
    admin_account_status: Mapped[dict | None] = mapped_column(JSON)
    password_policy: Mapped[dict | None] = mapped_column(JSON)
    fine_grained_policies: Mapped[list | None] = mapped_column(JSON)
    gpo_list: Mapped[list | None] = mapped_column(JSON)
    laps_deployed: Mapped[bool | None] = mapped_column(default=False)

    # Findings (constats d'audit)
    findings: Mapped[list | None] = mapped_column(JSON)
    summary: Mapped[dict | None] = mapped_column(JSON)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Relations
    equipement: Mapped["Equipement"] = relationship(back_populates="ad_audit_results")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<ADAuditResult(id={self.id}, domain='{self.domain_name}', "
            f"status='{self.status}', equip={self.equipement_id})>"
        )
