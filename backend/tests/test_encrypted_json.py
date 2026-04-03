"""
Tests unitaires pour EncryptedJSON (core/encryption.py)
- Round-trip dict et list via SQLAlchemy ORM
- Chiffrement effectif au repos
- Mode dev (ENCRYPTION_KEY vide)
- Valeurs None
"""

import json
import os

import pytest
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.encryption import EncryptedJSON

TEST_KEY_HEX = os.urandom(32).hex()


# ────────────────────────────────────────────────────────────────────────
# Modele de test
# ────────────────────────────────────────────────────────────────────────


class EncryptedJsonRecord(Base):
    """Modele de test pour EncryptedJSON — utilise uniquement dans les tests."""

    __tablename__ = "test_encrypted_json_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(200), nullable=False)
    payload = Column(EncryptedJSON, nullable=True)


# ────────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────────


class TestEncryptedJSON:
    """Tests du TypeDecorator EncryptedJSON avec un modele SQLAlchemy de test."""

    @pytest.fixture
    def encrypted_db(self, monkeypatch):
        """DB en memoire avec ENCRYPTION_KEY configuree."""
        monkeypatch.setenv("ENCRYPTION_KEY", TEST_KEY_HEX)
        from app.core.config import get_settings

        get_settings.cache_clear()

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        EncryptedJsonRecord.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        session = TestSession()

        yield session

        session.close()
        EncryptedJsonRecord.metadata.drop_all(bind=engine)
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
        EncryptedJsonRecord.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        session = TestSession()

        yield session

        session.close()
        EncryptedJsonRecord.metadata.drop_all(bind=engine)
        get_settings.cache_clear()

    # ── Round-trip dict ──

    def test_roundtrip_dict(self, encrypted_db: Session):
        """Un dict est serialise en JSON, chiffre, puis restaure a l'identique."""
        data = {"targets": ["192.168.1.0/24"], "ports": "1-1024", "fast": True}
        record = EncryptedJsonRecord(label="test_dict", payload=data)
        encrypted_db.add(record)
        encrypted_db.commit()

        encrypted_db.expire(record)
        result = encrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload == data
        assert isinstance(result.payload, dict)

    # ── Round-trip list ──

    def test_roundtrip_list(self, encrypted_db: Session):
        """Une liste est serialisee en JSON, chiffree, puis restauree a l'identique."""
        data = [{"cn": "DC01", "ip": "10.0.0.1"}, {"cn": "DC02", "ip": "10.0.0.2"}]
        record = EncryptedJsonRecord(label="test_list", payload=data)
        encrypted_db.add(record)
        encrypted_db.commit()

        encrypted_db.expire(record)
        result = encrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload == data
        assert isinstance(result.payload, list)

    # ── None ──

    def test_roundtrip_none(self, encrypted_db: Session):
        """None reste None, pas de chiffrement."""
        record = EncryptedJsonRecord(label="test_none", payload=None)
        encrypted_db.add(record)
        encrypted_db.commit()

        encrypted_db.expire(record)
        result = encrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload is None

    # ── Nested structures ──

    def test_roundtrip_nested(self, encrypted_db: Session):
        """Structures JSON imbriquees complexes."""
        data = {
            "scan": {
                "hosts": [
                    {"ip": "10.0.0.1", "ports": [22, 80, 443], "os": "Linux"},
                    {"ip": "10.0.0.2", "ports": [3389], "os": "Windows"},
                ],
                "metadata": {"duration": 42.5, "version": "1.0"},
            }
        }
        record = EncryptedJsonRecord(label="test_nested", payload=data)
        encrypted_db.add(record)
        encrypted_db.commit()

        encrypted_db.expire(record)
        result = encrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload == data

    # ── Unicode ──

    def test_roundtrip_unicode(self, encrypted_db: Session):
        """Texte Unicode dans les valeurs JSON."""
        data = {"description": "Résultat d'audit avec accents éàü 🔐"}
        record = EncryptedJsonRecord(label="test_unicode", payload=data)
        encrypted_db.add(record)
        encrypted_db.commit()

        encrypted_db.expire(record)
        result = encrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload == data

    # ── Chiffrement effectif au repos ──

    def test_data_encrypted_at_rest(self, encrypted_db: Session):
        """La valeur brute en base n'est PAS du JSON lisible."""
        data = {"secret": "mot_de_passe_admin"}
        record = EncryptedJsonRecord(label="test_rest", payload=data)
        encrypted_db.add(record)
        encrypted_db.commit()

        raw = encrypted_db.execute(
            text("SELECT payload FROM test_encrypted_json_records WHERE id = :id"),
            {"id": record.id},
        ).scalar()

        assert raw is not None
        # La valeur brute ne doit pas etre du JSON lisible
        assert raw != json.dumps(data, ensure_ascii=False)
        # Doit etre un hex string valide (nonce + ciphertext + tag)
        bytes.fromhex(raw)

    # ── Mode dev (pas de chiffrement) ──

    def test_dev_mode_no_encryption(self, unencrypted_db: Session):
        """Sans ENCRYPTION_KEY, les donnees sont stockees en JSON clair."""
        data = {"target": "192.168.1.1"}
        record = EncryptedJsonRecord(label="test_dev", payload=data)
        unencrypted_db.add(record)
        unencrypted_db.commit()

        raw = unencrypted_db.execute(
            text("SELECT payload FROM test_encrypted_json_records WHERE id = :id"),
            {"id": record.id},
        ).scalar()

        assert json.loads(raw) == data

    def test_dev_mode_roundtrip(self, unencrypted_db: Session):
        """Sans ENCRYPTION_KEY, le round-trip fonctionne quand meme."""
        data = [1, 2, 3]
        record = EncryptedJsonRecord(label="test_dev_rt", payload=data)
        unencrypted_db.add(record)
        unencrypted_db.commit()

        unencrypted_db.expire(record)
        result = unencrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload == data

    # ── Valeurs edge-case ──

    def test_empty_dict(self, encrypted_db: Session):
        """Dict vide fonctionne."""
        record = EncryptedJsonRecord(label="test_empty_dict", payload={})
        encrypted_db.add(record)
        encrypted_db.commit()

        encrypted_db.expire(record)
        result = encrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload == {}

    def test_empty_list(self, encrypted_db: Session):
        """Liste vide fonctionne."""
        record = EncryptedJsonRecord(label="test_empty_list", payload=[])
        encrypted_db.add(record)
        encrypted_db.commit()

        encrypted_db.expire(record)
        result = encrypted_db.get(EncryptedJsonRecord, record.id)
        assert result.payload == []
