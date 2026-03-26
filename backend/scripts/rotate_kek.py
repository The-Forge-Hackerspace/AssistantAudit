"""
Script de rotation de la KEK (Key Encryption Key).

Usage :
    python scripts/rotate_kek.py --old-key <ancien_hex_64chars>

Ce script :
1. Lit l'ancienne KEK depuis --old-key
2. Utilise la nouvelle KEK depuis FILE_ENCRYPTION_KEY (env var)
3. Itere sur tous les Attachments et re-chiffre chaque DEK
4. Incremente kek_version
5. Les fichiers sur disque ne sont PAS touches

Prerequis : FILE_ENCRYPTION_KEY doit etre definie avec la NOUVELLE cle avant execution.
"""
import argparse
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.file_encryption import EnvelopeEncryption


def rotate(old_key_hex: str) -> None:
    settings = get_settings()
    new_key_hex = settings.FILE_ENCRYPTION_KEY

    if not new_key_hex:
        print("ERREUR: FILE_ENCRYPTION_KEY n'est pas definie dans l'environnement.")
        print("Definissez la NOUVELLE cle avant d'executer ce script.")
        sys.exit(1)

    if old_key_hex == new_key_hex:
        print("ERREUR: L'ancienne et la nouvelle KEK sont identiques.")
        sys.exit(1)

    # TODO: Activer quand le modele Attachment aura les colonnes encrypted_dek/dek_nonce/kek_version
    # from app.models.attachment import Attachment
    # from sqlalchemy import select
    #
    # session = SessionLocal()
    # try:
    #     attachments = session.query(Attachment).filter(
    #         Attachment.encrypted_dek.isnot(None)
    #     ).all()
    #
    #     count = 0
    #     for att in attachments:
    #         new_dek, new_nonce = EnvelopeEncryption.rotate_kek(
    #             att.encrypted_dek, att.dek_nonce, old_key_hex, new_key_hex
    #         )
    #         att.encrypted_dek = new_dek
    #         att.dek_nonce = new_nonce
    #         att.kek_version += 1
    #         count += 1
    #
    #     session.commit()
    #     print(f"Rotation terminee : {count} DEK(s) re-chiffree(s).")
    # except Exception as e:
    #     session.rollback()
    #     print(f"ERREUR lors de la rotation : {e}")
    #     sys.exit(1)
    # finally:
    #     session.close()

    print("NOTE: Le modele Attachment n'a pas encore les colonnes de chiffrement.")
    print("Ce script sera fonctionnel apres la migration Alembic correspondante.")
    print(f"Ancienne KEK : {old_key_hex[:8]}...{old_key_hex[-8:]}")
    print(f"Nouvelle KEK : {new_key_hex[:8]}...{new_key_hex[-8:]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rotation de la KEK (Key Encryption Key) pour les fichiers chiffres"
    )
    parser.add_argument(
        "--old-key",
        required=True,
        help="Ancienne KEK en hex (64 caracteres)",
    )
    args = parser.parse_args()

    if len(args.old_key) != 64:
        print("ERREUR: --old-key doit etre un hex string de 64 caracteres (256 bits)")
        sys.exit(1)

    rotate(args.old_key)
