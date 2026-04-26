"""Service de génération de rapports d'audit."""

import base64
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from weasyprint import HTML

from ..models.audit import Audit
from ..models.entreprise import Entreprise
from ..models.report import REPORT_SECTIONS, AuditReport, ReportSection
from ..schemas.report import AuditReportCreate, ReportSectionUpdate

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
    def create_report(db: Session, data: AuditReportCreate, user_id: int, is_admin: bool) -> AuditReport:
        """Crée un rapport avec ses 25 sections."""
        ReportService._check_audit_access(db, data.audit_id, user_id, is_admin)

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
    def get_report(db: Session, report_id: int, user_id: int, is_admin: bool) -> AuditReport:
        """Récupère un rapport avec ses sections."""
        report = db.query(AuditReport).filter(AuditReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Rapport non trouvé")
        ReportService._check_audit_access(db, report.audit_id, user_id, is_admin)
        return report

    @staticmethod
    def _load_logo_base64(path: str | None) -> str | None:
        """Charge un logo depuis le disque en base64. Restreint au dossier uploads."""
        if not path:
            return None
        # Sécurité : interdire les chemins absolus et la traversée de répertoire
        if os.path.isabs(path) or ".." in path.split(os.sep):
            return None
        from ..core.config import get_settings

        settings = get_settings()
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        safe_path = (upload_dir / path).resolve()
        if not str(safe_path).startswith(str(upload_dir)):
            return None
        if not safe_path.is_file():
            return None
        with open(safe_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def list_reports(db: Session, audit_id: int, user_id: int, is_admin: bool) -> list[AuditReport]:
        """Liste les rapports d'un audit."""
        ReportService._check_audit_access(db, audit_id, user_id, is_admin)
        return db.query(AuditReport).filter(AuditReport.audit_id == audit_id).all()

    @staticmethod
    def update_section(
        db: Session, report_id: int, section_key: str, data: ReportSectionUpdate, user_id: int, is_admin: bool
    ) -> ReportSection:
        """Met à jour une section (inclure/exclure, titre, contenu custom)."""
        ReportService.get_report(db, report_id, user_id, is_admin)
        section = (
            db.query(ReportSection)
            .filter(
                ReportSection.report_id == report_id,
                ReportSection.section_key == section_key,
            )
            .first()
        )
        if not section:
            raise HTTPException(status_code=404, detail="Section non trouvée")

        updates = data.model_dump(exclude_unset=True)
        for key, val in updates.items():
            setattr(section, key, val)
        db.flush()
        db.refresh(section)
        return section

    @staticmethod
    def generate_pdf(db: Session, report_id: int, user_id: int, is_admin: bool) -> str:
        """Génère le PDF et retourne le chemin du fichier."""
        report = ReportService.get_report(db, report_id, user_id, is_admin)
        audit = db.query(Audit).filter(Audit.id == report.audit_id).first()

        report.status = "generating"
        db.flush()

        try:
            html_content = ReportService.render_html(db, report)

            from ..core.config import get_settings

            settings = get_settings()
            data_dir = getattr(settings, "DATA_DIR", "data")
            reports_dir = Path(data_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            filename = f"rapport_{audit.id}_{report.id}.pdf"
            pdf_path = str(reports_dir / filename)

            html_doc = HTML(string=html_content, base_url=str(TEMPLATES_DIR))
            html_doc.write_pdf(pdf_path)

            report.pdf_path = pdf_path
            report.status = "ready"
            report.generated_at = datetime.now(timezone.utc)
            db.flush()
            db.refresh(report)
            return pdf_path

        except Exception as e:
            report.status = "error"
            db.flush()
            raise HTTPException(status_code=500, detail=f"Erreur génération PDF: {str(e)}")

    @staticmethod
    def delete_report(db: Session, report_id: int, user_id: int, is_admin: bool) -> str:
        """Supprime un rapport et ses fichiers."""
        report = ReportService.get_report(db, report_id, user_id, is_admin)
        for path in [report.pdf_path, report.docx_path]:
            if path and os.path.isfile(path):
                os.remove(path)
        db.delete(report)
        db.flush()
        return f"Rapport {report_id} supprimé"

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

        # Si la section synthèse exécutive est incluse, calculer ses donnees
        executive_summary = None
        exec_section = sections_by_key.get("executive_summary")
        if exec_section and exec_section.included and not exec_section.custom_content:
            from .executive_summary_service import ExecutiveSummaryService

            try:
                executive_summary = ExecutiveSummaryService.generate(
                    db,
                    report.audit_id,
                    user_id=report.generated_by or 0,
                    is_admin=True,  # rendu serveur, pas de check user
                )
            except Exception:
                # Ne pas casser le rendu si la synthese echoue
                executive_summary = None

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
            executive_summary=executive_summary,
        )
