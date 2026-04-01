"""Routes API rapports d'audit (brief §7.7)."""

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_auditeur, get_current_user
from ...models.user import User
from ...schemas.common import MessageResponse
from ...schemas.report import (
    AuditReportCreate,
    AuditReportDetail,
    AuditReportRead,
    ReportGenerateRequest,
    ReportSectionRead,
    ReportSectionUpdate,
)
from ...services.report_service import ReportService

router = APIRouter()


@router.post("", response_model=AuditReportRead, status_code=201)
def create_report(
    body: AuditReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Crée un rapport pour un audit (avec 25 sections)."""
    return ReportService.create_report(
        db, body, user_id=current_user.id, is_admin=current_user.role == "admin"
    )


@router.get("", response_model=list[AuditReportRead])
def list_reports(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les rapports d'un audit."""
    return ReportService.list_reports(
        db, audit_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )


@router.get("/{report_id}", response_model=AuditReportDetail)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère un rapport avec ses sections."""
    report = ReportService.get_report(
        db, report_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )
    return AuditReportDetail.model_validate(report)


@router.put("/{report_id}/sections/{section_key}", response_model=ReportSectionRead)
def update_section(
    report_id: int,
    section_key: str,
    body: ReportSectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Met à jour une section (inclure/exclure, titre, contenu custom)."""
    return ReportService.update_section(
        db, report_id, section_key, body,
        user_id=current_user.id, is_admin=current_user.role == "admin"
    )


@router.post("/{report_id}/generate", response_model=AuditReportRead)
def generate_report(
    report_id: int,
    body: ReportGenerateRequest = ReportGenerateRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Génère le PDF du rapport."""
    ReportService.generate_pdf(
        db, report_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )
    return ReportService.get_report(
        db, report_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Télécharge le PDF du rapport."""
    report = ReportService.get_report(
        db, report_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )
    if not report.pdf_path or not os.path.isfile(report.pdf_path):
        raise HTTPException(status_code=404, detail="PDF non généré")
    return FileResponse(
        report.pdf_path,
        media_type="application/pdf",
        filename=f"rapport_{report.audit_id}.pdf",
    )


@router.delete("/{report_id}", response_model=MessageResponse)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Supprime un rapport."""
    msg = ReportService.delete_report(
        db, report_id, user_id=current_user.id, is_admin=current_user.role == "admin"
    )
    return MessageResponse(message=msg)
