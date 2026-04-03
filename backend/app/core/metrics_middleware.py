"""
Prometheus metrics middleware for FastAPI.
Collects HTTP request/response metrics automatically.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import MetricsCollector


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that collects Prometheus metrics for all HTTP requests.

    Tracks:
    - Request count by method, endpoint, and status
    - Request duration by method and endpoint
    - Active requests by method
    - Request and response sizes
    - Last request timestamp
    """

    # Endpoints to skip metrics collection (health checks, metrics endpoint)
    SKIP_PATHS = {
        "/health",
        "/healthz",
        "/ready",
        "/liveness",
        "/metrics",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process incoming request, collect metrics, and forward to handler.
        """
        # Skip WebSocket (BaseHTTPMiddleware ne supporte pas le protocole WS)
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # Skip metrics collection for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Get request details
        method = request.method
        path = request.url.path

        # Normalize path for metrics (replace IDs with placeholder)
        endpoint = self._normalize_path(path)

        # Increment active requests
        MetricsCollector.set_active_requests(method, 1)

        try:
            # Record request size if available
            request_size = None
            if request.headers.get("content-length"):
                try:
                    request_size = int(request.headers["content-length"])
                except (ValueError, TypeError):
                    pass

            # Measure request duration
            start_time = time.time()
            response = await call_next(request)
            duration = time.time() - start_time

            # Record response size if available
            response_size = None
            if "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                except (ValueError, TypeError):
                    pass

            # Record metrics
            status = response.status_code
            MetricsCollector.record_http_request(
                method=method,
                endpoint=endpoint,
                status=status,
                duration=duration,
                request_size=request_size,
                response_size=response_size,
            )

            return response

        finally:
            # Decrement active requests
            MetricsCollector.set_active_requests(method, -1)

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Normalize URL path for metrics aggregation.
        Replace numeric IDs with {id} placeholder.

        Examples:
            /campaigns/123 → /campaigns/{id}
            /audits/456/sites → /audits/{id}/sites
        """
        import re

        # Replace consecutive digits with {id}
        normalized = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        return normalized
