"""
Point d'entrée de l'application FastAPI — AssistantAudit v2.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.database import create_all_tables, SessionLocal

settings = get_settings()


def configure_logging():
    """Configure le logging global"""
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "assistantaudit.log", encoding="utf-8"),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle de l'application : démarrage et arrêt"""
    configure_logging()
    logger = logging.getLogger(__name__)

    # Création des tables en développement
    if settings.ENV == "development":
        logger.info("Mode développement : création des tables...")
        create_all_tables()

    # Créer le dossier uploads
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

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

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Enregistrement du router API v1
    from .api.v1.router import api_router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
