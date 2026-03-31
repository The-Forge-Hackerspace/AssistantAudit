"""Service de génération de rapports d'audit."""

import base64
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.audit import Audit
from ..models.entreprise import Entreprise
from ..models.report import AuditReport, ReportSection, REPORT_SECTIONS
from ..schemas.report import AuditReportCreate


TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "reports"


class ReportService:

    @staticmethod
    def _get_jinja_env() -> Environment:
        """Configure l'environnement Jinja2 pour les rapports."""
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        # Filtre date français
        env.filters["datefr"] = lambda dt: dt.strftime("%d/%m/%Y") if dt else ""
        return env

    @staticmethod
    def _check_audit_access(db: Session, audit_id: int, user_id: int, is_admin: bool) -> Audit:
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit non trouvé")
        if not is_admin and audit.owner_id != user_id:
            raise HTTPException(status_code=404, detail="Audit non trouvé")
        return audit

    @staticmethod
    def create_report(
        db: Session, data: AuditReportCreate, user_id: int, is_admin: bool
    ) -> AuditReport:
        """Crée un rapport avec ses 25 sections."""
        audit = ReportService._check_audit_access(db, data.audit_id, user_id, is_admin)

        report = AuditReport(
            audit_id=data.audit_id,
            template_name=data.template_name,
            consultant_logo_path=data.consultant_logo_path,
            client_logo_path=data.client_logo_path,
            consultant_name=data.consultant_name,
            consultant_contact=data.consultant_contact,
            generated_by=user_id,
        )
        db.add(report)
        db.flush()

        # Créer les 25 sections
        for order, (key, title) in enumerate(REPORT_SECTIONS):
            section = ReportSection(
                report_id=report.id,
                section_key=key,
                title=title,
                order=order,
                included=True,
            )
            db.add(section)
        db.flush()
        db.refresh(report)
        return report

    @staticmethod
    def get_report(
        db: Session, report_id: int, user_id: int, is_admin: bool
    ) -> AuditReport:
        """Récupère un rapport avec ses sections."""
        report = db.query(AuditReport).filter(AuditReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Rapport non trouvé")
        ReportService._check_audit_access(db, report.audit_id, user_id, is_admin)
        return report

    @staticmethod
    def _load_logo_base64(path: str | None) -> str | None:
        """Charge un logo depuis le disque en base64."""
        if not path or not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def render_html(db: Session, report: AuditReport) -> str:
        """Rend le rapport en HTML (étape intermédiaire avant PDF)."""
        audit = db.query(Audit).filter(Audit.id == report.audit_id).first()
        entreprise = None
        if audit and audit.entreprise_id:
            entreprise = db.query(Entreprise).filter(Entreprise.id == audit.entreprise_id).first()

        env = ReportService._get_jinja_env()

        # Charger CSS
        css_path = TEMPLATES_DIR / "styles.css"
        css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

        # Charger logos
        consultant_logo = ReportService._load_logo_base64(report.consultant_logo_path)
        client_logo = ReportService._load_logo_base64(report.client_logo_path)

        # Sections ordonnées
        ordered_sections = sorted(report.sections, key=lambda s: s.order)
        sections_by_key = {s.section_key: s for s in ordered_sections}

        template = env.get_template("report_base.html")
        return template.render(
            css=css,
            audit=audit,
            entreprise=entreprise,
            report=report,
            consultant_name=report.consultant_name,
            consultant_logo=consultant_logo,
            client_logo=client_logo,
            ordered_sections=ordered_sections,
            sections=sections_by_key,
        )
