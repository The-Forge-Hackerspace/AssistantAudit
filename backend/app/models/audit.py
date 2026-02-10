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
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus), default=AuditStatus.NOUVEAU, nullable=False
    )
    date_debut: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # FK
    entreprise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entreprises.id"), nullable=False
    )

    # Bloc Administratif
    lettre_mission_path: Mapped[str | None] = mapped_column(String(500))
    contrat_path: Mapped[str | None] = mapped_column(String(500))
    planning_path: Mapped[str | None] = mapped_column(String(500))

    # Bloc Contexte
    objectifs: Mapped[str | None] = mapped_column(Text)
    limites: Mapped[str | None] = mapped_column(Text)
    hypotheses: Mapped[str | None] = mapped_column(Text)
    risques_initiaux: Mapped[str | None] = mapped_column(Text)

    # Relations
    entreprise: Mapped["Entreprise"] = relationship(back_populates="audits")  # type: ignore[name-defined]
    campaigns: Mapped[list["AssessmentCampaign"]] = relationship(  # type: ignore[name-defined]
        back_populates="audit", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Audit(id={self.id}, projet='{self.nom_projet}', status={self.status.value})>"
