"""
Script unifié de rotation des clés de chiffrement.

Supporte deux types de rotation :
- ``kek``         : rotation de FILE_ENCRYPTION_KEY (re-chiffre les DEK des fichiers)
- ``encryption``  : rotation de ENCRYPTION_KEY (re-chiffre les colonnes EncryptedText/EncryptedJSON)
- ``all``         : les deux rotations en séquence

Usage :
    # Dry-run (par défaut) — vérifie sans modifier
    python scripts/rotate_kek.py --type kek      OLD_KEY
    python scripts/rotate_kek.py --type encryption OLD_KEY
    python scripts/rotate_kek.py --type all       OLD_KEK OLD_ENC

    # Appliquer réellement
    python scripts/rotate_kek.py --type kek      OLD_KEY --apply
    python scripts/rotate_kek.py --type all       OLD_KEK OLD_ENC --apply --verify

Prérequis :
- FILE_ENCRYPTION_KEY doit contenir la NOUVELLE KEK dans l'environnement
- ENCRYPTION_KEY doit contenir la NOUVELLE clé de chiffrement dans l'environnement
"""
import logging
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ajouter le backend au path
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_settings
from app.core.encryption import AES256GCMCipher, EncryptedText, EncryptedJSON
from app.core.file_encryption import EnvelopeEncryption
from app.models.attachment import Attachment

# Modèles contenant des colonnes chiffrées avec ENCRYPTION_KEY
from app.models.scan import ScanReseau
from app.models.oradad_config import OradadConfig
from app.models.collect_result import CollectResult
from app.models.finding import Finding
from app.models.agent_task import AgentTask
from app.models.ad_audit_result import ADAuditResultModel

# ---------------------------------------------------------------------------
# Logging structuré
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rotate_keys")

# ---------------------------------------------------------------------------
# Registre des colonnes chiffrées (modèle, nom_colonne, type_decorator)
# ---------------------------------------------------------------------------
ENCRYPTED_COLUMNS: list[tuple[type, str, type]] = [
    (ScanReseau, "raw_xml_output", EncryptedText),
    (OradadConfig, "explicit_domains", EncryptedText),
    (CollectResult, "username", EncryptedText),
    (Finding, "remediation_note", EncryptedText),
    (AgentTask, "parameters", EncryptedJSON),
    (ADAuditResultModel, "username", EncryptedText),
    (ADAuditResultModel, "dc_list", EncryptedJSON),
    (ADAuditResultModel, "domain_admins", EncryptedJSON),
    (ADAuditResultModel, "findings", EncryptedText),
]

# ---------------------------------------------------------------------------
# Expression régulière pour valider un hex de 64 caractères
# ---------------------------------------------------------------------------
_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _validate_hex_key(value: str, label: str) -> None:
    """Valide qu'une clé est un hex de 64 caractères. Lève ValueError sinon."""
    if not _HEX64_RE.match(value):
        raise ValueError(
            f"ERREUR: {label} doit être une chaîne hexadécimale de 64 caractères "
            f"(reçu {len(value)} caractères). "
            f"Générez avec : python -c 'import os; print(os.urandom(32).hex())'"
        )


# ===================================================================
# Phase 1 : Rotation ENCRYPTION_KEY (colonnes EncryptedText/EncryptedJSON)
# ===================================================================

def rotate_encryption_key(
    old_key_hex: str,
    new_key_hex: str,
    session: Session,
    apply: bool = False,
) -> tuple[int, int]:
    """
    Re-chiffre toutes les colonnes EncryptedText/EncryptedJSON
    avec la nouvelle ENCRYPTION_KEY.

    Retourne (success_count, error_count).
    Toute exception est propagée pour permettre le rollback transactionnel.
    """
    old_cipher = AES256GCMCipher(old_key_hex)
    new_cipher = AES256GCMCipher(new_key_hex)

    total_success = 0
    total_errors = 0

    for model_cls, col_name, col_type in ENCRYPTED_COLUMNS:
        table_name = model_cls.__tablename__
        logger.info("Rotation colonnes chiffrées : %s.%s", table_name, col_name)

        # Récupérer les lignes dont la colonne n'est pas null (requête brute
        # pour éviter le déchiffrement automatique du TypeDecorator)
        col_attr = getattr(model_cls, col_name)
        rows = session.query(model_cls).filter(col_attr.isnot(None)).all()

        row_success = 0
        row_errors = 0

        for row in rows:
            row_id = getattr(row, "id", "?")
            # Lire la valeur brute directement via inspection SQL
            # Les TypeDecorators déchiffrent automatiquement à la lecture,
            # on doit lire la valeur brute pour la re-chiffrer.
            raw_value = _read_raw_column(session, model_cls, col_name, row_id)
            if raw_value is None:
                continue

            try:
                # Déchiffrer avec l'ancienne clé
                plaintext = old_cipher.decrypt(raw_value)
                # Re-chiffrer avec la nouvelle clé
                new_ciphertext = new_cipher.encrypt(plaintext)

                if apply:
                    _write_raw_column(session, model_cls, col_name, row_id, new_ciphertext)

                row_success += 1
                logger.debug(
                    "  OK %s.%s id=%s", table_name, col_name, row_id
                )
            except Exception as exc:
                row_errors += 1
                logger.error(
                    "  ERREUR %s.%s id=%s : %s", table_name, col_name, row_id, exc
                )
                raise RuntimeError(
                    f"ERREUR: clé ancienne incorrecte ou donnée corrompue pour "
                    f"{table_name}.{col_name} id={row_id} — {exc}"
                ) from exc

        logger.info(
            "  %s.%s : %d OK, %d erreurs", table_name, col_name, row_success, row_errors
        )
        total_success += row_success
        total_errors += row_errors

    return total_success, total_errors


