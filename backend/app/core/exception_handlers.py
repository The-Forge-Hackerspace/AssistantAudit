"""
Global exception handlers pour FastAPI.
Centralise la gestion des erreurs avec des réponses standardisées.
"""

import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class ValidationErrorResponse:
    """Réponse standardisée pour les erreurs de validation."""

    def __init__(self, detail: str, errors: list = None):
        self.detail = detail
        self.errors = errors or []


def register_exception_handlers(app: FastAPI) -> None:
    """Enregistre tous les gestionnaires d'exceptions globaux."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Gère les erreurs de validation métier."""
        logger.warning(f"ValueError: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_type": "validation_error"},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """Gère les violations de contraintes de base de données."""
        logger.warning(f"IntegrityError: {exc.orig}")
        detail = "Violation d'intégrité : la ressource existe déjà ou les données sont invalides"
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": detail, "error_type": "integrity_error"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        """Gere les erreurs SQLAlchemy generiques."""
        logger.error(f"SQLAlchemy error: {exc}")
        # Ne jamais exposer les details SQL au client
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erreur de base de donnees", "error_type": "database_error"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Gestionnaire d'exception generique pour tous les autres erreurs non gerees."""
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}",
            exc_info=exc,
        )

        # En dev (DEBUG), retourner le detail ; en production, message generique seul
        from app.core.config import get_settings

        _env = get_settings().ENV
        if _env == "development":
            content = {
                "detail": str(exc),
                "error_type": "internal_server_error",
                "traceback": traceback.format_exc(),
            }
        else:
            content = {
                "detail": "Une erreur interne s'est produite.",
                "error_type": "internal_server_error",
            }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )
