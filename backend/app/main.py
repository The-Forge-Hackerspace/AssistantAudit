"""
Point d'entrée de l'application FastAPI — AssistantAudit v2.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .core.audit_logger import AuditLoggingMiddleware
from .core.config import get_settings
from .core.database import SessionLocal
from .core.health_check import HealthCheckService
from .core.logging_config import configure_structured_logging
from .core.metrics import get_metrics, init_app_metrics
from .core.metrics_middleware import PrometheusMiddleware
from .core.rate_limit import api_rate_limiter, public_rate_limiter
from .core.sentry_integration import init_sentry

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
        db.commit()
        total = sync_result["imported"] + sync_result["updated"] + sync_result["unchanged"]
        logger.info(
            f"Sync référentiels : {total} frameworks "
            f"({sync_result['imported']} nouveaux, {sync_result['updated']} mis à jour, "
            f"{sync_result['unchanged']} inchangés)"
        )
        if sync_result["errors"]:
            for err in sync_result["errors"]:
                logger.error(f"  Erreur sync : {err}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # Demarrage du sweeper heartbeat agents (TOS-12)
    from .core.heartbeat_sweeper import run_heartbeat_sweeper

    sweeper_task = asyncio.create_task(run_heartbeat_sweeper())

    # Demarrage du sweeper collectes orphelines (TOS-16)
    from .core.collect_sweeper import run_collect_sweeper

    collect_sweeper_task = asyncio.create_task(run_collect_sweeper())

    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} démarré ({settings.ENV})")
    try:
        yield
    finally:
        for task, name in (
            (sweeper_task, "Heartbeat sweeper"),
            (collect_sweeper_task, "Collect sweeper"),
        ):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                # Annulation attendue lors du shutdown — rien à logger.
                pass
            except Exception:
                logger.exception("%s a levé une exception pendant le shutdown", name)
        logger.info(f"🛑 {settings.APP_NAME} arrêté")


def create_app() -> FastAPI:
    """Factory pour créer l'application FastAPI"""
    # Desactiver Swagger/ReDoc en production (surface d'attaque inutile)
    is_prod = settings.ENV in ("production", "preprod", "staging")
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=("Outil d'audit d'infrastructure IT — Référentiels, évaluations de conformité et outils intégrés."),
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    # ── Security Headers Middleware ────────────────────────────────────────
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        """Ajoute les en-tetes de securite HTTP a chaque reponse.
        Skip les WebSocket (BaseHTTPMiddleware ne supporte pas le protocole WS)."""

        async def dispatch(self, request: Request, call_next):
            # BaseHTTPMiddleware casse les WebSocket — les laisser passer directement
            if request.scope.get("type") == "websocket":
                return await call_next(request)
            response: Response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
            # CSP : en prod (Swagger desactive) on supprime 'unsafe-inline'
            # et le CDN externe pour reduire la surface XSS. En dev, on garde
            # 'unsafe-inline' + cdn.jsdelivr.net pour compatibilite Swagger UI.
            if is_prod:
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "script-src 'self'; "
                    "style-src 'self'; "
                    "img-src 'self' data:; "
                    "font-src 'self'; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'"
                )
            else:
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
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            # Masquer les versions serveur (fingerprinting)
            if "server" in response.headers:
                del response.headers["server"]
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

    # WebSocket monte a la racine (agent se connecte a /ws/agent, pas /api/v1/ws/agent)
    from .api.v1.websocket import router as websocket_router

    app.include_router(websocket_router)

    # ── Prometheus metrics endpoint ────────────────────────────────────────
    from .core.deps import get_current_admin

    @app.get(
        "/metrics",
        responses={200: {"description": "Prometheus metrics"}},
        tags=["monitoring"],
    )
    def metrics(admin=Depends(get_current_admin)):
        """Expose Prometheus metrics (admin uniquement)"""
        return Response(content=get_metrics(), media_type="text/plain")

    # ── Rate Limiting Middleware ────────────────────────────────────────────
    # Routes publiques (health, ready, liveness, metrics) : 100 req/min
    # Routes API authentifiées : 30 req/min
    PUBLIC_PATHS = {"/health", "/ready", "/liveness", "/metrics"}

    class RateLimitMiddleware(BaseHTTPMiddleware):
        """Rate limiting par catégorie : public (100/min) vs API (30/min).
        Les endpoints auth (login/enroll) ont leur propre limiter inline."""

        async def dispatch(self, request: Request, call_next):
            # WebSocket : pas de rate limiting
            if request.scope.get("type") == "websocket":
                return await call_next(request)

            # Préflights CORS : pas de rate limiting (pas de logique métier,
            # consomme inutilement le budget quand le front poll à 3s)
            if request.method == "OPTIONS":
                return await call_next(request)

            path = request.url.path

            try:
                # Routes publiques
                if path in PUBLIC_PATHS:
                    public_rate_limiter.acquire_attempt(request)
                # Routes API (sauf auth — géré inline dans les routes)
                elif path.startswith(settings.API_V1_PREFIX):
                    auth_prefix = f"{settings.API_V1_PREFIX}/auth/"
                    agents_enroll = f"{settings.API_V1_PREFIX}/agents/enroll"
                    if not path.startswith(auth_prefix) and path != agents_enroll:
                        api_rate_limiter.acquire_attempt(request)
            except HTTPException as exc:
                from starlette.responses import JSONResponse

                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                    headers=exc.headers,
                )

            return await call_next(request)

    app.add_middleware(RateLimitMiddleware)

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
        # Ne renvoyer qu'un résumé booléen : les détails (erreurs DB, chemins internes)
        # ne doivent pas sortir côté client ; ils restent côté logs serveur.
        return JSONResponse(
            content={"ready": bool(status.get("ready"))},
            status_code=status_code,
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
