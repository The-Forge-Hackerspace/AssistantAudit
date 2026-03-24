"""
Tests for Monkey365 API endpoints.

Simplified config: only spo_sites and export_to (interactive auth hardcoded).
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models.entreprise import Entreprise
from tests.factories import EntrepriseFactory


# ─── Helper ──────────────────────────────────────────────────────────────

def _run_payload(
    entreprise_id: int,
    spo_sites: list[str] | None = None,
    export_to: list[str] | None = None,
) -> dict[str, object]:
    """Build a full /run request body."""
    cfg: dict[str, object] = {}
    if spo_sites is not None:
        cfg["spo_sites"] = spo_sites
    if export_to is not None:
        cfg["export_to"] = export_to
    return {"entreprise_id": entreprise_id, "config": cfg}


# ────────────────────────────────────────────────────────────────────────
# Authentication Tests
# ────────────────────────────────────────────────────────────────────────


def test_launch_scan_unauthorized(client: TestClient, db_session):
    """Test launching scan without authentication returns 401."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
    )
    assert response.status_code == 401


def test_launch_scan_lecteur_forbidden(client: TestClient, db_session, lecteur_headers):
    """Test launching scan with lecteur role returns 403."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=lecteur_headers,
    )
    assert response.status_code == 403


def test_list_scans_unauthorized(client: TestClient, db_session):
    """Test listing scans without authentication returns 401."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.get(f"/api/v1/tools/monkey365/scans/{entreprise.id}")
    assert response.status_code == 401


def test_get_scan_detail_unauthorized(client: TestClient):
    """Test getting scan detail without authentication returns 401."""
    response = client.get("/api/v1/tools/monkey365/scans/result/1")
    assert response.status_code == 401


# ────────────────────────────────────────────────────────────────────────
# Validation Tests
# ────────────────────────────────────────────────────────────────────────


def test_launch_scan_missing_entreprise_id(client: TestClient, auditeur_headers):
    """Test launching scan without entreprise_id returns 422."""
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={"config": {}},
        headers=auditeur_headers,
    )
    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────────────
# CRUD Operation Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_success_auditeur(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test launching scan with auditeur role returns 201."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(
            entreprise.id,
            spo_sites=["https://example.sharepoint.com"],
        ),
        headers=auditeur_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "running"
    assert "scan_id" in data
    assert data["entreprise_id"] == entreprise.id
    assert "created_at" in data
    mock_exec.assert_called_once()


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_success_admin(mock_exec, client: TestClient, db_session, admin_headers):
    """Test launching scan with admin role returns 201."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "running"


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_default_config(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test launching scan with empty config uses defaults (spo_sites=[], export_to=[JSON, HTML])."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={"entreprise_id": entreprise.id, "config": {}},
        headers=auditeur_headers,
    )

    assert response.status_code == 201
    result_id = response.json()["id"]

    detail = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )
    assert detail.status_code == 200
    config = detail.json()["config_snapshot"]
    assert config["spo_sites"] == []
    assert "JSON" in config["export_to"]
    assert "HTML" in config["export_to"]


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_invalid_entreprise(mock_exec, client: TestClient, auditeur_headers):
    """Test launching scan with non-existent entreprise returns 404."""
    mock_exec.return_value = None

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(99999),
        headers=auditeur_headers,
    )
    assert response.status_code == 404


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_list_scans_success(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test listing scans for an entreprise returns 200 with array."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    # Launch 2 scans
    for _ in range(2):
        client.post(
            "/api/v1/tools/monkey365/run",
            json=_run_payload(entreprise.id),
            headers=auditeur_headers,
        )

    response = client.get(
        f"/api/v1/tools/monkey365/scans/{entreprise.id}",
        headers=auditeur_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for scan in data:
        assert "id" in scan
        assert "status" in scan
        assert "scan_id" in scan
        assert scan["entreprise_id"] == entreprise.id


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_get_scan_detail_success(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test getting scan detail returns 200 with full details."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    # Launch scan
    launch_response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(
            entreprise.id,
            spo_sites=["https://example.sharepoint.com"],
            export_to=["JSON"],
        ),
        headers=auditeur_headers,
    )
    assert launch_response.status_code == 201
    result_id = launch_response.json()["id"]

    # Get detail
    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == result_id
    assert data["status"] == "running"
    assert "config_snapshot" in data
    assert "output_path" in data
    assert "created_at" in data


def test_get_scan_detail_not_found(client: TestClient, auditeur_headers):
    """Test getting non-existent scan returns 404."""
    response = client.get(
        "/api/v1/tools/monkey365/scans/result/99999",
        headers=auditeur_headers,
    )
    assert response.status_code == 404


# ────────────────────────────────────────────────────────────────────────
# Config Snapshot Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_config_snapshot_contains_only_expected_keys(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that config_snapshot contains spo_sites, export_to, output_dir — no secrets."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(
            entreprise.id,
            spo_sites=["https://corp.sharepoint.com"],
            export_to=["JSON", "HTML"],
        ),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    detail = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )
    assert detail.status_code == 200
    config = detail.json()["config_snapshot"]

    # Only these keys should be present
    allowed_keys = {"spo_sites", "export_to", "output_dir"}
    assert set(config.keys()) <= allowed_keys

    assert config["spo_sites"] == ["https://corp.sharepoint.com"]
    assert "JSON" in config["export_to"]
    assert "HTML" in config["export_to"]

    # No legacy fields
    for forbidden in ("client_secret", "password", "auth_mode", "tenant_id", "client_id", "provider"):
        assert forbidden not in config


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_response_has_no_secrets(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that launch (summary) response has no secret fields."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert response.status_code == 201
    raw = str(response.json())
    for secret in ("client_secret", "password", "tenant_id", "client_id"):
        assert secret not in raw


# ────────────────────────────────────────────────────────────────────────
# Response Schema Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_response_schema(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that launch scan response matches Monkey365ScanResultSummary schema."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )

    assert response.status_code == 201
    data = response.json()

    # Required fields
    assert isinstance(data["id"], int)
    assert isinstance(data["entreprise_id"], int)
    assert isinstance(data["status"], str)
    assert isinstance(data["scan_id"], str)
    assert isinstance(data["created_at"], str)

    # Optional fields
    assert "entreprise_slug" in data
    assert "findings_count" in data
    assert "completed_at" in data
    assert "duration_seconds" in data


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_get_scan_detail_response_schema(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that get scan detail response matches Monkey365ScanResultRead schema."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    # Launch scan
    launch_response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    result_id = launch_response.json()["id"]

    # Get detail
    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Required fields from summary
    assert isinstance(data["id"], int)
    assert isinstance(data["entreprise_id"], int)
    assert isinstance(data["status"], str)
    assert isinstance(data["scan_id"], str)
    assert isinstance(data["created_at"], str)

    # Additional fields in detail response
    assert "config_snapshot" in data
    assert isinstance(data["config_snapshot"], dict)
    assert "output_path" in data
    assert "error_message" in data


# ────────────────────────────────────────────────────────────────────────
# JSON Auto-Append Validation Test
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_export_to_auto_includes_json(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that export_to automatically includes JSON format."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    # Launch scan with only HTML export
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id, export_to=["HTML"]),
        headers=auditeur_headers,
    )

    assert response.status_code == 201
    result_id = response.json()["id"]

    # Get detail and verify JSON was added
    detail_response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )

    assert detail_response.status_code == 200
    config = detail_response.json()["config_snapshot"]
    assert "JSON" in config["export_to"]
    assert "HTML" in config["export_to"]
