"""
Sentry SDK integration for error tracking and monitoring.
Captures and reports exceptions to Sentry for centralized error management.
"""

import logging
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


logger = logging.getLogger(__name__)


def init_sentry(
    dsn: Optional[str],
    environment: str,
    version: str,
    enable_tracing: bool = False,
    traces_sample_rate: float = 0.1,
) -> bool:
    """
    Initialize Sentry SDK for error tracking and monitoring.
    
    Args:
        dsn: Sentry DSN (Data Source Name). If None, Sentry is disabled.
        environment: Environment name (development, staging, production)
        version: Application version
        enable_tracing: Enable performance tracing (generates more data)
        traces_sample_rate: Fraction of transactions to trace (0.0 - 1.0)
    
    Returns:
        True if Sentry was successfully initialized, False if disabled (DSN is None)
    
    Example:
        >>> init_sentry(
        ...     dsn="https://key@sentry.io/project",
        ...     environment="production",
        ...     version="1.0.0"
        ... )
        True
    """
    if not dsn:
        logger.info("Sentry DSN not configured. Error tracking disabled.")
        return False

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=version,
            
            # Integrations for capturing errors from different layers
            integrations=[
                # FastAPI/Starlette HTTP integration
                StarletteIntegration(),
                FastApiIntegration(),
                
                # SQLAlchemy database integration (captures slow queries)
                SqlalchemyIntegration(),
                
                # Logging integration (captures logs as breadcrumbs)
                LoggingIntegration(
                    level=logging.INFO,        # Capture logger.info and above
                    event_level=logging.ERROR  # Send as event only ERROR and above
                ),
            ],
            
            # Performance monitoring settings
            traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
            
            # Error filtering - don't send specific exceptions
            ignore_errors=[
                # HTTP client errors (not our fault)
                "aiohttp.ClientError",
                "httpx.RequestError",
                
                # HTTP status errors we handle
                "fastapi.HTTPException",
                
                # Known harmless errors
                "KeyboardInterrupt",
                "SystemExit",
            ],
            
            # Before sending transaction or event to Sentry
            before_send=before_send_hook,
            before_send_transaction=before_send_transaction_hook,
            
            # Extra configuration
            attach_stacktrace=True,              # Include stack traces with all messages
            include_local_variables=False,       # Don't include local vars (security)
            max_breadcrumbs=100,                 # Keep last 100 events
            server_name=f"app-{environment}",    # Identify this server instance
        )
        
        logger.info(
            f"✓ Sentry initialized successfully (environment={environment}, version={version})"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def before_send_hook(event: dict, hint: dict) -> Optional[dict]:
    """
    Hook called before sending event to Sentry.
    Used to filter sensitive data or skip certain errors.
    
    Returns:
        Modified event, or None to skip sending the event
    """
    # Don't send if it's just a warning or debug message
    if event.get("level") in ["warning", "debug"]:
        return None
    
    # Skip if this is a harmless HTTP 4xx error
    if event.get("level") == "error":
        exc = hint.get("exc_info")
        if exc and exc[0]:
            error_type = exc[0].__name__
            # Skip client errors we've already logged
            if error_type in ["HTTPException", "ValidationError"]:
                return None
    
    return event


def before_send_transaction_hook(transaction: dict, hint: dict) -> Optional[dict]:
    """
    Hook called before sending transaction to Sentry (for performance monitoring).
    Used to filter sensitive data or skip certain transactions.
    
    Returns:
        Modified transaction, or None to skip sending
    """
    # Skip health check transactions
    op = transaction.get("contexts", {}).get("trace", {}).get("op")
    transaction_name = transaction.get("transaction", "")
    
    if "/health" in transaction_name or "/metrics" in transaction_name:
        return None
    
    return transaction


def capture_exception(exc: Exception, level: str = "error", **kwargs):
    """
    Manually capture an exception to Sentry.
    
    Args:
        exc: Exception to capture
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context data
    
    Example:
        >>> try:
        ...     do_something()
        ... except Exception as e:
        ...     capture_exception(e, level="error", operation="do_something")
    """
    with sentry_sdk.push_scope() as scope:
        # Set the level
        scope.level = level
        
        # Add extra context
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        
        # Send the exception
        sentry_sdk.capture_exception(exc)


def capture_message(message: str, level: str = "info", **kwargs):
    """
    Manually capture a message to Sentry.
    
    Args:
        message: Message to send
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context data
    
    Example:
        >>> capture_message(
        ...     "Campaign completed",
        ...     level="info",
        ...     campaign_id=123,
        ...     duration_seconds=45.2
        ... )
    """
    with sentry_sdk.push_scope() as scope:
        # Set the level
        scope.level = level
        
        # Add extra context
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        
        # Send the message
        sentry_sdk.capture_message(message)


def set_user_context(user_id: Optional[str] = None, email: Optional[str] = None, **kwargs):
    """
    Set user context for error tracking.
    Associates errors with specific users.
    
    Args:
        user_id: Unique user identifier
        email: User email address
        **kwargs: Additional user attributes
    
    Example:
        >>> set_user_context(
        ...     user_id="user_123",
        ...     email="user@example.com",
        ...     role="admin"
        ... )
    """
    with sentry_sdk.push_scope() as scope:
        if user_id or email:
            scope.set_user({
                "id": user_id,
                "email": email,
                **kwargs
            })


def set_request_context(request_id: str, method: str, path: str, **kwargs):
    """
    Set HTTP request context for error tracking.
    
    Args:
        request_id: Unique request identifier
        method: HTTP method
        path: Request path
        **kwargs: Additional context
    
    Example:
        >>> set_request_context(
        ...     request_id="req_123",
        ...     method="POST",
        ...     path="/campaigns",
        ...     ip_address="192.168.1.1"
        ... )
    """
    with sentry_sdk.push_scope() as scope:
        scope.set_context("request", {
            "request_id": request_id,
            "method": method,
            "path": path,
            **kwargs
        })


def set_transaction_name(name: str):
    """
    Set transaction name for performance monitoring.
    
    Args:
        name: Transaction/operation name
    
    Example:
        >>> set_transaction_name("POST /campaigns")
    """
    sentry_sdk.set_transaction_name(name)


def add_breadcrumb(category: str, message: str, level: str = "info", **kwargs):
    """
    Add a breadcrumb to the current transaction context.
    Breadcrumbs help understand what happened before an error.
    
    Args:
        category: Breadcrumb category (e.g. "auth", "database", "http")
        message: Breadcrumb message
        level: Severity level (debug, info, warning, error)
        **kwargs: Additional data
    
    Example:
        >>> add_breadcrumb(
        ...     category="assessment",
        ...     message="Campaign assessment completed",
        ...     level="info",
        ...     campaign_id=123,
        ...     score=85.5
        ... )
    """
    sentry_sdk.add_breadcrumb(
        category=category,
        message=message,
        level=level,
        data=kwargs,
    )


# ────────────────────────────────────────────────────────────────────────
# Context Managers for transaction tracking
# ────────────────────────────────────────────────────────────────────────


class operation_context:
    """
    Context manager to track an operation in Sentry.
    Automatically records operation duration and captures any exceptions.
    
    Example:
        >>> with operation_context("assessment_scoring", assessment_id=123):
        ...     result = calculate_score(assessment)
        ...     return result
    """
    
    def __init__(self, operation_name: str, **context_data):
        self.operation_name = operation_name
        self.context_data = context_data
        self.transaction = None
    
    def __enter__(self):
        # Set transaction name
        set_transaction_name(self.operation_name)
        
        # Add operation as breadcrumb
        add_breadcrumb(
            category="operation",
            message=f"Starting: {self.operation_name}",
            **self.context_data
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Capture the exception
            capture_exception(
                exc_val,
                level="error",
                operation=self.operation_name,
                **self.context_data
            )
            
            # Add error breadcrumb
            add_breadcrumb(
                category="operation",
                message=f"Failed: {self.operation_name}",
                level="error",
                error=str(exc_val),
                **self.context_data
            )
        else:
            # Add success breadcrumb
            add_breadcrumb(
                category="operation",
                message=f"Completed: {self.operation_name}",
                level="info",
                **self.context_data
            )
        
        return False  # Re-raise any exception


# ────────────────────────────────────────────────────────────────────────
# Health Check
# ────────────────────────────────────────────────────────────────────────


def test_sentry_connection() -> bool:
    """
    Test connection to Sentry by sending a test message.
    Useful for verifying configuration during startup.
    
    Returns:
        True if message was sent successfully
    """
    try:
        sentry_sdk.capture_message("🔍 Sentry integration test", level="info")
        logger.info("✓ Sentry connection test successful")
        return True
    except Exception as e:
        logger.error(f"✗ Sentry connection test failed: {e}")
        return False
