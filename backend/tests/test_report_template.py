"""Tests TDD — Service de rendu rapport Jinja2 (RPT-003, brief §7.7)."""

import pytest

from app.schemas.report import AuditReportCreate
from app.services.report_service import ReportService


class TestReportService:
    """RPT-003 : service de rendu rapport."""

    def test_create_report_with_sections(self, db_session, auditeur_user):
        from app.models.audit import Audit

        audit = Audit(nom_projet="template-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = ReportService.create_report(
            db_session,
            AuditReportCreate(audit_id=audit.id, template_name="complete"),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        assert len(report.sections) == 29
        assert report.sections[0].section_key == "cover"
        # TOC suit la cover, puis la synthese executive
        assert report.sections[1].section_key == "toc"
        assert report.sections[2].section_key == "executive_summary"
        assert report.sections[2].order == 2
        assert report.status == "draft"

    def test_render_html_contains_cover(self, db_session, auditeur_user):
        from app.models.audit import Audit

        audit = Audit(nom_projet="rendu-html-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = ReportService.create_report(
            db_session,
            AuditReportCreate(audit_id=audit.id),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        html = ReportService.render_html(db_session, report)
        assert "Rapport d'audit" in html
        assert "rendu-html-test" in html

    def test_render_html_contains_sections(self, db_session, auditeur_user):
        from app.models.audit import Audit

        audit = Audit(nom_projet="sections-html", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = ReportService.create_report(
            db_session,
            AuditReportCreate(audit_id=audit.id),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        html = ReportService.render_html(db_session, report)
        assert "Introduction" in html
        assert "Objectifs" in html

    def test_other_user_cannot_create_report(self, db_session, auditeur_user, second_auditeur_user):
        from app.models.audit import Audit

        audit = Audit(nom_projet="isolation-rpt", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        with pytest.raises(Exception) as exc:
            ReportService.create_report(
                db_session,
                AuditReportCreate(audit_id=audit.id),
                user_id=second_auditeur_user.id,
                is_admin=False,
            )
        assert exc.value.status_code == 404

    def test_excluded_section_not_in_html(self, db_session, auditeur_user):
        """Une section exclue n'apparaît pas dans le HTML."""
        from app.models.audit import Audit

        audit = Audit(nom_projet="exclude-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = ReportService.create_report(
            db_session,
            AuditReportCreate(audit_id=audit.id),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        # Exclure la section "Introduction"
        for section in report.sections:
            if section.section_key == "introduction":
                section.included = False
        db_session.flush()

        html = ReportService.render_html(db_session, report)
        # Le titre "Introduction" ne doit plus apparaître comme section
        assert 'id="section-introduction"' not in html
