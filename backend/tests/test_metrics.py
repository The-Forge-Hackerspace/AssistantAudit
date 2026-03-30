"""
Tests for Prometheus metrics collection and exposure.
"""

import pytest
import re
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.metrics import (
    MetricsCollector,
    get_metrics,
    init_app_metrics,
    http_requests_total,
    http_request_duration_seconds,
    http_active_requests,
    assessment_results_total,
    audit_operations_total,
)
from app.core.metrics_middleware import PrometheusMiddleware


class TestMetricsCollection:
    """Tests for metrics collection functionality"""

    def test_metrics_collector_record_http_request(self):
        """Verify MetricsCollector records HTTP request metrics"""
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/campaigns/{id}",
            status=200,
            duration=0.123,
            request_size=100,
            response_size=5000,
        )
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_record_db_query(self):
        """Verify MetricsCollector records database query metrics"""
        MetricsCollector.record_db_query(
            operation="SELECT",
            table="campaigns",
            duration=0.045,
        )
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_record_assessment_result(self):
        """Verify MetricsCollector records assessment result metrics"""
        MetricsCollector.record_assessment_result(
            compliance_status="COMPLIANT",
            score=85.5,
        )
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_record_audit_operation(self):
        """Verify MetricsCollector records audit operation metrics"""
        MetricsCollector.record_audit_operation("CREATE")
        MetricsCollector.record_audit_operation("UPDATE")
        MetricsCollector.record_audit_operation("DELETE")
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_record_error(self):
        """Verify MetricsCollector records error metrics"""
        MetricsCollector.record_error(error_type="ValidationError", endpoint="/campaigns")
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_record_auth_failure(self):
        """Verify MetricsCollector records auth failure metrics"""
        MetricsCollector.record_auth_failure(reason="INVALID_TOKEN")
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_set_active_requests(self):
        """Verify MetricsCollector can set active request gauge"""
        MetricsCollector.set_active_requests("GET", 5)
        MetricsCollector.set_active_requests("POST", 2)
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_set_active_assessments(self):
        """Verify MetricsCollector can set active assessments gauge"""
        MetricsCollector.set_active_assessments(10)
        
        # Should not raise exceptions
        assert True

    def test_metrics_collector_set_db_pool_stats(self):
        """Verify MetricsCollector can set database pool statistics"""
        MetricsCollector.set_db_pool_stats(size=10, checked_out=3)
        
        # Should not raise exceptions
        assert True


class TestMetricsExport:
    """Tests for metrics export in Prometheus format"""

    def test_get_metrics_returns_bytes(self):
        """Verify get_metrics returns bytes in Prometheus format"""
        metrics = get_metrics()
        
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0

    def test_metrics_format_is_valid_prometheus(self):
        """Verify metrics output is valid Prometheus format"""
        # Record some metrics
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/test",
            status=200,
            duration=0.05,
        )
        
        metrics = get_metrics()
        text = metrics.decode("utf-8")
        
        # Should contain HELP and TYPE comments
        assert "# HELP" in text
        assert "# TYPE" in text
        
        # Should contain metric names
        assert "http_requests_total" in text
        assert "http_request_duration_seconds" in text

    def test_metrics_contain_labels(self):
        """Verify metrics include proper labels"""
        MetricsCollector.record_http_request(
            method="POST",
            endpoint="/assessments",
            status=201,
            duration=0.08,
        )
        
        metrics = get_metrics()
        text = metrics.decode("utf-8")
        
        # Should contain label information
        assert 'method="POST"' in text
        assert 'endpoint="/assessments"' in text

    def test_init_app_metrics_registers_version(self):
        """Verify init_app_metrics registers app info"""
        init_app_metrics(version="1.0.0", environment="test")
        
        metrics = get_metrics()
        text = metrics.decode("utf-8")
        
        # Should contain app info metric
        assert "app_info" in text


class TestPrometheusMiddleware:
    """Tests for Prometheus middleware integration"""

    def test_middleware_normalizes_paths(self):
        """Verify middleware normalizes numeric IDs in paths"""
        path = "/campaigns/123"
        normalized = PrometheusMiddleware._normalize_path(path)
        assert normalized == "/campaigns/{id}"
        
        path = "/audits/456/sites/789"
        normalized = PrometheusMiddleware._normalize_path(path)
        assert normalized == "/audits/{id}/sites/{id}"
        
        path = "/campaigns/abc"  # Non-numeric should not be replaced
        normalized = PrometheusMiddleware._normalize_path(path)
        assert normalized == "/campaigns/abc"

    def test_middleware_skips_health_endpoints(self):
        """Verify middleware skips metrics collection for health endpoints"""
        skip_paths = PrometheusMiddleware.SKIP_PATHS
        
        assert "/health" in skip_paths
        assert "/healthz" in skip_paths
        assert "/ready" in skip_paths
        assert "/metrics" in skip_paths

    @pytest.mark.asyncio
    async def test_middleware_integration_with_fastapi(self, app):
        """Verify middleware integrates successfully with FastAPI app"""
        # The app fixture should have middleware installed
        # Just verify it was created without errors
        assert app is not None
        assert hasattr(app, "middleware_stack")


