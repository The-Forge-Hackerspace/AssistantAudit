"""
Script de rotation de la KEK (Key Encryption Key).

Usage :
    python scripts/rotate_kek.py <ancien_hex_64chars>           # dry-run
    python scripts/rotate_kek.py <ancien_hex_64chars> --apply   # appliquer

Ce script :
1. Lit l'ancienne KEK depuis l'argument positionnel
2. Utilise la nouvelle KEK depuis FILE_ENCRYPTION_KEY (env var)
3. Itère sur tous les Attachments avec encrypted_dek non null
4. Re-chiffre chaque DEK avec la nouvelle KEK
5. Met à jour la base de données (seulement avec --apply)
6. Les fichiers sur disque ne sont PAS touchés

Prérequis : FILE_ENCRYPTION_KEY doit être définie avec la NOUVELLE clé avant exécution.
"""
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.file_encryption import EnvelopeEncryption
from app.models.attachment import Attachment


def rotate(old_key_hex: str, apply: bool = False) -> None:
    settings = get_settings()
    new_key_hex = settings.FILE_ENCRYPTION_KEY

    # Validations
    if not old_key_hex or len(old_key_hex) != 64:
        print("ERREUR: old_key doit être une clé hex de 64 caractères")
        sys.exit(1)
    if not new_key_hex or len(new_key_hex) != 64:
        print("ERREUR: FILE_ENCRYPTION_KEY doit être définie (64 hex)")
        sys.exit(1)
    if old_key_hex == new_key_hex:
        print("ERREUR: ancienne et nouvelle KEK identiques")
        sys.exit(1)

    # Connexion DB
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        attachments = session.query(Attachment).filter(
            Attachment.encrypted_dek.isnot(None)
        ).all()

        print(f"Trouvé {len(attachments)} fichiers avec DEK chiffré")
        if not apply:
            print("Mode DRY-RUN — ajouter --apply pour exécuter")

        success = 0
        errors = 0
        for att in attachments:
            try:
                new_encrypted_dek, new_nonce = EnvelopeEncryption.rotate_kek(
                    att.encrypted_dek, att.dek_nonce, old_key_hex, new_key_hex
                )
                if apply:
                    att.encrypted_dek = new_encrypted_dek
                    att.dek_nonce = new_nonce
                    if att.kek_version is not None:
                        att.kek_version += 1
                success += 1
            except Exception as e:
                print(f"  ERREUR fichier {att.id} ({att.original_filename}): {e}")
                errors += 1

        if apply:
            session.commit()
            print(f"Rotation appliquée: {success} OK, {errors} erreurs")
        else:
            print(f"DRY-RUN: {success} fichiers seraient rotés, {errors} erreurs")
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rotation de la KEK (File Encryption Key)")
    parser.add_argument("old_key", help="Ancienne KEK (64 caractères hex)")
    parser.add_argument("--apply", action="store_true", help="Appliquer la rotation (sinon dry-run)")
    args = parser.parse_args()
    rotate(args.old_key, apply=args.apply)
