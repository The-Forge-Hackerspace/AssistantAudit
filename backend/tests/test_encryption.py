"""
Tests unitaires pour core/encryption.py
- AES256GCMCipher : encrypt/decrypt
- EncryptedText : TypeDecorator SQLAlchemy
"""
import json
import os

import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.encryption import AES256GCMCipher, EncryptedText

# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────

TEST_KEY_HEX = os.urandom(32).hex()  # 64 chars hex, genere une fois par session


@pytest.fixture
def cipher():
    """AES256GCMCipher avec une cle de test."""
    return AES256GCMCipher(TEST_KEY_HEX)


# ────────────────────────────────────────────────────────────────────────
# AES256GCMCipher — Tests
# ────────────────────────────────────────────────────────────────────────


class TestAES256GCMCipher:
    """Tests de la classe AES256GCMCipher."""

    def test_encrypt_decrypt_roundtrip(self, cipher):
        """Chiffre puis dechiffre une chaine : on retrouve l'original."""
        plaintext = "Hello, World! Données sensibles avec accents: éàü"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_produces_hex_string(self, cipher):
        """Le resultat du chiffrement est un hex string valide."""
        encrypted = cipher.encrypt("test")
        # Doit etre un hex string valide
        bytes.fromhex(encrypted)
        # nonce (12B) + plaintext chiffre + tag (16B) >= 12+4+16 = 32 bytes = 64 hex chars
        assert len(encrypted) >= 64

    def test_encrypt_different_nonces(self, cipher):
        """Deux chiffrements du meme texte produisent des resultats differents (nonce aleatoire)."""
        plaintext = "same text"
        encrypted1 = cipher.encrypt(plaintext)
        encrypted2 = cipher.encrypt(plaintext)
        assert encrypted1 != encrypted2
        # Mais les deux dechiffrent vers le meme texte
        assert cipher.decrypt(encrypted1) == plaintext
        assert cipher.decrypt(encrypted2) == plaintext

    def test_encrypt_empty_string(self, cipher):
        """Chiffrement d'une chaine vide fonctionne."""
        encrypted = cipher.encrypt("")
        assert cipher.decrypt(encrypted) == ""

    def test_encrypt_unicode(self, cipher):
        """Chiffrement de texte Unicode complexe."""
        plaintext = "日本語テスト 🔐 Données françaises àéïôù"
        encrypted = cipher.encrypt(plaintext)
        assert cipher.decrypt(encrypted) == plaintext

    def test_decrypt_wrong_key_raises(self):
        """Dechiffrement avec une mauvaise cle leve une exception."""
        key1 = os.urandom(32).hex()
        key2 = os.urandom(32).hex()
        cipher1 = AES256GCMCipher(key1)
        cipher2 = AES256GCMCipher(key2)
        encrypted = cipher1.encrypt("secret")
        with pytest.raises(Exception):  # InvalidTag from cryptography
            cipher2.decrypt(encrypted)

    def test_invalid_key_empty(self):
        """Cle vide leve ValueError."""
        with pytest.raises(ValueError, match="64-character hex string"):
            AES256GCMCipher("")

    def test_invalid_key_too_short(self):
        """Cle trop courte leve ValueError."""
        with pytest.raises(ValueError, match="64-character hex string"):
            AES256GCMCipher("abcd1234")

    def test_invalid_key_too_long(self):
        """Cle trop longue leve ValueError."""
        with pytest.raises(ValueError, match="64-character hex string"):
            AES256GCMCipher("a" * 128)

    def test_invalid_key_not_hex(self):
        """Cle non-hex leve ValueError."""
        with pytest.raises(ValueError, match="hexadecimal"):
            AES256GCMCipher("g" * 64)

    def test_invalid_key_none(self):
        """Cle None leve ValueError."""
        with pytest.raises(ValueError, match="64-character hex string"):
            AES256GCMCipher(None)


# ────────────────────────────────────────────────────────────────────────
# EncryptedText TypeDecorator — Tests avec SQLAlchemy en memoire
# ────────────────────────────────────────────────────────────────────────


class SecretNote(Base):
    """Modele de test pour EncryptedText — utilise uniquement dans les tests."""
    __tablename__ = "test_secret_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    secret_content = Column(EncryptedText, nullable=True)