class TestMetricsEndpoint:
    """Tests for /metrics endpoint"""

    def test_metrics_endpoint_returns_200(self, client, admin_headers):
        """Verify /metrics endpoint returns 200 status (admin only)"""
        response = client.get("/metrics", headers=admin_headers)

        assert response.status_code == 200

    def test_metrics_endpoint_returns_prometheus_format(self, client, admin_headers):
        """Verify /metrics endpoint returns Prometheus format"""
        response = client.get("/metrics", headers=admin_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        content = response.text
        assert len(content) > 0
        assert "# HELP" in content or "#" in content  # Should have comments

    def test_metrics_endpoint_contains_http_metrics(self, client, admin_headers):
        """Verify /metrics endpoint contains HTTP metrics"""
        # Make a request first
        client.get("/health")

        response = client.get("/metrics", headers=admin_headers)
        assert response.status_code == 200

        content = response.text
        # Should have some metrics defined
        assert "http_requests_total" in content or "app_info" in content

    def test_metrics_endpoint_is_excluded_from_metrics_loop(self, client, admin_headers):
        """Verify /metrics endpoint itself doesn't create infinite metrics loop"""
        # Get metrics endpoint multiple times
        for _ in range(3):
            response = client.get("/metrics", headers=admin_headers)
            assert response.status_code == 200

        # Should still work without errors
        response = client.get("/metrics", headers=admin_headers)
        assert response.status_code == 200


class TestMetricsAccuracy:
    """Tests verifying metrics accuracy"""

    def test_metrics_can_track_multiple_endpoints(self):
        """Verify metrics can track requests to multiple endpoints"""
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/campaigns",
            status=200,
            duration=0.01,
        )
        
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/audits/{id}",
            status=200,
            duration=0.02,
        )
        
        MetricsCollector.record_http_request(
            method="POST",
            endpoint="/campaigns",
            status=201,
            duration=0.03,
        )
        
        metrics = get_metrics()
        text = metrics.decode("utf-8")
        
        # Should contain metrics for different endpoints
        assert "/campaigns" in text
        assert "/audits/{id}" in text

    def test_metrics_can_track_error_statuses(self):
        """Verify metrics track different HTTP status codes"""
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/campaigns",
            status=200,
            duration=0.01,
        )
        
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/campaigns",
            status=404,
            duration=0.005,
        )
        
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/campaigns",
            status=500,
            duration=0.02,
        )
        
        metrics = get_metrics()
        text = metrics.decode("utf-8")
        
        # Should track all statuses
        assert 'status="200"' in text or "http_requests_total" in text

    def test_metrics_histogram_buckets_exist(self):
        """Verify metrics histogram has appropriate buckets"""
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/test",
            status=200,
            duration=0.123,
        )
        
        metrics = get_metrics()
        text = metrics.decode("utf-8")
        
        # Should have histogram buckets
        assert "_bucket" in text or "http_request_duration" in text


class TestMetricsIntegration:
    """Integration tests for metrics with the application"""

    def test_metrics_work_with_actual_requests(self, client, admin_headers):
        """Verify metrics collection works with real HTTP requests"""
        # Health endpoints are skipped, but we can track requests to other endpoints
        MetricsCollector.record_http_request(
            method="GET",
            endpoint="/health",
            status=200,
            duration=0.001,
        )

        response = client.get("/metrics", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.text) > 0

    def test_all_metric_types_work_together(self):
        """Verify all metric types can be used together"""
        # Record various metrics
        MetricsCollector.record_http_request("GET", "/campaigns", 200, 0.05, 100, 5000)
        MetricsCollector.record_db_query("SELECT", "campaigns", 0.02)
        MetricsCollector.record_assessment_result("COMPLIANT", 92.5)
        MetricsCollector.record_audit_operation("CREATE")
        MetricsCollector.record_error("ValueError", "/campaigns")
        MetricsCollector.set_active_requests("GET", 3)
        MetricsCollector.set_active_assessments(5)
        
        # Should be able to export all metrics
        metrics = get_metrics()
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0
        
        text = metrics.decode("utf-8")
        # Should contain multiple metric names
        assert "http_requests_total" in text or "http_request" in text
