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
    # Bloc Intervention (brief §4.1)
    date_fin: Optional[datetime] = None
    client_contact_name: Optional[str] = Field(None, max_length=200)
    client_contact_title: Optional[str] = Field(None, max_length=200)
    client_contact_email: Optional[str] = Field(None, max_length=200)
    client_contact_phone: Optional[str] = Field(None, max_length=50)
    access_level: Optional[str] = Field(None, pattern=r"^(complete|partial|none)$")
    access_missing_details: Optional[str] = None
    intervention_window: Optional[str] = Field(None, max_length=200)
    intervention_constraints: Optional[str] = None
    scope_covered: Optional[str] = None
    scope_excluded: Optional[str] = None
    audit_type: Optional[str] = Field(None, pattern=r"^(initial|recurring|targeted)$")


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
    # Bloc Intervention (brief §4.1)
    date_fin: Optional[datetime] = None
    client_contact_name: Optional[str] = Field(None, max_length=200)
    client_contact_title: Optional[str] = Field(None, max_length=200)
    client_contact_email: Optional[str] = Field(None, max_length=200)
    client_contact_phone: Optional[str] = Field(None, max_length=50)
    access_level: Optional[str] = Field(None, pattern=r"^(complete|partial|none)$")
    access_missing_details: Optional[str] = None
    intervention_window: Optional[str] = Field(None, max_length=200)
    intervention_constraints: Optional[str] = None
    scope_covered: Optional[str] = None
    scope_excluded: Optional[str] = None
    audit_type: Optional[str] = Field(None, pattern=r"^(initial|recurring|targeted)$")


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
