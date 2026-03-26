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


# ────────────────────────────────────────────────────────────────────────
# Cancel Endpoint Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_cancel_running_scan_moves_to_failed(mock_exec, client: TestClient, db_session, auditeur_headers):
    """POST /cancel on a running scan transitions status to cancelled."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    cancel = client.post(
        f"/api/v1/tools/monkey365/scans/{result_id}/cancel",
        headers=auditeur_headers,
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_cancel_non_running_scan_returns_400(mock_exec, client: TestClient, db_session, auditeur_headers):
    """POST /cancel on an already-cancelled scan returns 400."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    # First cancel succeeds
    first = client.post(
        f"/api/v1/tools/monkey365/scans/{result_id}/cancel",
        headers=auditeur_headers,
    )
    assert first.status_code == 200

    # Second cancel — scan is no longer running
    second = client.post(
        f"/api/v1/tools/monkey365/scans/{result_id}/cancel",
        headers=auditeur_headers,
    )
    assert second.status_code == 400


def test_cancel_not_found_returns_404(client: TestClient, auditeur_headers):
    """POST /cancel on a non-existent scan returns 404."""
    response = client.post(
        "/api/v1/tools/monkey365/scans/99999/cancel",
        headers=auditeur_headers,
    )
    assert response.status_code == 404


# ────────────────────────────────────────────────────────────────────────
# Logs Endpoint Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_logs_returns_empty_when_no_log_file(mock_exec, client: TestClient, db_session, auditeur_headers, tmp_path):
    """GET /logs returns empty lines list when the log file does not exist yet."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    # output_path points to a real directory that has no log file yet
    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}/logs",
        headers=auditeur_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "lines" in data
    assert isinstance(data["lines"], list)
    assert "total_lines" in data


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_logs_returns_content_when_log_file_exists(mock_exec, client: TestClient, db_session, auditeur_headers):
    """GET /logs returns log lines when monkey365.log exists in output_path."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]
    output_path = launch.json()["output_path"] if "output_path" in launch.json() else None

    # Get output_path from detail endpoint
    detail = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )
    output_path = detail.json()["output_path"]

    # Write a fake log file
    from pathlib import Path
    log_file = Path(output_path) / "monkey365.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}/logs",
        headers=auditeur_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_lines"] == 3
    assert data["lines"] == ["line 1", "line 2", "line 3"]


def test_logs_not_found_returns_404(client: TestClient, auditeur_headers):
    """GET /logs for a non-existent scan returns 404."""
    response = client.get(
        "/api/v1/tools/monkey365/scans/result/99999/logs",
        headers=auditeur_headers,
    )
    assert response.status_code == 404


# ────────────────────────────────────────────────────────────────────────
# Report Endpoint Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_report_returns_400_for_non_success_scan(mock_exec, client: TestClient, db_session, auditeur_headers):
    """GET /report returns 400 when the scan is not in success state."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    # Scan is still in running state — report not available
    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}/report",
        headers=auditeur_headers,
    )
    assert response.status_code == 400


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_report_returns_404_when_no_html_for_success_scan(mock_exec, client: TestClient, db_session, auditeur_headers):
    """GET /report returns 404 when scan succeeded but no HTML file was generated."""
    from app.models.monkey365_scan_result import Monkey365ScanStatus

    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    # Force scan to success without creating any HTML file
    from app.models.monkey365_scan_result import Monkey365ScanResult
    result = db_session.get(Monkey365ScanResult, result_id)
    result.status = Monkey365ScanStatus.SUCCESS
    db_session.commit()

    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}/report",
        headers=auditeur_headers,
    )
    assert response.status_code == 404


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_report_returns_200_file_response_when_html_exists(mock_exec, client: TestClient, db_session, auditeur_headers):
    """GET /report returns 200 FileResponse when a success scan has an HTML report."""
    from pathlib import Path
    from app.models.monkey365_scan_result import Monkey365ScanResult, Monkey365ScanStatus

    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    detail = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )
    output_path = detail.json()["output_path"]

    # Create the HTML report where the endpoint expects it
    html_dir = Path(output_path) / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    html_file = html_dir / "report.html"
    html_file.write_text("<html><body>Monkey365 report</body></html>", encoding="utf-8")

    # Mark scan as success
    result = db_session.get(Monkey365ScanResult, result_id)
    result.status = Monkey365ScanStatus.SUCCESS
    db_session.commit()

    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}/report",
        headers=auditeur_headers,
    )
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert b"Monkey365 report" in response.content


# ────────────────────────────────────────────────────────────────────────
# Delete Endpoint Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_delete_scan_removes_db_row_and_files(mock_exec, client: TestClient, db_session, auditeur_headers):
    """DELETE /scans/{id} returns 200, removes DB row, and cleans up output directory."""
    from pathlib import Path

    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    detail = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )
    output_path = Path(detail.json()["output_path"])

    # Create nested files to verify recursive deletion
    nested = output_path / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "file.txt").write_text("dummy", encoding="utf-8")

    response = client.delete(
        f"/api/v1/tools/monkey365/scans/{result_id}",
        headers=auditeur_headers,
    )
    assert response.status_code == 200
    assert "message" in response.json()

    # DB row gone
    get_after = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )
    assert get_after.status_code == 404

    # Filesystem cleaned up
    assert not output_path.exists()


def test_delete_scan_not_found_returns_404(client: TestClient, auditeur_headers):
    """DELETE /scans/{id} for a non-existent scan returns 404."""
    response = client.delete(
        "/api/v1/tools/monkey365/scans/99999",
        headers=auditeur_headers,
    )
    assert response.status_code == 404


# ─── Import-to-audit cross-tenant tests ──────────────────────────────────

@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_import_to_audit_rejects_cross_tenant_mismatch(mock_exec, client: TestClient, db_session, auditeur_headers):
    """POST /import-to-audit rejects scan-audit entreprise mismatch (multi-tenant safety)."""
    from app.models.monkey365_scan_result import Monkey365ScanResult, Monkey365ScanStatus
    from tests.factories import AuditFactory

    mock_exec.return_value = None

    entreprise_scan = EntrepriseFactory.create(db_session, nom="Entreprise Scan")
    entreprise_audit = EntrepriseFactory.create(db_session, nom="Entreprise Audit")

    # Create a successful scan belonging to entreprise_scan
    launch = client.post(
        "/api/v1/tools/monkey365/run",
        json=_run_payload(entreprise_scan.id),
        headers=auditeur_headers,
    )
    assert launch.status_code == 201
    result_id = launch.json()["id"]

    result = db_session.get(Monkey365ScanResult, result_id)
    result.status = Monkey365ScanStatus.SUCCESS
    db_session.commit()

    # Create an audit belonging to a DIFFERENT entreprise
    audit = AuditFactory.create(db_session, nom_projet="Audit Autre", entreprise_id=entreprise_audit.id)

    response = client.post(
        f"/api/v1/tools/monkey365/scans/{result_id}/import-to-audit",
        json={"audit_id": audit.id},
        headers=auditeur_headers,
    )
    assert response.status_code == 400
    assert "entreprise" in response.json()["detail"].lower()