def _read_raw_column(session: Session, model_cls: type, col_name: str, row_id: int) -> str | None:
    """Lit la valeur brute (chiffrée) d'une colonne sans passer par le TypeDecorator."""
    table_name = model_cls.__tablename__
    result = session.execute(
        text(f"SELECT {col_name} FROM {table_name} WHERE id = :rid"),
        {"rid": row_id},
    ).scalar()
    return result


def _write_raw_column(
    session: Session, model_cls: type, col_name: str, row_id: int, value: str
) -> None:
    """Écrit une valeur brute dans une colonne sans passer par le TypeDecorator."""
    table_name = model_cls.__tablename__
    session.execute(
        text(f"UPDATE {table_name} SET {col_name} = :val WHERE id = :rid"),
        {"val": value, "rid": row_id},
    )


# ===================================================================
# Phase 2 : Rotation KEK (FILE_ENCRYPTION_KEY) — re-chiffre les DEK
# ===================================================================

def rotate_kek(
    old_key_hex: str,
    new_key_hex: str,
    session: Session,
    apply: bool = False,
) -> tuple[int, int]:
    """
    Re-chiffre toutes les DEK des Attachments avec la nouvelle KEK.

    Retourne (success_count, error_count).
    Toute exception est propagée pour permettre le rollback transactionnel.
    """
    attachments = session.query(Attachment).filter(
        Attachment.encrypted_dek.isnot(None)
    ).all()

    logger.info("Trouvé %d fichiers avec DEK chiffré", len(attachments))

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
            logger.debug("  OK fichier id=%s (%s)", att.id, att.original_filename)
        except Exception as exc:
            errors += 1
            logger.error(
                "  ERREUR fichier id=%s (%s) : %s", att.id, att.original_filename, exc
            )
            raise RuntimeError(
                f"ERREUR: clé ancienne incorrecte ou donnée corrompue pour "
                f"Attachment id={att.id} ({att.original_filename}) — {exc}"
            ) from exc

    return success, errors


# ===================================================================
# Phase 3 : Vérification pré-rotation
# ===================================================================

def verify_pre_rotation(session: Session, rotation_type: str) -> None:
    """
    Vérification rapide avant rotation : compte les enregistrements concernés.
    """
    if rotation_type in ("kek", "all"):
        count = session.query(Attachment).filter(
            Attachment.encrypted_dek.isnot(None)
        ).count()
        logger.info("Vérification KEK : %d Attachments avec DEK chiffré", count)

    if rotation_type in ("encryption", "all"):
        for model_cls, col_name, _ in ENCRYPTED_COLUMNS:
            col_attr = getattr(model_cls, col_name)
            count = session.query(model_cls).filter(col_attr.isnot(None)).count()
            logger.info(
                "Vérification ENCRYPTION_KEY : %s.%s → %d enregistrements",
                model_cls.__tablename__, col_name, count,
            )


# ===================================================================
# Orchestrateur principal
# ===================================================================

