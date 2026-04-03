"""Tests TDD — Routes API tags (TAG-003, brief §5)."""

from fastapi.testclient import TestClient


class TestTagRoutes:
    """TAG-003 : routes API tags."""

    def test_create_tag(self, client: TestClient, auditeur_headers):
        resp = client.post("/api/v1/tags", json={"name": "test-route", "color": "#EF4444"}, headers=auditeur_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-route"
        assert data["id"] > 0

    def test_list_tags(self, client: TestClient, auditeur_headers):
        # Créer un tag d'abord
        client.post("/api/v1/tags", json={"name": "list-test"}, headers=auditeur_headers)
        resp = client.get("/api/v1/tags", headers=auditeur_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_update_tag(self, client: TestClient, auditeur_headers):
        resp = client.post("/api/v1/tags", json={"name": "before-update"}, headers=auditeur_headers)
        tag_id = resp.json()["id"]
        resp = client.put(f"/api/v1/tags/{tag_id}", json={"name": "after-update"}, headers=auditeur_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "after-update"

    def test_delete_tag(self, client: TestClient, auditeur_headers):
        resp = client.post("/api/v1/tags", json={"name": "to-delete"}, headers=auditeur_headers)
        tag_id = resp.json()["id"]
        resp = client.delete(f"/api/v1/tags/{tag_id}", headers=auditeur_headers)
        assert resp.status_code == 200

    def test_associate_tag(self, client: TestClient, auditeur_headers):
        resp = client.post("/api/v1/tags", json={"name": "assoc-route"}, headers=auditeur_headers)
        tag_id = resp.json()["id"]
        resp = client.post(
            "/api/v1/tags/associate",
            json={"tag_id": tag_id, "taggable_type": "equipement", "taggable_id": 1},
            headers=auditeur_headers,
        )
        assert resp.status_code == 201

    def test_get_entity_tags(self, client: TestClient, auditeur_headers):
        resp = client.post("/api/v1/tags", json={"name": "entity-route"}, headers=auditeur_headers)
        tag_id = resp.json()["id"]
        client.post(
            "/api/v1/tags/associate",
            json={"tag_id": tag_id, "taggable_type": "equipement", "taggable_id": 999},
            headers=auditeur_headers,
        )
        resp = client.get("/api/v1/tags/entity/equipement/999", headers=auditeur_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "entity-route"

    def test_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/tags")
        assert resp.status_code == 401

    def test_dissociate_tag(self, client: TestClient, auditeur_headers):
        resp = client.post("/api/v1/tags", json={"name": "dissoc-route"}, headers=auditeur_headers)
        tag_id = resp.json()["id"]
        client.post(
            "/api/v1/tags/associate",
            json={"tag_id": tag_id, "taggable_type": "equipement", "taggable_id": 888},
            headers=auditeur_headers,
        )
        resp = client.delete(
            f"/api/v1/tags/associate?tag_id={tag_id}&taggable_type=equipement&taggable_id=888",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200


class TestTagIsolation:
    """TAG-003 : isolation inter-utilisateurs."""

    def test_other_user_cannot_see_audit_tags(
        self, client: TestClient, auditeur_headers, second_auditeur_headers, db_session, auditeur_user
    ):
        """Un auditeur ne voit pas les tags d'audit d'un autre auditeur."""
        from app.models.audit import Audit

        # Créer un audit appartenant au premier auditeur
        audit = Audit(nom_projet="tag-isol-test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        # Créer un tag global (visible par tous)
        resp = client.post("/api/v1/tags", json={"name": "isol-global", "color": "#000000"}, headers=auditeur_headers)
        assert resp.status_code == 201

        # Créer un tag d'audit (visible uniquement par le propriétaire)
        resp = client.post(
            "/api/v1/tags",
            json={"name": "isol-audit", "color": "#FF0000", "scope": "audit", "audit_id": audit.id},
            headers=auditeur_headers,
        )
        assert resp.status_code == 201

        # Le second auditeur voit le tag global mais pas le tag d'audit
        resp = client.get("/api/v1/tags", headers=second_auditeur_headers)
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["items"]]
        assert "isol-global" in names
        assert "isol-audit" not in names
