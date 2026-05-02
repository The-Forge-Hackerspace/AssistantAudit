"""
Structured JSON logging configuration for AssistantAudit.
Provides production-ready JSON logging with context support and filtering.
"""

import hashlib
import ipaddress
import logging
import sys
from contextvars import ContextVar
from logging import LogRecord
from typing import Any, Dict

from pythonjsonlogger import json as jsonlogger

from .config import get_settings

# ────────────────────────────────────────────────────────────────────────
# PII Masking Helpers (TOS-82)
# ────────────────────────────────────────────────────────────────────────


def hash_username(username: str | None) -> str:
    """Hash un username via SHA-256 et retourne les 12 premiers chars hex.

    Sufficant pour corrélation logs sans révéler la valeur claire (cf NIST SP 800-63B).
    """
    if not username:
        return ""
    return hashlib.sha256(username.encode("utf-8")).hexdigest()[:12]


def mask_email(email: str | None) -> str:
    """Masque un email : `user@example.com` -> `u***@example.com`.

    Conserve le domaine complet (utile pour debug) et la première lettre du local-part.
    """
    if not email or "@" not in email:
        return ""
    local, _, domain = email.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def mask_ip(ip: str | None) -> str:
    """Masque un IP en zéro-isant le dernier octet IPv4 (/24) ou les 80 derniers bits IPv6 (/48).

    Retourne `""` si l'entrée n'est pas une IP valide.
    """
    if not ip:
        return ""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ""
    if isinstance(addr, ipaddress.IPv4Address):
        parts = str(addr).split(".")
        return ".".join(parts[:3] + ["0"])
    # IPv6 : conserver les 3 premiers segments (48 bits), reset le reste.
    segments = addr.exploded.split(":")
    return ":".join(segments[:3] + ["0", "0", "0", "0", "0"])

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

    def add_fields(self, log_record: Dict[str, Any], record: LogRecord, message_dict: Dict[str, Any]) -> None:
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
    # TOS-102 / AC-2: rotation via RotatingFileHandler pour éviter l'accumulation
    # de logs > 1 GB en prod. Taille max et nombre de backups configurables
    # via env (défauts: 50 MB × 10 backups = 500 MB max sur disque).
    if settings.LOG_DIR:
        from logging.handlers import RotatingFileHandler
        from pathlib import Path

        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "assistantaudit.json"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=settings.LOG_FILE_MAX_BYTES,
            backupCount=settings.LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
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


_request_id: ContextVar[str] = ContextVar("request_id", default="")
_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
_operation: ContextVar[str] = ContextVar("operation", default="")


class LogContext:
    """Context manager for adding structured logging context"""

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        """Set request ID for current context"""
        _request_id.set(request_id)

    @classmethod
    def push_request_id(cls, request_id: str):
        """Set request ID and return the ContextVar Token for later reset() (TOS-82).

        À utiliser dans un middleware avec un bloc try/finally pour éviter le leak
        de l'ID entre requêtes partageant le même thread (threadpool FastAPI).
        """
        return _request_id.set(request_id)

    @classmethod
    def reset_request_id(cls, token) -> None:
        """Reset the request ID ContextVar via the Token returned by push_request_id."""
        _request_id.reset(token)

    @classmethod
    def set_user_id(cls, user_id: int) -> None:
        """Set user ID for current context"""
        _user_id.set(user_id)

    @classmethod
    def set_operation(cls, operation: str) -> None:
        """Set operation type for current context"""
        _operation.set(operation)

    @classmethod
    def clear(cls) -> None:
        """Clear all context"""
        _request_id.set("")
        _user_id.set(None)
        _operation.set("")

    @classmethod
    def get(cls) -> dict:
        """Get current context"""
        ctx: dict = {}
        rid = _request_id.get()
        if rid:
            ctx["request_id"] = rid
        uid = _user_id.get()
        if uid is not None:
            ctx["user_id"] = uid
        op = _operation.get()
        if op:
            ctx["operation"] = op
        return ctx
