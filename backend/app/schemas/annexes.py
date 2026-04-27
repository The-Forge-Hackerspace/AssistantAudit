"""Schemas pour les annexes du rapport d'audit (TOS-25 section 7)."""

from typing import Optional

from pydantic import BaseModel, Field


class AnnexEquipement(BaseModel):
    """Une ligne du tableau des equipements audites."""

    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    type_equipement: str
    site_name: Optional[str] = None


class AnnexControlResult(BaseModel):
    """Une ligne du recap des resultats par controle."""

    control_ref: str
    title: str
    severity: str
    framework_name: str
    compliant: int = 0
    non_compliant: int = 0
    not_applicable: int = 0
    pending: int = 0


class AnnexFramework(BaseModel):
    """Un framework utilise dans l'audit."""

    ref_id: str
    name: str
    version: str
    source: Optional[str] = None
    author: Optional[str] = None


class AuditAnnexes(BaseModel):
    """Donnees consolidees pour la section Annexes."""

    audit_id: int
    equipements: list[AnnexEquipement] = Field(default_factory=list)
    results: list[AnnexControlResult] = Field(default_factory=list)
    frameworks: list[AnnexFramework] = Field(default_factory=list)
