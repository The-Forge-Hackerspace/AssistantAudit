"""
Global exception handlers pour FastAPI.
Centralise la gestion des erreurs avec des réponses standardisées.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.errors import AppError, BusinessRuleError, ConflictError, ForbiddenError, NotFoundError

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

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def forbidden_error_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Request, exc: ConflictError):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(BusinessRuleError)
    async def business_rule_error_handler(request: Request, exc: BusinessRuleError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Gestionnaire d'exception generique pour tous les autres erreurs non gerees."""
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}",
            exc_info=exc,
        )

        # Ne jamais exposer str(exc) ni traceback au client : ces données peuvent contenir
        # des chemins internes, du SQL, des secrets. Le détail reste dans les logs serveur.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Une erreur interne s'est produite.",
                "error_type": "internal_server_error",
            },
        )
