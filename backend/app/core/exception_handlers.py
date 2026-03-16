"""
Global exception handlers pour FastAPI.
Centralise la gestion des erreurs avec des réponses standardisées.
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError

from .config import get_settings

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
        """Gère les erreurs SQLAlchemy génériques."""
        logger.error(f"SQLAlchemy error: {exc}")
        # Never expose DB internals to the client — details are already logged server-side
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erreur de base de données", "error_type": "database_error"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Gestionnaire d'exception générique pour tous les autres erreurs non gérées."""
        # Log l'erreur complète server-side (always — no information is lost)
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}",
            exc_info=exc,
        )

        settings = get_settings()

        # Only expose exception message in development — NEVER in production
        if settings.ENV == "development":
            detail = str(exc)
        else:
            detail = "Une erreur interne s'est produite. Cette erreur a été enregistrée."

        # Never send traceback to client — it's already in server logs
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": detail,
                "error_type": "internal_server_error",
            },
        )
