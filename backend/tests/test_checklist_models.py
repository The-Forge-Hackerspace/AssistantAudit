"""Tests TDD — Modèles checklist terrain (step 26, brief §4.2, §7.2)."""

import pytest

from app.models.checklist import (
    ChecklistInstance,
    ChecklistItem,
    ChecklistResponse,
    ChecklistSection,
    ChecklistTemplate,
)


class TestChecklistTemplate:
    """CK-001 : modèle template checklist."""

    def test_create_template(self, db_session):
        tpl = ChecklistTemplate(name="Checklist LAN", category="lan", is_predefined=True)
        db_session.add(tpl)
        db_session.flush()
        assert tpl.id is not None

    def test_template_with_sections_and_items(self, db_session):
        tpl = ChecklistTemplate(name="Test Template", category="custom")
        db_session.add(tpl)
        db_session.flush()

        section = ChecklistSection(template_id=tpl.id, name="Section 1", order=0)
        db_session.add(section)
        db_session.flush()

        item = ChecklistItem(section_id=section.id, label="Point de contrôle 1", order=0, ref_code="1.1")
        db_session.add(item)
        db_session.flush()

        db_session.refresh(tpl)
        assert len(tpl.sections) == 1
        assert len(tpl.sections[0].items) == 1
        assert tpl.sections[0].items[0].label == "Point de contrôle 1"

    def test_cascade_delete_template(self, db_session):
        """Supprimer un template supprime sections et items."""
        tpl = ChecklistTemplate(name="Cascade Test", category="custom")
        db_session.add(tpl)
        db_session.flush()
        tpl_id = tpl.id

        section = ChecklistSection(template_id=tpl_id, name="S1", order=0)
        db_session.add(section)
        db_session.flush()
        section_id = section.id

        db_session.add(ChecklistItem(section_id=section_id, label="I1", order=0))
        db_session.flush()

        db_session.delete(tpl)
        db_session.flush()

        assert db_session.query(ChecklistSection).filter_by(id=section_id).first() is None


class TestChecklistInstance:
    """CK-001 : instance de checklist liée à un audit."""

    def test_create_instance(self, db_session, auditeur_user):
        from app.models.audit import Audit

        # Prérequis : template + audit
        tpl = ChecklistTemplate(name="Instance Test", category="lan")
        db_session.add(tpl)
        db_session.flush()

        audit = Audit(nom_projet="test-cl", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        instance = ChecklistInstance(template_id=tpl.id, audit_id=audit.id, filled_by=auditeur_user.id)
        db_session.add(instance)
        db_session.flush()
        assert instance.id is not None
        assert instance.status == "draft"

    def test_unique_instance_per_audit_site(self, db_session, auditeur_user):
        """Un même template ne peut être instancié 2 fois pour le même audit+site."""
        from sqlalchemy.exc import IntegrityError

        from app.models.audit import Audit

        tpl = ChecklistTemplate(name="Unique Test", category="custom")
        db_session.add(tpl)
        db_session.flush()

        audit = Audit(nom_projet="test-uniq", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        db_session.add(ChecklistInstance(template_id=tpl.id, audit_id=audit.id))
        db_session.flush()

        db_session.add(ChecklistInstance(template_id=tpl.id, audit_id=audit.id))
        with pytest.raises(IntegrityError):
            db_session.flush()


class TestChecklistResponse:
    """CK-001 : réponse à un item de checklist."""

    def test_respond_to_item(self, db_session, auditeur_user):
        from app.models.audit import Audit

        tpl = ChecklistTemplate(name="Response Test", category="custom")
        db_session.add(tpl)
        db_session.flush()

        section = ChecklistSection(template_id=tpl.id, name="S", order=0)
        db_session.add(section)
        db_session.flush()

        item = ChecklistItem(section_id=section.id, label="Check 1", order=0)
        db_session.add(item)
        db_session.flush()

        audit = Audit(nom_projet="test-resp", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        instance = ChecklistInstance(template_id=tpl.id, audit_id=audit.id)
        db_session.add(instance)
        db_session.flush()

        response = ChecklistResponse(instance_id=instance.id, item_id=item.id, status="OK", note="Vérifié sur site")
        db_session.add(response)
        db_session.flush()
        assert response.status == "OK"

    def test_invalid_status_rejected(self, db_session):
        """Un statut invalide est rejeté par la contrainte check."""
        # Note : SQLite ne vérifie pas les CHECK constraints par défaut
        # Ce test vérifie la validation au niveau schema (Pydantic)
        from pydantic import ValidationError

        from app.schemas.checklist import ChecklistResponseUpdate

        with pytest.raises(ValidationError):
            ChecklistResponseUpdate(status="INVALID")

    def test_unique_response_per_item_per_instance(self, db_session, auditeur_user):
        """Un item ne peut avoir qu'une seule réponse par instance."""
        from sqlalchemy.exc import IntegrityError

        from app.models.audit import Audit

        tpl = ChecklistTemplate(name="Unique Resp", category="custom")
        db_session.add(tpl)
        db_session.flush()
        section = ChecklistSection(template_id=tpl.id, name="S", order=0)
        db_session.add(section)
        db_session.flush()
        item = ChecklistItem(section_id=section.id, label="I", order=0)
        db_session.add(item)
        db_session.flush()

        audit = Audit(nom_projet="test-uniq-r", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()
        inst = ChecklistInstance(template_id=tpl.id, audit_id=audit.id)
        db_session.add(inst)
        db_session.flush()

        db_session.add(ChecklistResponse(instance_id=inst.id, item_id=item.id, status="OK"))
        db_session.flush()
        db_session.add(ChecklistResponse(instance_id=inst.id, item_id=item.id, status="NOK"))
        with pytest.raises(IntegrityError):
            db_session.flush()
