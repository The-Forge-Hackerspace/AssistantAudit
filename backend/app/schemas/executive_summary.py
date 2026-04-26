"""Schemas pour la synthese executive d'un audit."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StatusBreakdown(BaseModel):
    compliant: int = 0
    non_compliant: int = 0
    partially_compliant: int = 0
    not_applicable: int = 0
    not_assessed: int = 0


class SeverityBreakdown(BaseModel):
    """Decompte d'une severite : nb de chaque statut + total evalue."""

    total: int = 0
    compliant: int = 0
    non_compliant: int = 0
    partially_compliant: int = 0
    not_assessed: int = 0
    not_applicable: int = 0


class TopNonCompliance(BaseModel):
    """Une non-conformite recurrente (groupee par controle)."""

    control_ref: str
    title: str
    severity: str
    occurrences: int
    affected_equipements: list[str]


class Recommendation(BaseModel):
    """Recommandation prioritaire = non-conformite + remediation."""

    control_ref: str
    title: str
    severity: str
    remediation: Optional[str] = None
    occurrences: int


class ExecutiveSummary(BaseModel):
    """Synthese executive d'un audit, calculee a la volee."""

    audit_id: int
    audit_name: str
    entreprise_name: Optional[str] = None
    generated_at: datetime

    # Indique si la synthese a des donnees exploitables
    has_data: bool

    # KPIs globaux
    global_score: Optional[float] = None  # 0-100
    total_evaluations: int = 0
    total_equipements: int = 0
    total_controls_assessed: int = 0

    # Decompte par statut et severite
    by_status: StatusBreakdown
    by_severity: dict[str, SeverityBreakdown] = Field(default_factory=dict)

    # Top 5 non-conformites
    top_non_compliances: list[TopNonCompliance] = Field(default_factory=list)

    # 3 recommandations prioritaires
    recommendations: list[Recommendation] = Field(default_factory=list)
