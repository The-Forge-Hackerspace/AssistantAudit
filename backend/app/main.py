"""
Point d'entrée de l'application FastAPI — AssistantAudit v2.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import get_settings
from .core.database import create_all_tables, SessionLocal
from .core.logging_config import configure_structured_logging
from .core.audit_logger import AuditLoggingMiddleware
from .core.metrics import init_app_metrics, get_metrics
from .core.metrics_middleware import PrometheusMiddleware
from .core.sentry_integration import init_sentry
from .core.health_check import HealthCheckService

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle de l'application : démarrage et arrêt"""
    # Configure structured JSON logging
    configure_structured_logging(settings.LOG_LEVEL)
    logger = logging.getLogger(__name__)
    
    # Initialize Prometheus metrics
    init_app_metrics(version=settings.APP_VERSION, environment=settings.ENV)
    
    # Initialize Sentry error tracking (if DSN configured)
    init_sentry(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENV,
        version=settings.APP_VERSION,
        enable_tracing=settings.SENTRY_TRACING_ENABLED,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )

    # Création des tables en développement
    if settings.ENV == "development":
        logger.info("Mode développement : création des tables...")
        create_all_tables()

    # Créer le dossier uploads
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # Créer le dossier data (stockage des pièces jointes)
    data_dir = Path(settings.FRAMEWORKS_DIR).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Créer le dossier frameworks
    Path(settings.FRAMEWORKS_DIR).mkdir(parents=True, exist_ok=True)

    # Auto-sync des référentiels YAML → BDD au démarrage
    from .services.framework_service import FrameworkService
    db = SessionLocal()
    try:
        sync_result = FrameworkService.sync_from_directory(db, settings.FRAMEWORKS_DIR)
        total = sync_result['imported'] + sync_result['updated'] + sync_result['unchanged']
        logger.info(
            f"Sync référentiels : {total} frameworks "
            f"({sync_result['imported']} nouveaux, {sync_result['updated']} mis à jour, "
            f"{sync_result['unchanged']} inchangés)"
        )
        if sync_result['errors']:
            for err in sync_result['errors']:
                logger.error(f"  Erreur sync : {err}")
    finally:
        db.close()

    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} démarré ({settings.ENV})")
    yield
    logger.info(f"🛑 {settings.APP_NAME} arrêté")


def create_app() -> FastAPI:
    """Factory pour créer l'application FastAPI"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Outil d'audit d'infrastructure IT — "
            "Référentiels, évaluations de conformité et outils intégrés."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Security Headers Middleware ────────────────────────────────────────
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        """Ajoute les en-têtes de sécurité HTTP à chaque réponse."""

        async def dispatch(self, request: Request, call_next):
            response: Response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=(), payment=()"
            )
            # CSP : restrictif mais compatible avec Swagger UI
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data:; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
            # HSTS uniquement si HTTPS détecté
            if request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )
            return response

    app.add_middleware(SecurityHeadersMiddleware)

    # ── Prometheus Metrics Middleware ────────────────────────────────────
    app.add_middleware(PrometheusMiddleware)

    # ── Audit Logging Middleware (for tracing and business audit trail) ────
    app.add_middleware(AuditLoggingMiddleware)

    # ── CORS (restreint aux méthodes et en-têtes nécessaires) ────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Enregistrement du router API v1
    from .api.v1.router import api_router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Prometheus metrics endpoint ────────────────────────────────────────
    @app.get(
        "/metrics",
        responses={200: {"description": "Prometheus metrics"}},
        tags=["monitoring"],
    )
    async def metrics():
        """Expose Prometheus metrics for monitoring"""
        return Response(content=get_metrics(), media_type="text/plain")

    # ── Health check endpoints ────────────────────────────────────────────
    @app.get(
        "/health",
        responses={200: {"description": "Application health status"}},
        tags=["monitoring"],
    )
    async def health():
        """Basic health check endpoint - always responds if application is running"""
        status = HealthCheckService.get_health_status()
        return status

    @app.get(
        "/ready",
        responses={
            200: {"description": "Application is ready to serve requests"},
            503: {"description": "Application is not ready (dependencies unavailable)"},
        },
        tags=["monitoring"],
    )
    async def ready():
        """
        Readiness check endpoint - includes database connectivity check.
        Returns 503 if dependencies are not available.
        """
        status = HealthCheckService.get_ready_status()
        status_code = 200 if status["ready"] else 503
        return Response(
            content=str(status),
            status_code=status_code,
            media_type="application/json",
        )

    @app.get(
        "/liveness",
        responses={200: {"description": "Application is alive"}},
        tags=["monitoring"],
    )
    async def liveness():
        """
        Liveness check endpoint for Kubernetes.
        Returns 200 if the application is running.
        """
        status = HealthCheckService.get_liveness_status()
        return status

    # Enregistrement des gestionnaires d'exceptions globaux
    from .core.exception_handlers import register_exception_handlers
    register_exception_handlers(app)

    return app


app = create_app()
