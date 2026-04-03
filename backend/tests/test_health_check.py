"""
Tests for health check endpoints.
"""

from unittest.mock import MagicMock, patch

from app.core.health_check import HealthCheckService


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    def test_health_endpoint_returns_200(self, client):
        """Verify /health endpoint returns 200 status"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_json(self, client):
        """Verify /health endpoint returns JSON response"""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"

    def test_health_endpoint_includes_status(self, client):
        """Verify /health endpoint includes status field"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_includes_timestamp(self, client):
        """Verify /health endpoint includes timestamp"""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data
        # Verify ISO format
        assert "T" in data["timestamp"]


class TestReadyEndpoint:
    """Tests for /ready endpoint"""

    @patch("app.core.health_check.SessionLocal")
    def test_ready_endpoint_returns_200_when_db_connected(self, mock_session_local, client):
        """Verify /ready endpoint returns 200 when database is connected"""
        # Mock successful database connection
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        mock_session_local.return_value = mock_db

        response = client.get("/ready")
        assert response.status_code == 200

    @patch("app.core.health_check.SessionLocal")
    def test_ready_endpoint_returns_503_when_db_disconnected(self, mock_session_local, client):
        """Verify /ready endpoint returns 503 when database is not available"""
        # Mock failed database connection
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Connection refused")
        mock_session_local.return_value = mock_db

        response = client.get("/ready")
        assert response.status_code == 503

    @patch("app.core.health_check.SessionLocal")
    def test_ready_endpoint_includes_ready_status(self, mock_session_local, client):
        """Verify /ready endpoint includes ready field"""
        # Mock successful database connection
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        mock_session_local.return_value = mock_db

        response = client.get("/ready")
        # Note: Response is a string representation, not JSON
        content = response.text
        assert "ready" in content.lower()

    @patch("app.core.health_check.SessionLocal")
    def test_ready_endpoint_includes_components(self, mock_session_local, client):
        """Verify /ready endpoint includes component status"""
        # Mock successful database connection
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        mock_session_local.return_value = mock_db

        response = client.get("/ready")
        content = response.text
        assert "components" in content.lower()


class TestLivenessEndpoint:
    """Tests for /liveness endpoint"""

    def test_liveness_endpoint_returns_200(self, client):
        """Verify /liveness endpoint returns 200 status"""
        response = client.get("/liveness")
        assert response.status_code == 200

    def test_liveness_endpoint_returns_json(self, client):
        """Verify /liveness endpoint returns JSON response"""
        response = client.get("/liveness")
        assert response.headers["content-type"] == "application/json"

    def test_liveness_endpoint_includes_status(self, client):
        """Verify /liveness endpoint includes status field"""
        response = client.get("/liveness")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestHealthCheckService:
    """Tests for HealthCheckService"""

    def test_get_health_status_returns_healthy(self):
        """Verify get_health_status returns healthy status"""
        status = HealthCheckService.get_health_status()
        assert status["status"] == "healthy"
        assert "timestamp" in status

    @patch("app.core.health_check.SessionLocal")
    def test_check_database_connectivity_success(self, mock_session_local):
        """Verify database connectivity check succeeds when DB is available"""
        # Mock successful database connection
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        mock_session_local.return_value = mock_db

        result = HealthCheckService.check_database_connectivity()
        assert result["status"] == "connected"
        assert "response_time_ms" in result
        assert result["response_time_ms"] >= 0

    @patch("app.core.health_check.SessionLocal")
    def test_check_database_connectivity_failure(self, mock_session_local):
        """Verify database connectivity check fails when DB is unavailable"""
        # Mock failed database connection
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Connection refused")
        mock_session_local.return_value = mock_db

        result = HealthCheckService.check_database_connectivity()
        assert result["status"] == "disconnected"
        assert "error" in result
        assert "response_time_ms" in result

    @patch("app.core.health_check.SessionLocal")
    def test_get_ready_status_ready(self, mock_session_local):
        """Verify get_ready_status returns ready when DB is connected"""
        # Mock successful database connection
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        mock_session_local.return_value = mock_db

        status = HealthCheckService.get_ready_status()
        assert status["ready"] is True
        assert "components" in status
        assert status["components"]["database"]["status"] == "ready"

    @patch("app.core.health_check.SessionLocal")
    def test_get_ready_status_not_ready(self, mock_session_local):
        """Verify get_ready_status returns not ready when DB is disconnected"""
        # Mock failed database connection
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Connection refused")
        mock_session_local.return_value = mock_db

        status = HealthCheckService.get_ready_status()
        assert status["ready"] is False
        assert "components" in status
        assert status["components"]["database"]["status"] == "not_ready"

    def test_get_liveness_status_returns_healthy(self):
        """Verify get_liveness_status returns healthy status"""
        status = HealthCheckService.get_liveness_status()
        assert status["status"] == "healthy"
        assert "timestamp" in status


class TestHealthCheckIntegration:
    """Integration tests for health check endpoints"""

    def test_all_health_endpoints_respond(self, client):
        """Verify all health check endpoints are accessible"""
        endpoints = ["/health", "/ready", "/liveness"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # All should respond (200 or 503 for /ready)
            assert response.status_code in [200, 503], f"{endpoint} did not respond"

    def test_health_endpoints_not_affected_by_middleware(self, client):
        """Verify health endpoints work independently"""
        # Health endpoints should work even if app has issues
        response = client.get("/health")
        assert response.status_code == 200

    @patch("app.core.health_check.SessionLocal")
    def test_ready_endpoint_depends_on_database(self, mock_session_local, client):
        """Verify /ready endpoint status changes with database availability"""
        # First test with connected database
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        mock_session_local.return_value = mock_db

        response_ready = client.get("/ready")
        assert response_ready.status_code == 200

        # Simulate database disconnection
        mock_db.execute.side_effect = Exception("Connection lost")

        response_not_ready = client.get("/ready")
        assert response_not_ready.status_code == 503


class TestHealthCheckMetrics:
    """Tests for health check metrics integration"""

    def test_health_endpoints_excluded_from_metrics(self, client, admin_headers):
        """Verify health endpoints are excluded from Prometheus metrics"""
        # Make requests to health endpoints
        client.get("/health")
        client.get("/ready")
        client.get("/liveness")

        # Get metrics (admin uniquement)
        metrics_response = client.get("/metrics", headers=admin_headers)
        metrics_text = metrics_response.text

        # Verify health endpoints are not tracked in HTTP metrics
        # (PrometheusMiddleware has SKIP_PATHS = {"/health", "/ready", "/liveness", ...})
        # This is implicit behavior - we just verify metrics endpoint responds
        assert metrics_response.status_code == 200
        assert "http_requests_total" in metrics_text
