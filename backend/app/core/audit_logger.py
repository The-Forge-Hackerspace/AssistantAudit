"""
Audit trail middleware for tracking API operations and changes.
Logs all HTTP requests/responses and business-critical operations.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging_config import LogContext

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────
# HTTP Audit Middleware
# ────────────────────────────────────────────────────────────────────────


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging of HTTP requests and responses.
    Tracks:
    - Request metadata (method, path, query params, user)
    - Response status and timing
    - Error details
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit information"""
        # BaseHTTPMiddleware casse les WebSocket — les laisser passer
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())
        LogContext.set_request_id(request_id)

        # Extract user info if available
        try:
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                LogContext.set_user_id(user_id)
        except Exception:
            pass

        # Skip health check endpoints from audit logging
        if request.url.path in ["/health", "/healthz", "/ready", "/liveness"]:
            return await call_next(request)

        # Request start
        start_time = time.time()

        # Try to capture request body for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    try:
                        body.decode("utf-8")[:500]  # Validate decodable
                    except UnicodeDecodeError:
                        pass
                # Ensure request body is accessible later
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception as e:
                self.logger.debug(f"Could not capture request body: {e}")

        # Log request received
        self.logger.info(
            "HTTP request received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )

        # Call the actual endpoint
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "HTTP request failed with exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            raise

        # Log response
        duration_ms = (time.time() - start_time) * 1000
        log_level = "info" if response.status_code < 400 else "warning"
        
        log_method = getattr(self.logger, log_level)
        log_method(
            "HTTP response sent",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        # Add request ID to response header for tracing
        response.headers["X-Request-ID"] = request_id

        return response


# ────────────────────────────────────────────────────────────────────────
# Business Operation Logger
# ────────────────────────────────────────────────────────────────────────


class BusinessAuditLogger:
    """Logger for business-critical operations (create, update, delete, state changes)"""

    def __init__(self, logger_name: str = "audit") -> None:
        self.logger = logging.getLogger(logger_name)

    def log_create(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int | None = None,
        details: dict = None,
    ) -> None:
        """Log entity creation"""
        self.logger.info(
            f"Created {entity_type}",
            extra={
                "operation": "CREATE",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "details": details or {},
            },
        )

    def log_update(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int | None = None,
        changes: dict = None,
    ) -> None:
        """Log entity modification"""
        self.logger.info(
            f"Updated {entity_type}",
            extra={
                "operation": "UPDATE",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "changes": changes or {},
            },
        )

    def log_delete(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int | None = None,
    ) -> None:
        """Log entity deletion"""
        self.logger.info(
            f"Deleted {entity_type}",
            extra={
                "operation": "DELETE",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
            },
        )

    def log_status_change(
        self,
        entity_type: str,
        entity_id: int,
        old_status: str,
        new_status: str,
        user_id: int | None = None,
    ) -> None:
        """Log entity status change"""
        self.logger.info(
            f"Status changed for {entity_type}",
            extra={
                "operation": "STATUS_CHANGE",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "old_status": old_status,
                "new_status": new_status,
                "user_id": user_id,
            },
        )

    def log_export(
        self,
        entity_type: str,
        format: str,
        user_id: int | None = None,
        count: int = 0,
    ) -> None:
        """Log data export"""
        self.logger.info(
            f"Exported {entity_type}",
            extra={
                "operation": "EXPORT",
                "entity_type": entity_type,
                "format": format,
                "user_id": user_id,
                "count": count,
            },
        )

    def log_action(
        self,
        action: str,
        user_id: int | None = None,
        details: dict = None,
    ) -> None:
        """Log custom business action"""
        self.logger.info(
            f"Action: {action}",
            extra={
                "operation": action.upper(),
                "user_id": user_id,
                "details": details or {},
            },
        )


# Singleton instance
audit_logger = BusinessAuditLogger()


# ────────────────────────────────────────────────────────────────────────
# Security: RBAC Access Denied Logger
# ────────────────────────────────────────────────────────────────────────

_security_logger = logging.getLogger("security")


def log_access_denied(
    user_id: int,
    resource_type: str,
    resource_id: int | str,
    action: str = "read",
) -> None:
    """Log un échec d'ownership check pour monitoring sécurité."""
    _security_logger.warning(
        "access_denied: user=%s resource=%s/%s action=%s",
        user_id, resource_type, resource_id, action,
    )
