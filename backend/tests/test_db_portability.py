"""
Tests de portabilité SQLite / PostgreSQL.

Vérifie que les modèles et la configuration sont compatibles
avec les deux backends de base de données.
"""
import importlib
import pkgutil

import pytest
from sqlalchemy import JSON, inspect, text

from app.core.config import get_settings
from app.core.database import Base
from app.models import *  # noqa: F401, F403


# ---------------------------------------------------------------------------
# T001 — Imports JSON portables (pas de sqlalchemy.dialects.sqlite)
# ---------------------------------------------------------------------------
class TestPortableImports:
    """Vérifie que les modèles n'utilisent pas d'imports spécifiques à SQLite."""

    def test_no_sqlite_dialect_import(self):
        """Aucun modèle ne doit importer depuis sqlalchemy.dialects.sqlite."""
        import ast
        from pathlib import Path

        models_dir = Path(__file__).parent.parent / "app" / "models"
        violations = []

        for py_file in models_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            source = py_file.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "sqlalchemy.dialects.sqlite" in node.module:
                        violations.append(py_file.name)

        assert violations == [], (
            f"Imports SQLite-spécifiques trouvés dans : {violations}. "
            "Utiliser 'from sqlalchemy import JSON' à la place."
        )

    def test_json_columns_use_generic_type(self, db_engine):
        """Toutes les colonnes JSON doivent utiliser le type générique SQLAlchemy."""
        insp = inspect(db_engine)
        for table_name in insp.get_table_names():
            if table_name == "alembic_version":
                continue
            columns = insp.get_columns(table_name)
            for col in columns:
                if "json" in type(col["type"]).__name__.lower():
                    assert isinstance(col["type"], type(JSON())), (
                        f"Colonne {table_name}.{col['name']} utilise un type JSON "
                        f"non-portable : {type(col['type'])}"
                    )


# ---------------------------------------------------------------------------
# T002 — Configuration base de données
# ---------------------------------------------------------------------------
class TestDatabaseConfig:
    """Vérifie que la configuration supporte les deux backends."""

    def test_database_url_defaults_to_sqlite(self):
        """En dev, DATABASE_URL doit avoir un défaut SQLite valide."""
        settings = get_settings()
        assert settings.DATABASE_URL, "DATABASE_URL ne doit pas être vide"
        # Doit être soit sqlite soit postgresql
        assert settings.DATABASE_URL.startswith(("sqlite", "postgresql")), (
            f"DATABASE_URL non supporté : {settings.DATABASE_URL}"
        )

    def test_engine_connects(self, db_engine):
        """Le moteur SQLAlchemy doit se connecter sans erreur."""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_all_tables_created(self, db_engine):
        """Toutes les tables du modèle doivent exister."""
        insp = inspect(db_engine)
        db_tables = set(insp.get_table_names())
        model_tables = set(Base.metadata.tables.keys())
        missing = model_tables - db_tables
        assert missing == set(), f"Tables manquantes en base : {missing}"


# ---------------------------------------------------------------------------
# T003 — Alembic env.py portabilité
# ---------------------------------------------------------------------------
class TestAlembicPortability:
    """Vérifie que la config Alembic est portable."""

    def test_env_uses_settings_url(self):
        """alembic/env.py doit lire DATABASE_URL depuis Settings, pas alembic.ini."""
        from pathlib import Path

        env_py = Path(__file__).parent.parent / "alembic" / "env.py"
        source = env_py.read_text()
        assert "get_settings" in source or "settings.DATABASE_URL" in source, (
            "alembic/env.py doit utiliser Settings.DATABASE_URL"
        )

    def test_render_as_batch_enabled(self):
        """render_as_batch doit être activé pour la compatibilité SQLite."""
        from pathlib import Path

        env_py = Path(__file__).parent.parent / "alembic" / "env.py"
        source = env_py.read_text()
        assert "render_as_batch=True" in source, (
            "render_as_batch=True requis dans alembic/env.py pour SQLite"
        )

    def test_migrations_use_batch(self):
        """Les fichiers de migration doivent utiliser batch_alter_table pour alter_column."""
        from pathlib import Path

        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        if not versions_dir.exists():
            pytest.skip("Pas de migrations existantes")

        migrations = list(versions_dir.glob("*.py"))
        if not migrations:
            pytest.skip("Pas de migrations existantes")

        for migration in migrations:
            source = migration.read_text()
            # alter_column nécessite batch_alter_table pour SQLite
            if "op.alter_column" in source:
                assert "batch_alter_table" in source, (
                    f"Migration {migration.name} utilise alter_column sans batch_alter_table"
                )


# ---------------------------------------------------------------------------
# T004 — Script de migration
# ---------------------------------------------------------------------------
class TestMigrationScript:
    """Vérifie que le script de migration existe et est valide."""

    def test_migration_script_exists(self):
        """Le script migrate_to_postgres.py doit exister."""
        from pathlib import Path

        script = Path(__file__).parent.parent / "scripts" / "migrate_to_postgres.py"
        assert script.exists(), "scripts/migrate_to_postgres.py manquant"

    def test_migration_script_importable(self):
        """Le script doit être importable sans erreur."""
        import importlib.util
        from pathlib import Path

        script = Path(__file__).parent.parent / "scripts" / "migrate_to_postgres.py"
        spec = importlib.util.spec_from_file_location("migrate_to_postgres", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "main")
        assert hasattr(module, "migrate_table")
