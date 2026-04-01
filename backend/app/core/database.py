"""
Configuration de la base de donnees SQLAlchemy.
Supporte PostgreSQL (psycopg2) et SQLite (dev/tests).
Fournit le moteur, la session factory et le modele de base.
"""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Classe de base pour tous les modeles SQLAlchemy"""
    pass


def _get_engine():
    """Cree le moteur SQLAlchemy avec configuration adaptee au backend."""
    settings = get_settings()
    db_url = settings.DATABASE_URL
    is_sqlite = db_url.startswith("sqlite")

    # Creer le dossier instance pour SQLite
    if is_sqlite:
        db_path = db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connect_args = {}
    if is_sqlite:
        connect_args["check_same_thread"] = False

    # Pool config : uniquement pour PostgreSQL (SQLite utilise NullPool implicitement)
    pool_kwargs = {}
    if not is_sqlite:
        pool_kwargs["pool_size"] = 10
        pool_kwargs["max_overflow"] = 5
        pool_kwargs["pool_recycle"] = 3600
        pool_kwargs["pool_pre_ping"] = True

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=settings.SQL_ECHO,
        **pool_kwargs,
    )

    # Activer les cles etrangeres pour SQLite
    if is_sqlite:
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
    Generateur de session DB pour injection de dependance FastAPI.
    Auto-commit on success, auto-rollback on exception.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_all_tables():
    """Cree toutes les tables (developpement uniquement)"""
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """Supprime toutes les tables (tests uniquement)"""
    Base.metadata.drop_all(bind=engine)
