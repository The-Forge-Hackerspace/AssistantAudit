"""
Chiffrement enveloppe (Envelope Encryption) pour les fichiers preuves sur disque.

Architecture deux niveaux :
- Chaque fichier est chiffre avec une DEK (Data Encryption Key) unique et aleatoire
- La DEK est elle-meme chiffree avec la KEK (Key Encryption Key) globale
- La DEK chiffree + son nonce sont stockes en base (modele Attachment)
- Le fichier chiffre est stocke sur disque sous un nom UUID

Avantage : la rotation de la KEK ne necessite que de re-chiffrer les DEK (quelques bytes),
pas les fichiers (potentiellement des centaines de Mo).

Si FILE_ENCRYPTION_KEY est vide, le chiffrement est desactive (mode dev uniquement).
"""
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


def _validate_kek(key_hex: str) -> bytes:
    """Valide et convertit une KEK hex en bytes."""
    if not key_hex or len(key_hex) != 64:
        raise ValueError(
            "FILE_ENCRYPTION_KEY must be a 64-character hex string (256 bits). "
            "Generez avec : python -c 'import os; print(os.urandom(32).hex())'"
        )
    try:
        return bytes.fromhex(key_hex)
    except ValueError:
        raise ValueError("FILE_ENCRYPTION_KEY must contain only hexadecimal characters")


class EnvelopeEncryption:
    """
    Chiffrement enveloppe pour les fichiers preuves sur disque.

    Usage :
        envelope = EnvelopeEncryption()
        encrypted_file, encrypted_dek, dek_nonce = envelope.encrypt_file(data)
        # Stocker encrypted_file sur disque, encrypted_dek + dek_nonce en base
        original = envelope.decrypt_file(encrypted_file, encrypted_dek, dek_nonce)
    """

    def __init__(self):
        from app.core.config import get_settings
        key_hex = get_settings().FILE_ENCRYPTION_KEY
        if not key_hex:
            logger.warning(
                "FILE_ENCRYPTION_KEY non configuree — chiffrement fichier desactive (dev only)"
            )
            self.kek = None
        else:
            self.kek = _validate_kek(key_hex)

    @property
    def enabled(self) -> bool:
        """True si le chiffrement fichier est actif."""
        return self.kek is not None

    def encrypt_file(self, plaintext_data: bytes) -> tuple[bytes, bytes, bytes]:
        """
        Chiffre des donnees fichier.

        Returns:
            (encrypted_file_data, encrypted_dek, dek_nonce)
            - encrypted_file_data : nonce_fichier (12B) || ciphertext+tag -> a ecrire sur disque
            - encrypted_dek : la DEK chiffree avec la KEK -> a stocker en base
            - dek_nonce : le nonce utilise pour chiffrer la DEK -> a stocker en base
        """
        if not self.enabled:
            # Mode dev : pas de chiffrement, DEK/nonce vides
            return plaintext_data, b"", b""

        # 1. Generer une DEK aleatoire
        dek = os.urandom(32)  # 256 bits

        # 2. Chiffrer le fichier avec la DEK
        file_nonce = os.urandom(12)
        aesgcm_file = AESGCM(dek)
        encrypted_file = file_nonce + aesgcm_file.encrypt(file_nonce, plaintext_data, None)

        # 3. Chiffrer la DEK avec la KEK
        dek_nonce = os.urandom(12)
        aesgcm_kek = AESGCM(self.kek)
        encrypted_dek = aesgcm_kek.encrypt(dek_nonce, dek, None)

        return encrypted_file, encrypted_dek, dek_nonce

    def decrypt_file(
        self, encrypted_file_data: bytes, encrypted_dek: bytes, dek_nonce: bytes
    ) -> bytes:
        """
        Dechiffre des donnees fichier.

        Args:
            encrypted_file_data : contenu lu depuis le disque (nonce || ciphertext+tag)
            encrypted_dek : DEK chiffree lue depuis la base
            dek_nonce : nonce de la DEK lu depuis la base
        """
        if not self.enabled:
            # Mode dev : donnees non chiffrees
            return encrypted_file_data

        # 1. Dechiffrer la DEK avec la KEK
        aesgcm_kek = AESGCM(self.kek)
        dek = aesgcm_kek.decrypt(dek_nonce, encrypted_dek, None)

        # 2. Dechiffrer le fichier avec la DEK
        file_nonce = encrypted_file_data[:12]
        file_ciphertext = encrypted_file_data[12:]
        aesgcm_file = AESGCM(dek)
        return aesgcm_file.decrypt(file_nonce, file_ciphertext, None)

    @staticmethod
    def rotate_kek(
        encrypted_dek: bytes, dek_nonce: bytes, old_kek_hex: str, new_kek_hex: str
    ) -> tuple[bytes, bytes]:
        """
        Re-chiffre une DEK avec une nouvelle KEK.
        Appele lors de la rotation de cle — itere sur tous les Attachments.

        Args:
            encrypted_dek : DEK chiffree avec l'ancienne KEK
            dek_nonce : nonce utilise pour chiffrer la DEK avec l'ancienne KEK
            old_kek_hex : ancienne KEK en hex (64 chars)
            new_kek_hex : nouvelle KEK en hex (64 chars)

        Returns:
            (new_encrypted_dek, new_dek_nonce)
        """
        old_kek = _validate_kek(old_kek_hex)
        new_kek = _validate_kek(new_kek_hex)

        # Dechiffrer la DEK avec l'ancienne KEK
        aesgcm_old = AESGCM(old_kek)
        dek = aesgcm_old.decrypt(dek_nonce, encrypted_dek, None)

        # Re-chiffrer avec la nouvelle KEK
        new_nonce = os.urandom(12)
        aesgcm_new = AESGCM(new_kek)
        new_encrypted_dek = aesgcm_new.encrypt(new_nonce, dek, None)

        return new_encrypted_dek, new_nonce
