# tests/test_checklist_service.py

import pytest

from app.models.audit import Audit
from app.models.checklist import ChecklistItem, ChecklistSection, ChecklistTemplate
from app.schemas.checklist import ChecklistInstanceCreate, ChecklistResponseUpdate
from app.services.checklist_service import ChecklistService
from app.core.errors import ConflictError, NotFoundError


@pytest.fixture
def checklist_setup(db_session, auditeur_user):
    """Crée un template + audit pour les tests."""
    tpl = ChecklistTemplate(name="Test CL", category="lan", is_predefined=True)
    db_session.add(tpl)
    db_session.flush()

    s1 = ChecklistSection(template_id=tpl.id, name="Section 1", order=0)
    db_session.add(s1)
    db_session.flush()

    items = []
    for i in range(3):
        item = ChecklistItem(section_id=s1.id, label=f"Item {i + 1}", order=i, ref_code=f"1.{i + 1}")
        db_session.add(item)
        items.append(item)
    db_session.flush()

    audit = Audit(nom_projet="cl-test", entreprise_id=1, owner_id=auditeur_user.id)
    db_session.add(audit)
    db_session.flush()

    return {"template": tpl, "section": s1, "items": items, "audit": audit}


class TestChecklistServiceInstances:
    """CK-002 : service checklist — instances."""

    def test_create_instance(self, db_session, auditeur_user, checklist_setup):
        instance = ChecklistService.create_instance(
            db_session,
            ChecklistInstanceCreate(
                template_id=checklist_setup["template"].id,
                audit_id=checklist_setup["audit"].id,
            ),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        assert instance.status == "draft"

    def test_create_duplicate_instance_raises_409(self, db_session, auditeur_user, checklist_setup):
        data = ChecklistInstanceCreate(
            template_id=checklist_setup["template"].id,
            audit_id=checklist_setup["audit"].id,
        )
        ChecklistService.create_instance(db_session, data, auditeur_user.id, False)
        with pytest.raises(Exception) as exc:
            ChecklistService.create_instance(db_session, data, auditeur_user.id, False)
        assert isinstance(exc.value, ConflictError)

    def test_other_user_cannot_access_instance(self, db_session, second_auditeur_user, checklist_setup, auditeur_user):
        instance = ChecklistService.create_instance(
            db_session,
            ChecklistInstanceCreate(
                template_id=checklist_setup["template"].id,
                audit_id=checklist_setup["audit"].id,
            ),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        with pytest.raises(Exception) as exc:
            ChecklistService.get_instance(
                db_session,
                instance.id,
                user_id=second_auditeur_user.id,
                is_admin=False,
            )
        assert isinstance(exc.value, NotFoundError)


class TestChecklistServiceResponses:
    """CK-002 : service checklist — réponses et progression."""

    def test_respond_to_item(self, db_session, auditeur_user, checklist_setup):
        instance = ChecklistService.create_instance(
            db_session,
            ChecklistInstanceCreate(
                template_id=checklist_setup["template"].id,
                audit_id=checklist_setup["audit"].id,
            ),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        response = ChecklistService.respond_to_item(
            db_session,
            instance.id,
            checklist_setup["items"][0].id,
            ChecklistResponseUpdate(status="OK", note="Vérifié"),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        assert response.status == "OK"
        assert response.note == "Vérifié"

    def test_respond_updates_instance_status(self, db_session, auditeur_user, checklist_setup):
        instance = ChecklistService.create_instance(
            db_session,
            ChecklistInstanceCreate(
                template_id=checklist_setup["template"].id,
                audit_id=checklist_setup["audit"].id,
            ),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        assert instance.status == "draft"
        ChecklistService.respond_to_item(
            db_session,
            instance.id,
            checklist_setup["items"][0].id,
            ChecklistResponseUpdate(status="OK"),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        db_session.refresh(instance)
        assert instance.status == "in_progress"

    def test_progress_calculation(self, db_session, auditeur_user, checklist_setup):
        instance = ChecklistService.create_instance(
            db_session,
            ChecklistInstanceCreate(
                template_id=checklist_setup["template"].id,
                audit_id=checklist_setup["audit"].id,
            ),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        # Répondre à 2 items sur 3
        ChecklistService.respond_to_item(
            db_session,
            instance.id,
            checklist_setup["items"][0].id,
            ChecklistResponseUpdate(status="OK"),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        ChecklistService.respond_to_item(
            db_session,
            instance.id,
            checklist_setup["items"][1].id,
            ChecklistResponseUpdate(status="NOK"),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        progress = ChecklistService.get_progress(db_session, instance.id)
        assert progress["total_items"] == 3
        assert progress["answered"] == 2
        assert progress["ok"] == 1
        assert progress["nok"] == 1
        assert progress["unchecked"] == 1
        assert progress["progress_percent"] == 67  # round(2/3 * 100)

    def test_upsert_response(self, db_session, auditeur_user, checklist_setup):
        """Répondre 2 fois au même item met à jour la réponse."""
        instance = ChecklistService.create_instance(
            db_session,
            ChecklistInstanceCreate(
                template_id=checklist_setup["template"].id,
                audit_id=checklist_setup["audit"].id,
            ),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        ChecklistService.respond_to_item(
            db_session,
            instance.id,
            checklist_setup["items"][0].id,
            ChecklistResponseUpdate(status="NOK"),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        resp = ChecklistService.respond_to_item(
            db_session,
            instance.id,
            checklist_setup["items"][0].id,
            ChecklistResponseUpdate(status="OK", note="Corrigé"),
            user_id=auditeur_user.id,
            is_admin=False,
        )
        assert resp.status == "OK"
        assert resp.note == "Corrigé"
        # Vérifier qu'il n'y a qu'une seule réponse
        progress = ChecklistService.get_progress(db_session, instance.id)
        assert progress["answered"] == 1
