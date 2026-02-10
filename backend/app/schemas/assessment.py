"""
Schémas Assessment — Campagne & résultats d'évaluation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- ControlResult ---
class ControlResultBase(BaseModel):
    status: str = Field(
        default="not_assessed",
        pattern=r"^(not_assessed|compliant|non_compliant|partially_compliant|not_applicable)$",
    )
    evidence: Optional[str] = None
    comment: Optional[str] = None
    remediation_note: Optional[str] = None


class ControlResultUpdate(ControlResultBase):
    """Mise à jour d'un résultat de contrôle par l'auditeur"""
    pass


class ControlResultRead(ControlResultBase):
    id: int
    assessment_id: int
    control_id: int
    score: Optional[float] = None
    evidence_file_path: Optional[str] = None
    auto_result: Optional[str] = None
    is_auto_assessed: bool = False
    assessed_at: Optional[datetime] = None
    assessed_by: Optional[str] = None

    # Infos du contrôle (dénormalisé pour l'affichage)
    control_ref_id: Optional[str] = None
    control_title: Optional[str] = None
    control_severity: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Assessment ---
class AssessmentCreate(BaseModel):
    equipement_id: int
    framework_id: int
    notes: Optional[str] = None


class AssessmentRead(BaseModel):
    id: int
    campaign_id: int
    equipement_id: int
    framework_id: int
    score: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    assessed_by: Optional[str] = None
    results: list[ControlResultRead] = []

    # Infos liées
    equipement_ip: Optional[str] = None
    equipement_hostname: Optional[str] = None
    framework_name: Optional[str] = None
    compliance_score: Optional[float] = None

    model_config = {"from_attributes": True}


# --- Campaign ---
class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    audit_id: int


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(
        default=None,
        pattern=r"^(draft|in_progress|review|completed|archived)$",
    )


class CampaignRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    audit_id: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assessments: list[AssessmentRead] = []
    compliance_score: Optional[float] = None

    model_config = {"from_attributes": True}


class CampaignSummary(BaseModel):
    """Version allégée"""
    id: int
    name: str
    status: str
    audit_id: int
    created_at: datetime
    compliance_score: Optional[float] = None
    total_assessments: int = 0

    model_config = {"from_attributes": True}
