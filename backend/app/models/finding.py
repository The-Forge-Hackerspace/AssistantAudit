"""
Modèles Finding — Suivi des non-conformités.

Un Finding représente une non-conformité détectée lors d'une évaluation.
FindingStatusHistory trace l'audit trail des changements de statut.
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from ..core.encryption import EncryptedText


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FindingStatus(str, PyEnum):
    """Cycle de vie d'un finding."""
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REMEDIATED = "remediated"
    VERIFIED = "verified"
    CLOSED = "closed"


# Transitions valides : clé = statut actuel, valeur = statuts autorisés
VALID_TRANSITIONS: dict[FindingStatus, set[FindingStatus]] = {
    FindingStatus.OPEN: {FindingStatus.ASSIGNED, FindingStatus.CLOSED},
    FindingStatus.ASSIGNED: {FindingStatus.IN_PROGRESS, FindingStatus.OPEN},
    FindingStatus.IN_PROGRESS: {FindingStatus.REMEDIATED, FindingStatus.ASSIGNED},
    FindingStatus.REMEDIATED: {FindingStatus.VERIFIED, FindingStatus.IN_PROGRESS},
    FindingStatus.VERIFIED: {FindingStatus.CLOSED, FindingStatus.OPEN},
    FindingStatus.CLOSED: {FindingStatus.OPEN},
}


class Finding(Base):
    """
    Non-conformité détectée lors d'une évaluation.
    Vit indépendamment du ControlResult source (cycle de vie propre).
    """
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK vers les entités source
    control_result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("control_results.id"), nullable=False, index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False, index=True
    )
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipements.id"), nullable=False, index=True
    )

    # Données du finding
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical|high|medium|low|info
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), default=FindingStatus.OPEN, nullable=False, index=True
    )
    remediation_note: Mapped[str | None] = mapped_column(EncryptedText)

    # Attribution
    assigned_to: Mapped[str | None] = mapped_column(String(200))

    # Déduplication
    duplicate_of_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("findings.id"), nullable=True
    )

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Relations
    control_result: Mapped["ControlResult"] = relationship(lazy="selectin")  # type: ignore[name-defined]
    assessment: Mapped["Assessment"] = relationship(lazy="selectin")  # type: ignore[name-defined]
    equipment: Mapped["Equipement"] = relationship(lazy="selectin")  # type: ignore[name-defined]
    duplicate_of: Mapped["Finding | None"] = relationship(
        remote_side=[id], lazy="selectin"
    )
    status_history: Mapped[list["FindingStatusHistory"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan",
        lazy="selectin", order_by="FindingStatusHistory.created_at"
    )
    creator: Mapped["User | None"] = relationship(lazy="selectin")  # type: ignore[name-defined]

    # Propriétés dénormalisées
    @property
    def control_ref_id(self) -> str | None:
        cr = self.control_result
        return cr.control.ref_id if cr and cr.control else None

    @property
    def control_title(self) -> str | None:
        cr = self.control_result
        return cr.control.title if cr and cr.control else None

    @property
    def equipment_hostname(self) -> str | None:
        return self.equipment.hostname if self.equipment else None

    @property
    def equipment_ip(self) -> str | None:
        return self.equipment.ip_address if self.equipment else None

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, status={self.status.value}, severity={self.severity})>"


class FindingStatusHistory(Base):
    """Audit trail des changements de statut d'un finding."""
    __tablename__ = "finding_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    finding_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("findings.id"), nullable=False, index=True
    )
    old_status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), nullable=False
    )
    new_status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), nullable=False
    )
    changed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relations
    finding: Mapped["Finding"] = relationship(back_populates="status_history")
    user: Mapped["User | None"] = relationship(lazy="selectin")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<FindingStatusHistory(finding={self.finding_id}, {self.old_status.value}->{self.new_status.value})>"
