"""
Structured JSON logging configuration for AssistantAudit.
Provides production-ready JSON logging with context support and filtering.
"""

import json
import logging
import sys
from logging import LogRecord
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

from .config import get_settings


# ────────────────────────────────────────────────────────────────────────
# Custom JSON Formatter
# ────────────────────────────────────────────────────────────────────────


class ContextualJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that:
    - Adds contextual information (environment, version, etc.)
    - Extracts useful fields from log records
    - Preserves stack traces for exceptions
    """

    def add_fields(
        self, log_record: Dict[str, Any], record: LogRecord, message_dict: Dict[str, Any]
    ) -> None:
        """Add custom fields to JSON log record"""
        super().add_fields(log_record, record, message_dict)

        # Add environment context
        settings = get_settings()
        log_record["environment"] = settings.ENV
        log_record["app_name"] = settings.APP_NAME
        log_record["app_version"] = settings.APP_VERSION

        # Add timestamp (ISO format)
        log_record["timestamp"] = self.formatTime(record, self.datefmt)

        # Add level name
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add request ID if available (from context)
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        # Add user ID if available (from context)
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        # Add operation type if available (audit trail)
        if hasattr(record, "operation"):
            log_record["operation"] = record.operation

        # Add status code if available
        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code

        # Add duration if available
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms

        # Preserve exception info
        if record.exc_info and not log_record.get("exc_info"):
            log_record["exc_info"] = self.formatException(record.exc_info)


# ────────────────────────────────────────────────────────────────────────
# Logger Setup
# ────────────────────────────────────────────────────────────────────────


def configure_structured_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging for the application.

    Args:
        log_level: Logging level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    """
    settings = get_settings()

    # Create JSON formatter
    formatter = ContextualJsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(message)s",
        timestamp=True,
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout for JSON logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler for persistent logs (if enabled)
    if settings.LOG_DIR:
        from pathlib import Path

        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "assistantaudit.json"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress overly verbose libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


# ────────────────────────────────────────────────────────────────────────
# Context Management for Logging
# ────────────────────────────────────────────────────────────────────────


class LogContext:
    """Context manager for adding structured logging context"""

    _contexts: dict = {}

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        """Set request ID for current context"""
        cls._contexts["request_id"] = request_id

    @classmethod
    def set_user_id(cls, user_id: int) -> None:
        """Set user ID for current context"""
        cls._contexts["user_id"] = user_id

    @classmethod
    def set_operation(cls, operation: str) -> None:
        """Set operation type for current context"""
        cls._contexts["operation"] = operation

    @classmethod
    def clear(cls) -> None:
        """Clear all context"""
        cls._contexts.clear()

    @classmethod
    def get(cls) -> dict:
        """Get current context"""
        return cls._contexts.copy()
