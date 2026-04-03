"""
Point d'entrée Docker — initialise la base de données avant de démarrer uvicorn.

Stratégie :
- Base fraîche (aucune table) : create_all() + alembic stamp head + admin
- Base existante              : alembic upgrade head (migrations incrémentales)
- Admin absent                : création avec mot de passe affiché dans les logs
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

# Import au niveau module pour que Base.metadata connaisse tous les modèles
from sqlalchemy import inspect as sa_inspect  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

import app.models  # noqa: E402, F401 — Enregistre tous les modèles dans Base.metadata
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402


def _run(cmd: list[str], label: str) -> None:
    # Sécurité : cmd est toujours construit en interne (jamais depuis une entrée utilisateur)
    assert all(isinstance(arg, str) for arg in cmd), "cmd doit être une liste de chaînes"
    result = subprocess.run(cmd, cwd=str(BACKEND_DIR))  # noqa: S603
    if result.returncode != 0:
        print(f"[ERREUR] {label} a échoué (code {result.returncode})")
        sys.exit(result.returncode)
    print(f"[OK] {label}")


def _ensure_admin() -> None:
    """Crée l'utilisateur admin s'il n'existe pas encore."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("[SKIP] L'utilisateur 'admin' existe déjà")
            return

        admin_password = os.getenv("ADMIN_PASSWORD")
        if not admin_password:
            print("[WARN] ADMIN_PASSWORD non défini — admin non créé")
            print("[WARN] Définissez ADMIN_PASSWORD dans .env ou docker-compose.yml")
            return

        admin = User(
            username="admin",
            email=os.getenv("ADMIN_EMAIL", "admin@assistantaudit.fr"),
            password_hash=hash_password(admin_password),
            full_name="Administrateur",
            role="admin",
        )
        db.add(admin)
        try:
            db.commit()
        except IntegrityError:
            # Un autre processus a créé l'admin entre le SELECT et le INSERT
            db.rollback()
            print("[SKIP] L'utilisateur 'admin' a été créé par un autre processus")
            return
        print("[OK] Utilisateur admin créé (login: admin)")
    finally:
        db.close()


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

    # Créer l'admin si absent (premier démarrage ou base réinitialisée)
    _ensure_admin()


if __name__ == "__main__":
    main()