def run_rotation(
    rotation_type: str,
    old_kek_hex: str | None = None,
    old_enc_hex: str | None = None,
    apply: bool = False,
    verify: bool = False,
) -> None:
    """
    Point d'entrée principal pour la rotation des clés.

    Args:
        rotation_type: 'kek', 'encryption' ou 'all'
        old_kek_hex: ancienne FILE_ENCRYPTION_KEY (requise pour kek/all)
        old_enc_hex: ancienne ENCRYPTION_KEY (requise pour encryption/all)
        apply: True pour appliquer, False pour dry-run
        verify: True pour vérification pré-rotation
    """
    settings = get_settings()

    # --- Validation des clés fournies ---
    if rotation_type in ("kek", "all"):
        if not old_kek_hex:
            logger.error("ERREUR: ancienne FILE_ENCRYPTION_KEY requise pour la rotation KEK")
            sys.exit(1)
        _validate_hex_key(old_kek_hex, "ancienne FILE_ENCRYPTION_KEY")
        new_kek_hex = settings.FILE_ENCRYPTION_KEY
        if not new_kek_hex:
            logger.error("ERREUR: FILE_ENCRYPTION_KEY doit être définie dans l'environnement (nouvelle clé)")
            sys.exit(1)
        _validate_hex_key(new_kek_hex, "FILE_ENCRYPTION_KEY (nouvelle)")
        if old_kek_hex == new_kek_hex:
            logger.error("ERREUR: ancienne et nouvelle FILE_ENCRYPTION_KEY identiques")
            sys.exit(1)

    if rotation_type in ("encryption", "all"):
        if not old_enc_hex:
            logger.error("ERREUR: ancienne ENCRYPTION_KEY requise pour la rotation des colonnes chiffrées")
            sys.exit(1)
        _validate_hex_key(old_enc_hex, "ancienne ENCRYPTION_KEY")
        new_enc_hex = settings.ENCRYPTION_KEY
        if not new_enc_hex:
            logger.error("ERREUR: ENCRYPTION_KEY doit être définie dans l'environnement (nouvelle clé)")
            sys.exit(1)
        _validate_hex_key(new_enc_hex, "ENCRYPTION_KEY (nouvelle)")
        if old_enc_hex == new_enc_hex:
            logger.error("ERREUR: ancienne et nouvelle ENCRYPTION_KEY identiques")
            sys.exit(1)

    # --- Connexion DB ---
    engine = create_engine(settings.DATABASE_URL)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    if not apply:
        logger.info("=== MODE DRY-RUN — ajouter --apply pour exécuter ===")

    try:
        # --- Vérification pré-rotation ---
        if verify:
            logger.info("--- Vérification pré-rotation ---")
            verify_pre_rotation(session, rotation_type)

        # --- Rotation KEK (FILE_ENCRYPTION_KEY) ---
        if rotation_type in ("kek", "all"):
            logger.info("--- Rotation FILE_ENCRYPTION_KEY (KEK) ---")
            kek_ok, kek_err = rotate_kek(old_kek_hex, new_kek_hex, session, apply=apply)
            logger.info("KEK : %d OK, %d erreurs", kek_ok, kek_err)

        # --- Rotation ENCRYPTION_KEY (colonnes) ---
        if rotation_type in ("encryption", "all"):
            logger.info("--- Rotation ENCRYPTION_KEY (colonnes chiffrées) ---")
            enc_ok, enc_err = rotate_encryption_key(old_enc_hex, new_enc_hex, session, apply=apply)
            logger.info("ENCRYPTION_KEY : %d OK, %d erreurs", enc_ok, enc_err)

        # --- Commit transactionnel ---
        if apply:
            session.commit()
            logger.info("Rotation appliquée avec succès (commit effectué)")
        else:
            session.rollback()
            logger.info("DRY-RUN terminé — aucune modification en base")

    except Exception as exc:
        session.rollback()
        logger.error("ERREUR FATALE — rollback complet effectué : %s", exc)
        sys.exit(1)
    finally:
        session.close()


# ===================================================================
# CLI
# ===================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Rotation transactionnelle des clés de chiffrement (dry-run par défaut)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  # Dry-run rotation KEK
  python scripts/rotate_kek.py --type kek OLD_FILE_KEY

  # Appliquer rotation ENCRYPTION_KEY
  python scripts/rotate_kek.py --type encryption OLD_ENC_KEY --apply

  # Rotation complète avec vérification
  python scripts/rotate_kek.py --type all OLD_FILE_KEY OLD_ENC_KEY --apply --verify
        """,
    )
    parser.add_argument(
        "--type",
        choices=["kek", "encryption", "all"],
        default="kek",
        help="Type de rotation : kek (FILE_ENCRYPTION_KEY), encryption (ENCRYPTION_KEY), all (les deux)",
    )
    parser.add_argument(
        "old_keys",
        nargs="+",
        help="Ancienne(s) clé(s) hex 64 chars. 1 clé pour kek/encryption, 2 clés pour all (KEK puis ENC)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Appliquer la rotation (sinon dry-run)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Vérification pré-rotation (compte les enregistrements concernés)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Activer le logging DEBUG",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("rotate_keys").setLevel(logging.DEBUG)

    # Valider le nombre de clés fournies
    if args.type == "all" and len(args.old_keys) < 2:
        parser.error("--type all nécessite 2 clés : OLD_FILE_KEY OLD_ENCRYPTION_KEY")
    if args.type in ("kek", "encryption") and len(args.old_keys) < 1:
        parser.error(f"--type {args.type} nécessite 1 clé ancienne")

    old_kek_hex = None
    old_enc_hex = None

    if args.type == "kek":
        old_kek_hex = args.old_keys[0]
    elif args.type == "encryption":
        old_enc_hex = args.old_keys[0]
    elif args.type == "all":
        old_kek_hex = args.old_keys[0]
        old_enc_hex = args.old_keys[1]

    run_rotation(
        rotation_type=args.type,
        old_kek_hex=old_kek_hex,
        old_enc_hex=old_enc_hex,
        apply=args.apply,
        verify=args.verify,
    )
