"""Tests TDD — Routes API rapports (RPT-004 + RPT-012, brief §7.7)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def audit_for_report(db_session, auditeur_user):
    from app.models.audit import Audit

    audit = Audit(
        nom_projet="Audit réseau PME",
        entreprise_id=1,
        owner_id=auditeur_user.id,
        objectifs="Évaluer la sécurité réseau",
        limites="Pas de test d'intrusion",
    )
    db_session.add(audit)
    db_session.flush()
    return audit


class TestReportRoutes:
    """RPT-004 + RPT-012 : routes API rapports."""

    def test_create_report(self, client: TestClient, auditeur_headers, audit_for_report):
        resp = client.post(
            "/api/v1/reports",
            json={
                "audit_id": audit_for_report.id,
                "template_name": "complete",
                "consultant_name": "ACME Consulting",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"
        assert data["audit_id"] == audit_for_report.id

    def test_get_report_with_sections(self, client: TestClient, auditeur_headers, audit_for_report):
        resp = client.post(
            "/api/v1/reports",
            json={
                "audit_id": audit_for_report.id,
            },
            headers=auditeur_headers,
        )
        report_id = resp.json()["id"]

        resp = client.get(f"/api/v1/reports/{report_id}", headers=auditeur_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sections"]) == 28
        section_keys = [s["section_key"] for s in data["sections"]]
        assert "executive_summary" in section_keys
        # Synthese executive : section apres la page de garde
        exec_section = next(s for s in data["sections"] if s["section_key"] == "executive_summary")
        assert exec_section["order"] == 2

    def test_update_section_exclude(self, client: TestClient, auditeur_headers, audit_for_report):
        resp = client.post(
            "/api/v1/reports",
            json={
                "audit_id": audit_for_report.id,
            },
            headers=auditeur_headers,
        )
        report_id = resp.json()["id"]

        resp = client.put(
            f"/api/v1/reports/{report_id}/sections/introduction",
            json={"included": False},
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["included"] is False

    def test_generate_pdf(self, client: TestClient, auditeur_headers, audit_for_report):
        resp = client.post(
            "/api/v1/reports",
            json={
                "audit_id": audit_for_report.id,
                "consultant_name": "Test Consultant",
            },
            headers=auditeur_headers,
        )
        report_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/reports/{report_id}/generate",
            json={"format": "pdf"},
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"
        assert resp.json()["pdf_path"] is not None

    def test_download_pdf(self, client: TestClient, auditeur_headers, audit_for_report):
        # Créer et générer
        resp = client.post(
            "/api/v1/reports",
            json={
                "audit_id": audit_for_report.id,
            },
            headers=auditeur_headers,
        )
        report_id = resp.json()["id"]
        client.post(f"/api/v1/reports/{report_id}/generate", json={}, headers=auditeur_headers)

        resp = client.get(f"/api/v1/reports/{report_id}/download", headers=auditeur_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_list_reports(self, client: TestClient, auditeur_headers, audit_for_report):
        client.post("/api/v1/reports", json={"audit_id": audit_for_report.id}, headers=auditeur_headers)
        resp = client.get(f"/api/v1/reports?audit_id={audit_for_report.id}", headers=auditeur_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_report(self, client: TestClient, auditeur_headers, audit_for_report):
        resp = client.post("/api/v1/reports", json={"audit_id": audit_for_report.id}, headers=auditeur_headers)
        report_id = resp.json()["id"]
        resp = client.delete(f"/api/v1/reports/{report_id}", headers=auditeur_headers)
        assert resp.status_code == 200

    def test_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/reports?audit_id=1")
        assert resp.status_code == 401

    def test_other_user_gets_404(self, client: TestClient, second_auditeur_headers, auditeur_headers, audit_for_report):
        resp = client.post("/api/v1/reports", json={"audit_id": audit_for_report.id}, headers=auditeur_headers)
        report_id = resp.json()["id"]
        resp = client.get(f"/api/v1/reports/{report_id}", headers=second_auditeur_headers)
        assert resp.status_code == 404
