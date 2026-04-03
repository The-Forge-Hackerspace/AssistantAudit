"""
Modèles Assessment — Évaluation de conformité.

Une AssessmentCampaign regroupe les évaluations d'un audit.
Chaque Assessment lie un équipement à un framework.
Chaque ControlResult est le résultat d'un contrôle sur un équipement.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CampaignStatus(str, PyEnum):
    """Statuts d'une campagne d'évaluation"""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ComplianceStatus(str, PyEnum):
    """Résultat de conformité d'un contrôle"""

    NOT_ASSESSED = "not_assessed"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"


class AssessmentCampaign(Base):
    """
    Campagne d'évaluation : regroupe les assessments d'un audit donné.
    Par exemple : "Campagne audit infra Q1 2026 - Client X"
    """

    __tablename__ = "assessment_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False)

    # FK
    audit_id: Mapped[int] = mapped_column(Integer, ForeignKey("audits.id"), nullable=False, index=True)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relations
    audit: Mapped["Audit"] = relationship(back_populates="campaigns")  # type: ignore[name-defined]
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<AssessmentCampaign(id={self.id}, name='{self.name}', status={self.status.value})>"

    @property
    def compliance_score(self) -> float | None:
        """Score de conformité global (0-100)"""
        all_results = []
        for assessment in self.assessments:
            all_results.extend(assessment.results)

        assessed = [
            r for r in all_results if r.status not in (ComplianceStatus.NOT_ASSESSED, ComplianceStatus.NOT_APPLICABLE)
        ]
        if not assessed:
            return None

        compliant = sum(1 for r in assessed if r.status == ComplianceStatus.COMPLIANT)
        partial = sum(0.5 for r in assessed if r.status == ComplianceStatus.PARTIALLY_COMPLIANT)
        return round((compliant + partial) / len(assessed) * 100, 1)


class Assessment(Base):
    """
    Évaluation d'un équipement selon un référentiel.
    Lie un équipement + un framework au sein d'une campagne.
    """

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessment_campaigns.id"), nullable=False, index=True)
    equipement_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipements.id"), nullable=False, index=True)
    framework_id: Mapped[int] = mapped_column(Integer, ForeignKey("frameworks.id"), nullable=False, index=True)

    # Score
    score: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    assessed_by: Mapped[str | None] = mapped_column(String(200))

    # Relations
    campaign: Mapped["AssessmentCampaign"] = relationship(back_populates="assessments")
    equipement: Mapped["Equipement"] = relationship(back_populates="assessments", lazy="selectin")  # type: ignore[name-defined]
    framework: Mapped["Framework"] = relationship(lazy="selectin")  # type: ignore[name-defined]
    results: Mapped[list["ControlResult"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Assessment(id={self.id}, equipement_id={self.equipement_id}, framework_id={self.framework_id})>"

    # Propriétés dénormalisées pour Pydantic from_attributes
    @property
    def equipement_ip(self) -> str | None:
        return self.equipement.ip_address if self.equipement else None

    @property
    def equipement_hostname(self) -> str | None:
        return self.equipement.hostname if self.equipement else None

    @property
    def framework_name(self) -> str | None:
        return self.framework.name if self.framework else None

    @property
    def compliance_score(self) -> float | None:
        """Score de conformité pour cet assessment (0-100)"""
        assessed = [
            r for r in self.results if r.status not in (ComplianceStatus.NOT_ASSESSED, ComplianceStatus.NOT_APPLICABLE)
        ]
        if not assessed:
            return None
        compliant = sum(1 for r in assessed if r.status == ComplianceStatus.COMPLIANT)
        partial = sum(0.5 for r in assessed if r.status == ComplianceStatus.PARTIALLY_COMPLIANT)
        return round((compliant + partial) / len(assessed) * 100, 1)


class ControlResult(Base):
    """
    Résultat d'un contrôle individuel pour un assessment donné.
    C'est ici qu'on stocke : conforme/non-conforme, preuve, commentaire, etc.
    """

    __tablename__ = "control_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK
    assessment_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    control_id: Mapped[int] = mapped_column(Integer, ForeignKey("controls.id"), nullable=False, index=True)

    # Résultat
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus), default=ComplianceStatus.NOT_ASSESSED, nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float)

    # Preuve & commentaire
    evidence: Mapped[str | None] = mapped_column(Text)
    evidence_file_path: Mapped[str | None] = mapped_column(String(500))
    comment: Mapped[str | None] = mapped_column(Text)
    remediation_note: Mapped[str | None] = mapped_column(Text)

    # Auto-évaluation
    auto_result: Mapped[str | None] = mapped_column(Text)  # résultat brut de l'outil auto
    is_auto_assessed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Métadonnées
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assessed_by: Mapped[str | None] = mapped_column(String(200))

    # Relations
    assessment: Mapped["Assessment"] = relationship(back_populates="results")
    control: Mapped["Control"] = relationship(lazy="selectin")  # type: ignore[name-defined]
    attachments: Mapped[list["Attachment"]] = relationship(  # type: ignore[name-defined]
        back_populates="control_result", cascade="all, delete-orphan", lazy="selectin"
    )

    # Propriétés dénormalisées pour Pydantic from_attributes
    @property
    def control_ref_id(self) -> str | None:
        return self.control.ref_id if self.control else None

    @property
    def control_title(self) -> str | None:
        return self.control.title if self.control else None

    @property
    def control_severity(self) -> str | None:
        return self.control.severity.value if self.control else None

    @property
    def control_category_name(self) -> str | None:
        return self.control.category.name if self.control and self.control.category else None

    @property
    def control_category_id(self) -> int | None:
        return self.control.category_id if self.control else None

    @property
    def control_description(self) -> str | None:
        return self.control.description if self.control else None

    @property
    def control_remediation(self) -> str | None:
        return self.control.remediation if self.control else None

    @property
    def control_check_type(self) -> str | None:
        return self.control.check_type.value if self.control else None

    def __repr__(self) -> str:
        return f"<ControlResult(id={self.id}, control_id={self.control_id}, status={self.status.value})>"
