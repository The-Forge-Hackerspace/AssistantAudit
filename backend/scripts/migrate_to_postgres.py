#!/usr/bin/env python3
"""
Script de migration SQLite → PostgreSQL.

Lit toutes les données depuis la base SQLite source et les insère
dans la base PostgreSQL cible. Les tables sont créées via Alembic
(exécuté automatiquement si la cible est vide).

Usage :
    python scripts/migrate_to_postgres.py \
        --source "sqlite:///instance/assistantaudit.db" \
        --target "postgresql://user:pass@localhost:5432/assistantaudit"

Prérequis :
    - La base PostgreSQL cible doit exister (CREATE DATABASE).
    - psycopg2-binary doit être installé (déjà dans requirements.txt).
    - Les migrations Alembic doivent être à jour.
"""

import argparse
import logging
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Tables à migrer dans l'ordre (respecte les FK)
# Les tables parentes avant les tables enfants
MIGRATION_ORDER = [
    "users",
    "audit_projects",
    "audit_scopes",
    "tags",
    "frameworks",
    "framework_categories",
    "framework_controls",
    "agents",
    "audit_scope_tags",
    "anssi_checklist_items",
    "collect_results",
    "config_analyses",
    "monkey365_scan_results",
    "ad_audit_results",
    "agent_collect_artifacts",
]


def get_table_names(engine) -> list[str]:
    """Retourne les noms de tables existantes dans la base."""
    inspector = inspect(engine)
    return inspector.get_table_names()


def migrate_table(source_engine, target_engine, table_name: str, metadata: MetaData) -> int:
    """Migre une table de la source vers la cible. Retourne le nombre de lignes."""
    if table_name not in metadata.tables:
        logger.warning("Table '%s' absente du schéma source — ignorée", table_name)
        return 0

    table = metadata.tables[table_name]

    with Session(source_engine) as src_session:
        rows = src_session.execute(table.select()).fetchall()

    if not rows:
        logger.info("  %s : 0 lignes (vide)", table_name)
        return 0

    columns = [c.name for c in table.columns]
    data = [dict(zip(columns, row)) for row in rows]

    with Session(target_engine) as tgt_session:
        # Désactiver les contraintes FK le temps de l'insertion
        dialect = target_engine.dialect.name
        fk_disabled = False
        if dialect == "postgresql":
            try:
                tgt_session.execute(text("SET session_replication_role = 'replica'"))
                fk_disabled = True
            except Exception:
                logger.warning(
                    "  Impossible de désactiver les FK (nécessite superuser). "
                    "Les insertions respecteront l'ordre des contraintes."
                )
                tgt_session.rollback()

        tgt_session.execute(table.insert(), data)

        if fk_disabled:
            tgt_session.execute(text("SET session_replication_role = 'origin'"))

        tgt_session.commit()

    logger.info("  %s : %d lignes migrées", table_name, len(data))
    return len(data)


def reset_sequences(target_engine, metadata: MetaData):
    """Remet à jour les séquences PostgreSQL après insertion avec ID explicites.

    Utilise pg_get_serial_sequence() pour introspecter le nom réel de la
    séquence au lieu de deviner le pattern par défaut.
    """
    with Session(target_engine) as session:
        for table_name, table in metadata.tables.items():
            for col in table.columns:
                if col.autoincrement and col.primary_key:
                    # Introspecter le nom réel de la séquence
                    row = session.execute(
                        text("SELECT pg_get_serial_sequence(:tbl, :col)"),
                        {"tbl": table_name, "col": col.name},
                    ).scalar()
                    if not row:
                        continue
                    session.execute(
                        text(
                            f"SELECT setval('{row}', "
                            f"COALESCE((SELECT MAX({col.name}) FROM {table_name}), 0) + 1, false)"
                        )
                    )
        session.commit()
    logger.info("Séquences PostgreSQL recalées")


def run_alembic_upgrade(target_url: str):
    """Exécute alembic upgrade head sur la base cible."""
    import subprocess

    logger.info("Application des migrations Alembic sur la cible...")
    # target_url vient de argparse (CLI admin uniquement), passé en env var
    # et non dans la commande — pas de risque d'injection de commande.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(Path(__file__).resolve().parent.parent),
        env={**__import__("os").environ, "DATABASE_URL": target_url},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Alembic a échoué :\n%s", result.stderr)
        sys.exit(1)
    logger.info("Migrations Alembic appliquées avec succès")


def main():
    parser = argparse.ArgumentParser(description="Migration SQLite → PostgreSQL")
    parser.add_argument(
        "--source",
        required=True,
        help="URL SQLAlchemy de la base SQLite source",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="URL SQLAlchemy de la base PostgreSQL cible",
    )
    parser.add_argument(
        "--skip-alembic",
        action="store_true",
        help="Ne pas exécuter alembic upgrade head sur la cible",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les tables et comptes sans écrire",
    )
    args = parser.parse_args()

    if not args.source.startswith("sqlite"):
        logger.error("La source doit être une base SQLite")
        sys.exit(1)
    if not args.target.startswith("postgresql"):
        logger.error("La cible doit être une base PostgreSQL")
        sys.exit(1)

    # 1. Appliquer les migrations sur la cible
    if not args.skip_alembic and not args.dry_run:
        run_alembic_upgrade(args.target)

    # 2. Connecter les deux bases
    source_engine = create_engine(args.source)
    target_engine = create_engine(args.target)

    source_tables = get_table_names(source_engine)
    logger.info("Tables source : %s", source_tables)

    # Charger le schéma depuis la source
    metadata = MetaData()
    metadata.reflect(bind=source_engine)

    # 3. Déterminer l'ordre de migration
    tables_to_migrate = [t for t in MIGRATION_ORDER if t in source_tables]
    # Ajouter les tables non listées dans MIGRATION_ORDER
    extra = [t for t in source_tables if t not in MIGRATION_ORDER and t != "alembic_version"]
    tables_to_migrate.extend(extra)

    if args.dry_run:
        logger.info("=== MODE DRY-RUN ===")
        for table_name in tables_to_migrate:
            if table_name in metadata.tables:
                with Session(source_engine) as s:
                    count = s.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
                    ).scalar()
                logger.info("  %s : %d lignes", table_name, count)
        return

    # 4. Migrer table par table
    logger.info("Début de la migration...")
    total = 0
    for table_name in tables_to_migrate:
        total += migrate_table(source_engine, target_engine, table_name, metadata)

    # 5. Recaler les séquences PostgreSQL
    reset_sequences(target_engine, metadata)

    logger.info("Migration terminée : %d lignes au total", total)


if __name__ == "__main__":
    main()
