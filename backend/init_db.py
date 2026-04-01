"""
Script d'initialisation de la base de données et du premier utilisateur admin.
À exécuter une seule fois lors de la mise en place.

Le schema est gere EXCLUSIVEMENT par Alembic. Ce script ne touche jamais
au schema directement (pas de create_all_tables). Il se contente de :
  1. Appliquer les migrations Alembic (alembic upgrade head)
  2. Creer l'utilisateur admin par defaut
  3. Synchroniser les referentiels YAML via sync_from_directory
"""
import io
import os
import subprocess
import sys
from pathlib import Path

# Forcer UTF-8 pour la sortie console (Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ajouter le répertoire backend au path
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.services.framework_service import FrameworkService


def _run_alembic_upgrade() -> bool:
    """Execute alembic upgrade head et retourne True si OK."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("  [ERREUR] alembic upgrade head a echoue:")
        for line in result.stderr.strip().splitlines():
            print(f"    {line}")
        return False
    for line in result.stdout.strip().splitlines():
        print(f"    {line}")
    return True


def init_database():
    """Applique les migrations, cree l'admin et synchronise les referentiels."""
    print("=" * 60)
    print("  AssistantAudit - Initialisation de la base de donnees")
    print("=" * 60)

    # 1. Appliquer les migrations Alembic
    print("\n[1/3] Application des migrations Alembic...")
    # Creer le dossier instance si absent (SQLite)
    (BACKEND_DIR / "instance").mkdir(parents=True, exist_ok=True)
    if _run_alembic_upgrade():
        print("  [OK] Migrations appliquees")
    else:
        print("  [ERREUR] Echec des migrations — voir les messages ci-dessus")
        sys.exit(1)

    # 2. Créer l'utilisateur admin
    print("\n[2/3] Creation de l'utilisateur admin...")
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("  [SKIP] L'utilisateur 'admin' existe deja")
        else:
            admin_password = os.getenv("ADMIN_PASSWORD")
            if not admin_password:
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits + "!@#$%"
                admin_password = "".join(secrets.choice(alphabet) for _ in range(16))
                print("  [INFO] Mot de passe admin genere aleatoirement")

            admin = User(
                username="admin",
                email=os.getenv("ADMIN_EMAIL", "admin@assistantaudit.fr"),
                password_hash=hash_password(admin_password),
                full_name="Administrateur",
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("  [OK] Utilisateur admin cree (login: admin)")
            print(f"  [INFO] Mot de passe initial: {admin_password}")

        # 3. Synchroniser les référentiels (hash-based, skip inchanges)
        print("\n[3/3] Synchronisation des referentiels YAML...")
        settings = get_settings()
        frameworks_dir = Path(settings.FRAMEWORKS_DIR)
        if frameworks_dir.exists():
            sync = FrameworkService.sync_from_directory(db, frameworks_dir)
            total = sync["imported"] + sync["updated"] + sync["unchanged"]
            print(
                f"  [OK] {total} referentiels "
                f"({sync['imported']} nouveaux, {sync['updated']} mis a jour, "
                f"{sync['unchanged']} inchanges)"
            )
            for err in sync.get("errors", []):
                print(f"  [WARN] {err}")
        else:
            print(f"  [WARN] Dossier {frameworks_dir} introuvable")

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("  Initialisation terminee !")
    print("  Demarrer avec : uvicorn app.main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    init_database()
