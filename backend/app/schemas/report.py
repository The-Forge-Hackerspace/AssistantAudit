"""Schemas Pydantic pour les rapports d'audit."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReportSectionRead(BaseModel):
    id: int
    section_key: str
    title: str
    order: int
    included: bool
    custom_content: Optional[str] = None
    model_config = {"from_attributes": True}


class ReportSectionUpdate(BaseModel):
    """Permet d'activer/désactiver une section ou de modifier son contenu."""
    included: Optional[bool] = None
    title: Optional[str] = Field(None, max_length=200)
    custom_content: Optional[str] = None


class AuditReportCreate(BaseModel):
    audit_id: int
    template_name: str = Field(default="complete", pattern=r"^(complete|light|compliance)$")
    consultant_logo_path: Optional[str] = None
    client_logo_path: Optional[str] = None
    consultant_name: Optional[str] = None
    consultant_contact: Optional[str] = None


class AuditReportRead(BaseModel):
    id: int
    audit_id: int
    status: str
    template_name: str
    consultant_logo_path: Optional[str] = None
    client_logo_path: Optional[str] = None
    consultant_name: Optional[str] = None
    consultant_contact: Optional[str] = None
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    generated_by: Optional[int] = None
    generated_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditReportDetail(AuditReportRead):
    """Rapport avec toutes ses sections."""
    sections: list[ReportSectionRead] = []


class ReportGenerateRequest(BaseModel):
    """Demande de génération PDF/Word."""
    format: str = Field(default="pdf", pattern=r"^(pdf|docx|both)$")
