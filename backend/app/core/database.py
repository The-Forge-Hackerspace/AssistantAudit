"""
Configuration de la base de données SQLAlchemy (async-ready).
Fournit le moteur, la session factory et le modèle de base.
"""
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from .config import get_settings


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy"""
    pass


def _get_engine():
    """Crée le moteur SQLAlchemy"""
    settings = get_settings()
    db_url = settings.DATABASE_URL

    # Créer le dossier instance pour SQLite
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )

    # Activer les clés étrangères pour SQLite
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _get_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """
    Générateur de session DB pour injection de dépendance FastAPI.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """Crée toutes les tables (développement uniquement)"""
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """Supprime toutes les tables (tests uniquement)"""
    Base.metadata.drop_all(bind=engine)
