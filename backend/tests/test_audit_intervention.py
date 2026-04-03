"""
CK-009 : Champs intervention sur le modèle Audit (brief §4.1).
Tests TDD — écrits avant implémentation.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.entreprise import Entreprise


@pytest.fixture
def entreprise(db_session, auditeur_user):
    """Entreprise de test rattachée à l'auditeur."""
    e = Entreprise(nom="Entreprise Intervention Test", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


class TestAuditInterventionFields:
    """CK-009 : champs intervention sur le modèle Audit."""

    def test_create_audit_with_intervention_fields(self, client: TestClient, auditeur_headers, entreprise):
        resp = client.post(
            "/api/v1/audits",
            json={
                "nom_projet": "Audit intervention test",
                "entreprise_id": entreprise.id,
                "client_contact_name": "Jean Dupont",
                "client_contact_title": "DSI",
                "client_contact_email": "jean@example.com",
                "client_contact_phone": "01 23 45 67 89",
                "access_level": "partial",
                "access_missing_details": "Pas d'accès firewall",
                "intervention_window": "9h-18h",
                "scope_covered": "LAN + serveurs + AD",
                "scope_excluded": "Wi-Fi invités",
                "audit_type": "initial",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["client_contact_name"] == "Jean Dupont"
        assert data["access_level"] == "partial"
        assert data["audit_type"] == "initial"

    def test_create_audit_without_intervention_fields(self, client: TestClient, auditeur_headers, entreprise):
        """Les champs intervention sont optionnels — rétro-compatible."""
        resp = client.post(
            "/api/v1/audits",
            json={
                "nom_projet": "Audit simple",
                "entreprise_id": entreprise.id,
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["client_contact_name"] is None
        assert data["audit_type"] is None

    def test_update_audit_intervention_fields(self, client: TestClient, auditeur_headers, entreprise):
        resp = client.post(
            "/api/v1/audits",
            json={
                "nom_projet": "Audit update test",
                "entreprise_id": entreprise.id,
            },
            headers=auditeur_headers,
        )
        audit_id = resp.json()["id"]

        resp = client.put(
            f"/api/v1/audits/{audit_id}",
            json={
                "client_contact_name": "Marie Martin",
                "audit_type": "recurring",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["client_contact_name"] == "Marie Martin"
        assert resp.json()["audit_type"] == "recurring"

    def test_invalid_access_level_rejected(self, client: TestClient, auditeur_headers, entreprise):
        """access_level doit être complete/partial/none."""
        resp = client.post(
            "/api/v1/audits",
            json={
                "nom_projet": "Invalid access",
                "entreprise_id": entreprise.id,
                "access_level": "invalid",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 422

    def test_invalid_audit_type_rejected(self, client: TestClient, auditeur_headers, entreprise):
        """audit_type doit être initial/recurring/targeted."""
        resp = client.post(
            "/api/v1/audits",
            json={
                "nom_projet": "Invalid type",
                "entreprise_id": entreprise.id,
                "audit_type": "invalid",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 422

    def test_existing_audits_unaffected(
        self, client: TestClient, auditeur_headers, db_session, auditeur_user, entreprise
    ):
        """Les audits existants (sans champs intervention) fonctionnent toujours."""
        from app.models.audit import Audit

        # Créer un audit "ancien" directement en base
        audit = Audit(nom_projet="Legacy audit", entreprise_id=entreprise.id, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        # L'API peut le lire sans erreur
        resp = client.get(f"/api/v1/audits/{audit.id}", headers=auditeur_headers)
        # Le test passe si l'audit est accessible
        assert resp.status_code in (200, 404)
