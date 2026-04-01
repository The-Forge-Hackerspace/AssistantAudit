"""
Chiffrement AES-256-GCM pour les colonnes sensibles en base de donnees.

Fournit :
- AES256GCMCipher : chiffre/dechiffre des chaines avec AES-256-GCM
- EncryptedText : TypeDecorator SQLAlchemy pour chiffrement transparent

Format stocke en base : hex(nonce_12B || ciphertext || tag_16B)
La cle ENCRYPTION_KEY est une variable d'environnement distincte de SECRET_KEY.
"""
import json
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class AES256GCMCipher:
    """
    Chiffrement AES-256-GCM pour les colonnes sensibles en base.
    La cle est un hex string de 64 caracteres (32 bytes = 256 bits).
    """

    def __init__(self, key_hex: str):
        if not key_hex or len(key_hex) != 64:
            raise ValueError(
                "ENCRYPTION_KEY must be a 64-character hex string (256 bits). "
                "Generez avec : python -c 'import os; print(os.urandom(32).hex())'"
            )
        try:
            self.key = bytes.fromhex(key_hex)
        except ValueError:
            raise ValueError("ENCRYPTION_KEY must contain only hexadecimal characters")

    def encrypt(self, plaintext: str) -> str:
        """Chiffre une chaine UTF-8, retourne hex(nonce || ciphertext+tag)."""
        nonce = os.urandom(12)  # 96 bits, recommande pour GCM
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return (nonce + ciphertext).hex()

    def decrypt(self, data_hex: str) -> str:
        """Dechiffre hex(nonce || ciphertext+tag), retourne la chaine UTF-8."""
        raw = bytes.fromhex(data_hex)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


class EncryptedJSON(TypeDecorator):
    """
    Type SQLAlchemy qui serialise en JSON puis chiffre/dechiffre automatiquement.

    Usage :
        parameters = Column(EncryptedJSON, nullable=False)

    En Python on manipule des dict/list natifs, en base c'est chiffre.
    Si ENCRYPTION_KEY est vide, les donnees sont stockees en JSON clair (mode dev).
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Python -> DB : json.dumps puis chiffre."""
        if value is None:
            return None
        json_str = json.dumps(value, ensure_ascii=False)
        cipher = self._get_cipher()
        if cipher is None:
            return json_str  # Mode dev : JSON clair
        return cipher.encrypt(json_str)

    def process_result_value(self, value, dialect):
        """DB -> Python : dechiffre puis json.loads."""
        if value is None:
            return None
        cipher = self._get_cipher()
        if cipher is None:
            json_str = value  # Mode dev : JSON clair
        else:
            json_str = cipher.decrypt(value)
        return json.loads(json_str)

    _warned_no_key = False

    @staticmethod
    def _get_cipher() -> AES256GCMCipher | None:
        """Retourne le cipher si ENCRYPTION_KEY est configuree, sinon None."""
        from app.core.config import get_settings
        key = get_settings().ENCRYPTION_KEY
        if not key:
            if not EncryptedJSON._warned_no_key:
                logger.warning(
                    "ENCRYPTION_KEY non configuree — colonnes EncryptedJSON stockees en clair (dev only)"
                )
                EncryptedJSON._warned_no_key = True
            return None
        return AES256GCMCipher(key)


class EncryptedText(TypeDecorator):
    """
    Type SQLAlchemy qui chiffre/dechiffre automatiquement les colonnes Text.

    Usage :
        results_raw = Column(EncryptedText, nullable=True)

    En Python on manipule du texte clair, en base c'est chiffre.
    Si ENCRYPTION_KEY est vide, les donnees sont stockees en clair (mode dev).
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Python -> DB : chiffre."""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        cipher = self._get_cipher()
        if cipher is None:
            return value  # Mode dev : pas de chiffrement
        return cipher.encrypt(value)

    def process_result_value(self, value, dialect):
        """DB -> Python : dechiffre."""
        if value is None:
            return None
        cipher = self._get_cipher()
        if cipher is None:
            return value  # Mode dev : pas de chiffrement
        return cipher.decrypt(value)

    _warned_no_key = False

    @staticmethod
    def _get_cipher() -> AES256GCMCipher | None:
        """Retourne le cipher si ENCRYPTION_KEY est configuree, sinon None."""
        from app.core.config import get_settings
        key = get_settings().ENCRYPTION_KEY
        if not key:
            if not EncryptedText._warned_no_key:
                logger.warning(
                    "ENCRYPTION_KEY non configuree — colonnes sensibles stockees en clair (dev only)"
                )
                EncryptedText._warned_no_key = True
            return None
        return AES256GCMCipher(key)
