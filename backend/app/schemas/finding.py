"""Schemas Pydantic — Findings."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FindingStatusUpdate(BaseModel):
    """Mise à jour du statut d'un finding."""

    status: str = Field(..., pattern=r"^(open|assigned|in_progress|remediated|verified|closed)$")
    comment: Optional[str] = None
    assigned_to: Optional[str] = None


class FindingLinkDuplicate(BaseModel):
    """Liaison de finding dupliqué."""

    duplicate_of_id: int


class FindingBase(BaseModel):
    """Champs communs des findings."""

    title: str
    description: Optional[str] = None
    severity: str = Field(..., pattern=r"^(critical|high|medium|low|info)$")
    remediation_note: Optional[str] = None
    assigned_to: Optional[str] = None


class FindingCreate(FindingBase):
    """Création manuelle d'un finding."""

    control_result_id: int
    assessment_id: int
    equipment_id: int


class FindingStatusHistoryResponse(BaseModel):
    """Réponse d'un changement de statut."""

    id: int
    old_status: str
    new_status: str
    changed_by: Optional[int] = None
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    """Réponse d'un finding (liste)."""

    id: int
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    assigned_to: Optional[str] = None
    duplicate_of_id: Optional[int] = None
    control_result_id: int
    assessment_id: int
    equipment_id: int
    created_at: datetime
    updated_at: datetime

    # Dénormalisé
    control_ref_id: Optional[str] = None
    control_title: Optional[str] = None
    equipment_hostname: Optional[str] = None
    equipment_ip: Optional[str] = None

    model_config = {"from_attributes": True}


class FindingDetail(FindingResponse):
    """Réponse détaillée d'un finding."""

    remediation_note: Optional[str] = None
    created_by: Optional[int] = None
    status_history: list[FindingStatusHistoryResponse] = []

    model_config = {"from_attributes": True}


class FindingGenerateRequest(BaseModel):
    """Requête de génération de findings depuis une campagne."""

    assessment_id: int


class FindingGenerateResponse(BaseModel):
    """Réponse de génération de findings."""

    generated: int
    skipped: int
    message: str


class FindingCountsByStatus(BaseModel):
    """Compteurs par statut."""

    open: int = 0
    assigned: int = 0
    in_progress: int = 0
    remediated: int = 0
    verified: int = 0
    closed: int = 0
    total: int = 0
