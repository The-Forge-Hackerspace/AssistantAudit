"""Tests TDD — Modèles rapport d'audit (RPT-002, brief §7.7)."""

import pytest

from app.models.report import REPORT_SECTIONS, AuditReport, ReportSection


class TestAuditReport:
    """RPT-002 : modèle rapport d'audit."""

    def test_create_report(self, db_session, auditeur_user):
        from app.models.audit import Audit

        audit = Audit(nom_projet="rapport-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = AuditReport(
            audit_id=audit.id,
            template_name="complete",
            generated_by=auditeur_user.id,
        )
        db_session.add(report)
        db_session.flush()
        assert report.id is not None
        assert report.status == "draft"

    def test_report_with_sections(self, db_session, auditeur_user):
        from app.models.audit import Audit

        audit = Audit(nom_projet="rapport-sections", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = AuditReport(audit_id=audit.id, template_name="complete")
        db_session.add(report)
        db_session.flush()

        # Creer toutes les sections
        for order, (key, title) in enumerate(REPORT_SECTIONS):
            section = ReportSection(
                report_id=report.id,
                section_key=key,
                title=title,
                order=order,
            )
            db_session.add(section)
        db_session.flush()

        db_session.refresh(report)
        assert len(report.sections) == 31
        assert report.sections[0].section_key == "cover"
        assert report.sections[1].section_key == "toc"
        assert report.sections[2].section_key == "executive_summary"
        assert report.sections[26].section_key == "synthesis"
        assert report.sections[27].section_key == "recommendations"
        assert report.sections[28].section_key == "remediation_plan"
        assert report.sections[29].section_key == "annexes"
        assert report.sections[30].section_key == "glossary"

    def test_sections_defined(self):
        """Le brief §7.7 définit 25 sections + synthèse exécutive + recommandations + plan."""
        assert len(REPORT_SECTIONS) == 31

    def test_section_keys_unique(self):
        """Chaque section a une clé unique."""
        keys = [k for k, _ in REPORT_SECTIONS]
        assert len(keys) == len(set(keys))

    def test_duplicate_section_key_rejected(self, db_session, auditeur_user):
        """Un rapport ne peut pas avoir 2 sections avec la même clé."""
        from sqlalchemy.exc import IntegrityError

        from app.models.audit import Audit

        audit = Audit(nom_projet="dup-section", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = AuditReport(audit_id=audit.id)
        db_session.add(report)
        db_session.flush()

        db_session.add(ReportSection(report_id=report.id, section_key="cover", title="PG", order=0))
        db_session.flush()
        db_session.add(ReportSection(report_id=report.id, section_key="cover", title="PG2", order=1))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_cascade_delete_report(self, db_session, auditeur_user):
        """Supprimer un rapport supprime ses sections."""
        from app.models.audit import Audit

        audit = Audit(nom_projet="cascade-rpt", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = AuditReport(audit_id=audit.id)
        db_session.add(report)
        db_session.flush()
        report_id = report.id

        db_session.add(ReportSection(report_id=report_id, section_key="cover", title="PG", order=0))
        db_session.flush()

        db_session.delete(report)
        db_session.flush()
        assert db_session.query(ReportSection).filter_by(report_id=report_id).count() == 0

    def test_section_included_default_true(self, db_session, auditeur_user):
        """Par défaut, toutes les sections sont incluses."""
        from app.models.audit import Audit

        audit = Audit(nom_projet="incl-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = AuditReport(audit_id=audit.id)
        db_session.add(report)
        db_session.flush()

        section = ReportSection(report_id=report.id, section_key="cover", title="PG", order=0)
        db_session.add(section)
        db_session.flush()
        assert section.included is True

    def test_section_custom_content(self, db_session, auditeur_user):
        """Une section peut avoir du contenu personnalisé."""
        from app.models.audit import Audit

        audit = Audit(nom_projet="custom-content", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        report = AuditReport(audit_id=audit.id)
        db_session.add(report)
        db_session.flush()

        section = ReportSection(
            report_id=report.id,
            section_key="introduction",
            title="Introduction",
            order=1,
            custom_content="Merci de nous avoir fait confiance.",
        )
        db_session.add(section)
        db_session.flush()
        assert section.custom_content is not None
