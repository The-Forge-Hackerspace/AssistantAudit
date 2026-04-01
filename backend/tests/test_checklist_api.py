# tests/test_checklist_api.py

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_template(db_session):
    """Crée un template avec items pour les tests API."""
    from app.models.checklist import ChecklistItem, ChecklistSection, ChecklistTemplate
    tpl = ChecklistTemplate(name="API Test CL", category="lan", is_predefined=True)
    db_session.add(tpl)
    db_session.flush()
    s = ChecklistSection(template_id=tpl.id, name="Section API", order=0)
    db_session.add(s)
    db_session.flush()
    for i in range(3):
        db_session.add(ChecklistItem(section_id=s.id, label=f"Item API {i}", order=i, ref_code=f"A.{i}"))
    db_session.flush()
    return tpl


class TestChecklistTemplateRoutes:
    """CK-003 : routes templates."""

    def test_list_templates(self, client: TestClient, auditeur_headers, seeded_template):
        resp = client.get("/api/v1/checklists/templates", headers=auditeur_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_template_with_sections_and_items(self, client: TestClient, auditeur_headers, seeded_template):
        resp = client.get(f"/api/v1/checklists/templates/{seeded_template.id}", headers=auditeur_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sections"]) >= 1
        assert len(data["sections"][0]["items"]) >= 1

    def test_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/checklists/templates")
        assert resp.status_code == 401


class TestChecklistInstanceRoutes:
    """CK-003 : routes instances."""

    def test_create_instance(self, client: TestClient, auditeur_headers, seeded_template, db_session, auditeur_user):
        from app.models.audit import Audit
        audit = Audit(nom_projet="cl-api-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        resp = client.post("/api/v1/checklists/instances", json={
            "template_id": seeded_template.id, "audit_id": audit.id
        }, headers=auditeur_headers)
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"

    def test_respond_to_item(self, client: TestClient, auditeur_headers, seeded_template, db_session, auditeur_user):
        from app.models.audit import Audit
        from app.models.checklist import ChecklistItem, ChecklistSection
        audit = Audit(nom_projet="cl-resp-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        # Créer instance
        resp = client.post("/api/v1/checklists/instances", json={
            "template_id": seeded_template.id, "audit_id": audit.id
        }, headers=auditeur_headers)
        instance_id = resp.json()["id"]

        # Trouver un item
        item = db_session.query(ChecklistItem).join(ChecklistSection).filter(
            ChecklistSection.template_id == seeded_template.id
        ).first()

        # Répondre
        resp = client.put(
            f"/api/v1/checklists/instances/{instance_id}/items/{item.id}",
            json={"status": "OK", "note": "Test OK"},
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "OK"

    def test_get_progress(self, client: TestClient, auditeur_headers, seeded_template, db_session, auditeur_user):
        from app.models.audit import Audit
        audit = Audit(nom_projet="cl-prog-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        resp = client.post("/api/v1/checklists/instances", json={
            "template_id": seeded_template.id, "audit_id": audit.id
        }, headers=auditeur_headers)
        instance_id = resp.json()["id"]

        resp = client.get(
            f"/api/v1/checklists/instances/{instance_id}/progress",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total_items"] == 3
        assert resp.json()["progress_percent"] == 0

    def test_isolation_other_user_gets_404(
        self, client: TestClient, second_auditeur_headers, seeded_template, db_session, auditeur_user, auditeur_headers
    ):
        from app.models.audit import Audit
        audit = Audit(nom_projet="cl-isol-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        resp = client.post("/api/v1/checklists/instances", json={
            "template_id": seeded_template.id, "audit_id": audit.id
        }, headers=auditeur_headers)
        instance_id = resp.json()["id"]

        # L'autre auditeur ne peut pas voir l'instance
        resp = client.get(
            f"/api/v1/checklists/instances/{instance_id}",
            headers=second_auditeur_headers,
        )
        assert resp.status_code == 404

    def test_delete_instance_makes_it_non_retrievable(
        self, client: TestClient, auditeur_headers, seeded_template, db_session, auditeur_user
    ):
        from app.models.audit import Audit
        audit = Audit(nom_projet="cl-del-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        resp = client.post("/api/v1/checklists/instances", json={
            "template_id": seeded_template.id, "audit_id": audit.id
        }, headers=auditeur_headers)
        instance_id = resp.json()["id"]

        resp = client.delete(
            f"/api/v1/checklists/instances/{instance_id}", headers=auditeur_headers
        )
        assert resp.status_code == 200

        resp_get = client.get(
            f"/api/v1/checklists/instances/{instance_id}", headers=auditeur_headers
        )
        assert resp_get.status_code == 404

    def test_complete_instance_sets_status_and_completed_at(
        self, client: TestClient, auditeur_headers, seeded_template, db_session, auditeur_user
    ):
        from app.models.audit import Audit
        audit = Audit(nom_projet="cl-compl-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        resp = client.post("/api/v1/checklists/instances", json={
            "template_id": seeded_template.id, "audit_id": audit.id
        }, headers=auditeur_headers)
        instance_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/checklists/instances/{instance_id}/complete", headers=auditeur_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

        resp_get = client.get(
            f"/api/v1/checklists/instances/{instance_id}", headers=auditeur_headers
        )
        assert resp_get.status_code == 200
        assert resp_get.json()["status"] == "completed"
        assert resp_get.json()["completed_at"] is not None
