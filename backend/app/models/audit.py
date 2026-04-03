"""
Modèle Audit — Projet d'audit IT.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditStatus(str, PyEnum):
    NOUVEAU = "NOUVEAU"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ARCHIVE = "ARCHIVE"


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Informations générales
    nom_projet: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[AuditStatus] = mapped_column(Enum(AuditStatus), default=AuditStatus.NOUVEAU, nullable=False)
    date_debut: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # FK
    entreprise_id: Mapped[int] = mapped_column(Integer, ForeignKey("entreprises.id"), nullable=False, index=True)
    # Isolation inter-techniciens
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Bloc Administratif
    lettre_mission_path: Mapped[str | None] = mapped_column(String(500))
    contrat_path: Mapped[str | None] = mapped_column(String(500))
    planning_path: Mapped[str | None] = mapped_column(String(500))

    # Bloc Contexte
    objectifs: Mapped[str | None] = mapped_column(Text)
    limites: Mapped[str | None] = mapped_column(Text)
    hypotheses: Mapped[str | None] = mapped_column(Text)
    risques_initiaux: Mapped[str | None] = mapped_column(Text)

    # Bloc Intervention (brief §4.1)
    # Dates
    date_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Interlocuteur technique côté client
    client_contact_name: Mapped[str | None] = mapped_column(String(200))
    client_contact_title: Mapped[str | None] = mapped_column(String(200))
    client_contact_email: Mapped[str | None] = mapped_column(String(200))
    client_contact_phone: Mapped[str | None] = mapped_column(String(50))
    # Accès admin
    access_level: Mapped[str | None] = mapped_column(String(20))  # complete, partial, none
    access_missing_details: Mapped[str | None] = mapped_column(Text)
    # Fenêtre d'intervention
    intervention_window: Mapped[str | None] = mapped_column(String(200))
    intervention_constraints: Mapped[str | None] = mapped_column(Text)
    # Périmètre convenu
    scope_covered: Mapped[str | None] = mapped_column(Text)
    scope_excluded: Mapped[str | None] = mapped_column(Text)
    # Type d'audit
    audit_type: Mapped[str | None] = mapped_column(String(30))  # initial, recurring, targeted

    # Relations
    owner: Mapped["User"] = relationship()  # type: ignore[name-defined]
    entreprise: Mapped["Entreprise"] = relationship(back_populates="audits")  # type: ignore[name-defined]
    campaigns: Mapped[list["AssessmentCampaign"]] = relationship(  # type: ignore[name-defined]
        back_populates="audit", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def total_campaigns(self) -> int:
        return len(self.campaigns) if self.campaigns else 0

    def __repr__(self) -> str:
        return f"<Audit(id={self.id}, projet='{self.nom_projet}', status={self.status.value})>"
