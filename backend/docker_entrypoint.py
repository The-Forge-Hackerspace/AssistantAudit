"""
Point d'entrée Docker — initialise la base de données avant de démarrer uvicorn.

Stratégie :
- Base fraîche (aucune table) : create_all() + alembic stamp head
- Base existante              : alembic upgrade head (migrations incrémentales)
"""
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

# Import au niveau module pour que Base.metadata connaisse tous les modèles
from app.core.database import Base, engine  # noqa: E402
import app.models  # noqa: E402, F401 — Enregistre tous les modèles dans Base.metadata
from sqlalchemy import inspect as sa_inspect  # noqa: E402


def _run(cmd: list[str], label: str) -> None:
    result = subprocess.run(cmd, cwd=str(BACKEND_DIR))
    if result.returncode != 0:
        print(f"[ERREUR] {label} a échoué (code {result.returncode})")
        sys.exit(result.returncode)
    print(f"[OK] {label}")


def main() -> None:
    inspector = sa_inspect(engine)
    existing_tables = inspector.get_table_names()
    has_alembic_version = "alembic_version" in existing_tables

    if not existing_tables:
        # Base fraîche : créer le schéma complet puis marquer à HEAD
        print("[INFO] Base de données vide — création du schéma complet…")
        Base.metadata.create_all(bind=engine)
        _run([sys.executable, "-m", "alembic", "stamp", "head"], "alembic stamp head")
    elif not has_alembic_version:
        # Tables présentes mais pas encore sous Alembic (migration vers Docker)
        print("[INFO] Tables existantes sans historique Alembic — stamp head…")
        _run([sys.executable, "-m", "alembic", "stamp", "head"], "alembic stamp head")
    else:
        # Base gérée par Alembic : appliquer les migrations en attente
        print("[INFO] Application des migrations Alembic…")
        _run([sys.executable, "-m", "alembic", "upgrade", "head"], "alembic upgrade head")


if __name__ == "__main__":
    main()
