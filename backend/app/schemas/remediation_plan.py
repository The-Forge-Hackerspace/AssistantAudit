"""Schemas pour le plan de remediation d'un audit (TOS-25 section 6)."""

from typing import Optional

from pydantic import BaseModel, Field


class RemediationAction(BaseModel):
    """Une action du plan : un controle non-conforme avec son horizon et sa charge estimee."""

    control_ref: str
    title: str
    severity: str
    remediation: Optional[str] = None
    occurrences: int
    affected_equipements: list[str] = Field(default_factory=list)
    horizon: str  # "quick_wins" | "short_term" | "mid_term" | "long_term"
    effort_days: float


class RemediationHorizon(BaseModel):
    """Un bloc d'horizon avec ses actions et ses totaux."""

    key: str
    label: str
    description: str
    actions: list[RemediationAction] = Field(default_factory=list)
    total_actions: int = 0
    total_effort_days: float = 0.0


class RemediationPlan(BaseModel):
    """Plan de remediation complet groupe par horizon temporel."""

    audit_id: int
    total_actions: int
    total_effort_days: float
    horizons: list[RemediationHorizon] = Field(default_factory=list)
