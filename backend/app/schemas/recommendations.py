"""Schemas pour la liste exhaustive des recommandations d'un audit (TOS-25 section 5)."""

from typing import Optional

from pydantic import BaseModel, Field


class RecommendationDetail(BaseModel):
    """Une recommandation = un controle non-conforme avec ses occurrences et sa remediation."""

    control_ref: str
    title: str
    severity: str
    description: Optional[str] = None
    remediation: Optional[str] = None
    occurrences: int
    affected_equipements: list[str] = Field(default_factory=list)
    category_name: Optional[str] = None


class RecommendationsList(BaseModel):
    """Liste exhaustive des recommandations groupees par severite."""

    audit_id: int
    total: int
    by_severity: dict[str, list[RecommendationDetail]] = Field(default_factory=dict)
