"""
Tests for Monkey365 API endpoints.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models.entreprise import Entreprise
from tests.factories import EntrepriseFactory


# ────────────────────────────────────────────────────────────────────────
# Authentication Tests
# ────────────────────────────────────────────────────────────────────────


def test_launch_scan_unauthorized(client: TestClient, db_session):
    """Test launching scan without authentication returns 401."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        }
    )
    assert response.status_code == 401


def test_launch_scan_lecteur_forbidden(client: TestClient, db_session, lecteur_headers):
    """Test launching scan with lecteur role returns 403."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
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
        json={
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
        headers=auditeur_headers,
    )
    assert response.status_code == 422


def test_launch_scan_missing_required_config(client: TestClient, db_session, auditeur_headers):
    """Test launching scan with missing required config fields returns 422."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
            }
        },
        headers=auditeur_headers,
    )
    assert response.status_code == 422


def test_launch_scan_invalid_collect_pattern(client: TestClient, db_session, auditeur_headers):
    """Test launching scan with invalid collect values returns 422."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
                "collect": ["Invalid@Name", "path/to/collector"]
            }
        },
        headers=auditeur_headers,
    )
    assert response.status_code == 422


def test_launch_scan_invalid_auth_mode(client: TestClient, db_session, auditeur_headers):
    """Test launching scan with invalid auth_mode returns 422."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "invalid_mode",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret"
            }
        },
        headers=auditeur_headers,
    )
    assert response.status_code == 422


def test_launch_scan_invalid_scan_sites(client: TestClient, db_session, auditeur_headers):
    """Test launching scan with non-HTTPS scan_sites returns 422."""
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
                "scan_sites": ["http://example.com", "ftp://site.com"]
            }
        },
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
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
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
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
        headers=admin_headers,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "running"


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_invalid_entreprise(mock_exec, client: TestClient, auditeur_headers):
    """Test launching scan with non-existent entreprise returns 404."""
    mock_exec.return_value = None
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": 99999,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
        headers=auditeur_headers,
    )
    assert response.status_code == 404


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_list_scans_success(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test listing scans for an entreprise returns 200 with array."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    # Launch 2 scans
    for i in range(2):
        client.post(
            "/api/v1/tools/monkey365/run",
            json={
                "entreprise_id": entreprise.id,
                "config": {
                    "provider": "Microsoft365",
                    "auth_mode": "client_credentials",
                    "tenant_id": f"12345678-1234-1234-1234-12345678{i:04d}",
                    "client_id": "87654321-4321-4321-4321-cba987654321",
                    "client_secret": "test-secret",
                }
            },
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
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
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
# Security Tests
# ────────────────────────────────────────────────────────────────────────


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_launch_scan_excludes_client_secret_from_response(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that client_secret is not included in launch response config_snapshot."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "super-secret-value",
            }
        },
        headers=auditeur_headers,
    )
    
    assert response.status_code == 201
    # Summary response does not include config_snapshot
    data = response.json()
    assert "client_secret" not in str(data)


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_get_scan_detail_excludes_secrets_from_config_snapshot(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that config_snapshot in detail response excludes secrets."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")
    
    # Launch scan with secrets
    launch_response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "super-secret-value",
            }
        },
        headers=auditeur_headers,
    )
    assert launch_response.status_code == 201
    result_id = launch_response.json()["id"]
    
    # Get detail and verify secrets excluded
    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    config = data["config_snapshot"]
    assert "client_secret" not in config
    # Verify non-secret fields are present
    assert config["provider"] == "Microsoft365"
    assert config["tenant_id"] == "12345678-1234-1234-1234-123456789abc"
    assert config["client_id"] == "87654321-4321-4321-4321-cba987654321"


@patch('app.services.monkey365_scan_service.Monkey365ScanService.execute_scan_background')
def test_get_scan_detail_excludes_password_from_config_snapshot(mock_exec, client: TestClient, db_session, auditeur_headers):
    """Test that config_snapshot excludes ROPC password values."""
    mock_exec.return_value = None
    entreprise = EntrepriseFactory.create(db_session, nom="Test Corp")

    launch_response = client.post(
        "/api/v1/tools/monkey365/run",
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "ropc",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "username": "auditor@example.com",
                "password": "super-secret-password",
            }
        },
        headers=auditeur_headers,
    )
    assert launch_response.status_code == 201
    result_id = launch_response.json()["id"]

    response = client.get(
        f"/api/v1/tools/monkey365/scans/result/{result_id}",
        headers=auditeur_headers,
    )

    assert response.status_code == 200
    config = response.json()["config_snapshot"]
    assert "password" not in config


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
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
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
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
            }
        },
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
        json={
            "entreprise_id": entreprise.id,
            "config": {
                "provider": "Microsoft365",
                "auth_mode": "client_credentials",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "client_id": "87654321-4321-4321-4321-cba987654321",
                "client_secret": "test-secret",
                "export_to": ["HTML"]
            }
        },
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

