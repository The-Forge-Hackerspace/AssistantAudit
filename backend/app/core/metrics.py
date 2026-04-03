"""
Prometheus metrics for monitoring application performance and health.
"""

import time
from typing import Any, Callable

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Create a custom registry for application metrics
app_registry = CollectorRegistry()

# ────────────────────────────────────────────────────────────────────────
# HTTP Request Metrics
# ────────────────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=app_registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=app_registry,
)

http_active_requests = Gauge(
    "http_active_requests",
    "Number of active HTTP requests",
    ["method"],
    registry=app_registry,
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request payload size in bytes",
    ["method", "endpoint"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000),
    registry=app_registry,
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response payload size in bytes",
    ["method", "endpoint"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000),
    registry=app_registry,
)

# ────────────────────────────────────────────────────────────────────────
# Database Metrics
# ────────────────────────────────────────────────────────────────────────

db_queries_total = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table"],
    registry=app_registry,
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=app_registry,
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    registry=app_registry,
)

db_connection_pool_checked_out = Gauge(
    "db_connection_pool_checked_out",
    "Database connections checked out from pool",
    registry=app_registry,
)

# ────────────────────────────────────────────────────────────────────────
# Business Logic Metrics
# ────────────────────────────────────────────────────────────────────────

assessment_campaigns_total = Counter(
    "assessment_campaigns_total",
    "Total assessment campaigns created",
    ["status"],
    registry=app_registry,
)

assessment_results_total = Counter(
    "assessment_results_total",
    "Total assessment results recorded",
    ["compliance_status"],
    registry=app_registry,
)

assessment_compliance_score = Histogram(
    "assessment_compliance_score",
    "Compliance score distribution",
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
    registry=app_registry,
)

active_assessments = Gauge(
    "active_assessments",
    "Number of in-progress assessments",
    registry=app_registry,
)

audit_operations_total = Counter(
    "audit_operations_total",
    "Total audit operations (create, update, delete)",
    ["operation"],
    registry=app_registry,
)

# ────────────────────────────────────────────────────────────────────────
# Error Metrics
# ────────────────────────────────────────────────────────────────────────

errors_total = Counter(
    "errors_total",
    "Total application errors",
    ["error_type", "endpoint"],
    registry=app_registry,
)

validation_errors_total = Counter(
    "validation_errors_total",
    "Total validation errors",
    ["field", "error_type"],
    registry=app_registry,
)

auth_failures_total = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["reason"],
    registry=app_registry,
)

# ────────────────────────────────────────────────────────────────────────
# System Metrics
# ────────────────────────────────────────────────────────────────────────

app_info = Counter(
    "app_info",
    "Application info",
    ["version", "environment"],
    registry=app_registry,
)

last_request_timestamp = Gauge(
    "last_request_timestamp",
    "Timestamp of last HTTP request",
    registry=app_registry,
)

# ────────────────────────────────────────────────────────────────────────
# Metrics Collectors & Decorators
# ────────────────────────────────────────────────────────────────────────


class MetricsCollector:
    """Helper class for collecting metrics"""

    @staticmethod
    def record_http_request(
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        request_size: int = None,
        response_size: int = None,
    ):
        """Record HTTP request metrics"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        if request_size:
            http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(request_size)
        if response_size:
            http_response_size_bytes.labels(method=method, endpoint=endpoint).observe(response_size)
        last_request_timestamp.set(time.time())

    @staticmethod
    def record_db_query(operation: str, table: str, duration: float):
        """Record database query metrics"""
        db_queries_total.labels(operation=operation, table=table).inc()
        db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

    @staticmethod
    def record_assessment_result(compliance_status: str, score: float = None):
        """Record assessment result metrics"""
        assessment_results_total.labels(compliance_status=compliance_status).inc()
        if score is not None:
            assessment_compliance_score.observe(score)

    @staticmethod
    def record_audit_operation(operation: str):
        """Record audit operation metrics"""
        audit_operations_total.labels(operation=operation).inc()

    @staticmethod
    def record_error(error_type: str, endpoint: str = None):
        """Record error metrics"""
        errors_total.labels(error_type=error_type, endpoint=endpoint or "unknown").inc()

    @staticmethod
    def record_auth_failure(reason: str):
        """Record authentication failure metrics"""
        auth_failures_total.labels(reason=reason).inc()

    @staticmethod
    def set_active_requests(http_method: str, count: int):
        """Set active request gauge"""
        http_active_requests.labels(method=http_method).set(count)

    @staticmethod
    def set_active_assessments(count: int):
        """Set active assessments gauge"""
        active_assessments.set(count)

    @staticmethod
    def set_db_pool_stats(size: int, checked_out: int):
        """Set database pool statistics"""
        db_connection_pool_size.set(size)
        db_connection_pool_checked_out.set(checked_out)


def metrics_timer(operation: str, table: str = "unknown") -> Callable:
    """
    Decorator to time database operations.

    Usage:
        @metrics_timer("SELECT", "users")
        def get_user(user_id):
            ...
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                MetricsCollector.record_db_query(operation, table, duration)

        return wrapper

    return decorator


# ────────────────────────────────────────────────────────────────────────
# Metrics Export
# ────────────────────────────────────────────────────────────────────────


def get_metrics() -> bytes:
    """
    Generate Prometheus-format metrics output.

    Returns:
        Bytes containing metrics in Prometheus exposition format
    """
    return generate_latest(app_registry)


def init_app_metrics(version: str, environment: str):
    """
    Initialize application metrics.

    Args:
        version: Application version
        environment: Environment name (dev, test, staging, prod)
    """
    app_info.labels(version=version, environment=environment).inc()