class TestEncryptedText:
    """Tests du TypeDecorator EncryptedText avec un modele SQLAlchemy de test."""

    @pytest.fixture
    def encrypted_db(self, monkeypatch):
        """DB en memoire avec ENCRYPTION_KEY configuree."""
        monkeypatch.setenv("ENCRYPTION_KEY", TEST_KEY_HEX)
        # Invalider le cache de get_settings pour que la nouvelle env var soit prise en compte
        from app.core.config import get_settings
        get_settings.cache_clear()

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SecretNote.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        session = TestSession()

        yield session

        session.close()
        SecretNote.metadata.drop_all(bind=engine)
        # Restaurer le cache
        get_settings.cache_clear()

    @pytest.fixture
    def unencrypted_db(self, monkeypatch):
        """DB en memoire SANS ENCRYPTION_KEY (mode dev)."""
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("ENCRYPTION_KEY", "")
        from app.core.config import get_settings
        get_settings.cache_clear()

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SecretNote.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        session = TestSession()

        yield session

        session.close()
        SecretNote.metadata.drop_all(bind=engine)
        get_settings.cache_clear()

    def test_roundtrip_string(self, encrypted_db: Session):
        """Ecrire et relire une chaine via EncryptedText."""
        note = SecretNote(title="test", secret_content="Mon secret")
        encrypted_db.add(note)
        encrypted_db.commit()
        encrypted_db.refresh(note)

        assert note.secret_content == "Mon secret"

    def test_roundtrip_none(self, encrypted_db: Session):
        """None reste None, pas de chiffrement."""
        note = SecretNote(title="test", secret_content=None)
        encrypted_db.add(note)
        encrypted_db.commit()
        encrypted_db.refresh(note)

        assert note.secret_content is None

    def test_roundtrip_dict(self, encrypted_db: Session):
        """Un dict est serialise en JSON puis chiffre."""
        data = {"vulns": ["CVE-2024-1234"], "score": 9.8}
        note = SecretNote(title="test", secret_content=data)
        encrypted_db.add(note)
        encrypted_db.commit()

        # Relire depuis la DB
        encrypted_db.expire(note)
        result = encrypted_db.get(SecretNote, note.id)
        # Le TypeDecorator retourne un string JSON dechiffre
        parsed = json.loads(result.secret_content)
        assert parsed == data

    def test_roundtrip_list(self, encrypted_db: Session):
        """Une liste est serialisee en JSON puis chiffree."""
        data = ["item1", "item2", "item3"]
        note = SecretNote(title="test", secret_content=data)
        encrypted_db.add(note)
        encrypted_db.commit()

        encrypted_db.expire(note)
        result = encrypted_db.get(SecretNote, note.id)
        parsed = json.loads(result.secret_content)
        assert parsed == data

    def test_data_encrypted_at_rest(self, encrypted_db: Session):
        """Verifier que la valeur en base n'est PAS en clair."""
        note = SecretNote(title="test", secret_content="top secret data")
        encrypted_db.add(note)
        encrypted_db.commit()

        # Lire la valeur brute en base (contourne le TypeDecorator)
        from sqlalchemy import text
        raw = encrypted_db.execute(
            text("SELECT secret_content FROM test_secret_notes WHERE id = :id"),
            {"id": note.id},
        ).scalar()

        assert raw is not None
        assert raw != "top secret data"
        # La valeur brute doit etre un hex string valide
        bytes.fromhex(raw)

    def test_dev_mode_no_encryption(self, unencrypted_db: Session):
        """Sans ENCRYPTION_KEY, les donnees sont stockees en clair."""
        note = SecretNote(title="test", secret_content="plaintext data")
        unencrypted_db.add(note)
        unencrypted_db.commit()

        from sqlalchemy import text
        raw = unencrypted_db.execute(
            text("SELECT secret_content FROM test_secret_notes WHERE id = :id"),
            {"id": note.id},
        ).scalar()

        assert raw == "plaintext data"

    def test_roundtrip_unicode(self, encrypted_db: Session):
        """Texte Unicode survit au chiffrement/dechiffrement via ORM."""
        content = "Résultats d'audit : vulnérabilités détectées 🔒"
        note = SecretNote(title="test", secret_content=content)
        encrypted_db.add(note)
        encrypted_db.commit()
        encrypted_db.refresh(note)

        assert note.secret_content == content
