"""
Alembic env.py — Configuration des migrations.
Lit DATABASE_URL depuis la config applicative (Settings).
"""
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
import sqlalchemy as sa
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403 — Import tous les modeles

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL script."""
    from app.core.config import get_settings
    settings = get_settings()
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — uses the application engine."""
    with engine.connect() as connection:
        # SQLite: disable FK checks during batch_alter_table (copy-and-move)
        is_sqlite = connection.dialect.name == "sqlite"
        if is_sqlite:
            connection.execute(sa.text("PRAGMA foreign_keys=OFF"))

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()

        if is_sqlite:
            connection.execute(sa.text("PRAGMA foreign_keys=ON"))


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
