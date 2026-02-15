"""
Script d'initialisation de la base de données et du premier utilisateur admin.
À exécuter une seule fois lors de la mise en place.
"""
import sys
import io
from pathlib import Path

# Forcer UTF-8 pour la sortie console (Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ajouter le répertoire backend au path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import create_all_tables, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.services.framework_service import FrameworkService
from app.core.config import get_settings


def init_database():
    """Crée les tables et l'utilisateur admin par défaut"""
    print("=" * 60)
    print("  AssistantAudit - Initialisation de la base de donnees")
    print("=" * 60)

    # 1. Créer les tables
    print("\n[1/3] Creation des tables...")
    # Import tous les modèles pour qu'ils soient détectés
    from app.models import (  # noqa: F401
        User, Entreprise, Contact, Audit, Site,
        Equipement, EquipementReseau, EquipementServeur, EquipementFirewall,
        ScanReseau, ScanHost, ScanPort,
        Framework, FrameworkCategory, Control,
        AssessmentCampaign, Assessment, ControlResult,
    )
    create_all_tables()
    print("  [OK] Tables creees")

    # 2. Créer l'utilisateur admin
    print("\n[2/3] Creation de l'utilisateur admin...")
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("  [SKIP] L'utilisateur 'admin' existe deja")
        else:
            # Utiliser un mot de passe depuis l'environnement ou demander à l'utilisateur
            import os
            admin_password = os.getenv("ADMIN_PASSWORD")
            if not admin_password:
                # Générer un mot de passe aléatoire pour la première initialisation
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits + "!@#$%"
                admin_password = "".join(secrets.choice(alphabet) for _ in range(16))
                print(f"  [INFO] Mot de passe admin généré aléatoirement (à changer dès la première connexion)")
            
            admin = User(
                username="admin",
                email="admin@assistantaudit.fr",
                password_hash=hash_password(admin_password),
                full_name="Administrateur",
                role="admin",
            )
            db.add(admin)
            db.commit()
            print(f"  [OK] Utilisateur admin cree (login: admin / <mot_de_passe_genere>)")
            print(f"  [INFO] Mot de passe initial: {admin_password}")

        # 3. Importer les référentiels
        print("\n[3/3] Import des referentiels YAML...")
        settings = get_settings()
        frameworks_dir = Path(settings.FRAMEWORKS_DIR)
        if frameworks_dir.exists():
            frameworks = FrameworkService.import_all_from_directory(db, frameworks_dir)
            for fw in frameworks:
                print(f"  [OK] {fw.name} ({fw.total_controls} controles)")
            if not frameworks:
                print("  [WARN] Aucun fichier YAML trouve dans frameworks/")
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
