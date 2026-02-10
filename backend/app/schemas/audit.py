"""
Schémas Audit.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AuditBase(BaseModel):
    nom_projet: str = Field(..., min_length=1, max_length=200)
    entreprise_id: int
    objectifs: Optional[str] = None
    limites: Optional[str] = None
    hypotheses: Optional[str] = None
    risques_initiaux: Optional[str] = None


class AuditCreate(AuditBase):
    pass


class AuditUpdate(BaseModel):
    nom_projet: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = Field(
        default=None,
        pattern=r"^(NOUVEAU|EN_COURS|TERMINE|ARCHIVE)$",
    )
    objectifs: Optional[str] = None
    limites: Optional[str] = None
    hypotheses: Optional[str] = None
    risques_initiaux: Optional[str] = None


class AuditRead(AuditBase):
    id: int
    status: str
    date_debut: datetime
    lettre_mission_path: Optional[str] = None
    contrat_path: Optional[str] = None
    planning_path: Optional[str] = None
    total_campaigns: int = 0

    model_config = {"from_attributes": True}


class AuditDetail(AuditRead):
    """Vue détaillée avec les campagnes résumées"""
    entreprise_nom: Optional[str] = None

    model_config = {"from_attributes": True}
