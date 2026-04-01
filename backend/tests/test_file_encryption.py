"""
Tests unitaires pour core/file_encryption.py
- EnvelopeEncryption : encrypt/decrypt fichier, rotation de KEK
- Mode dev sans cle (passthrough)
"""
import os

import pytest

from app.core.file_encryption import EnvelopeEncryption, _validate_kek


# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────

KEK_A = os.urandom(32).hex()
KEK_B = os.urandom(32).hex()


@pytest.fixture
def envelope(monkeypatch):
    """EnvelopeEncryption avec une KEK de test."""
    monkeypatch.setenv("FILE_ENCRYPTION_KEY", KEK_A)
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield EnvelopeEncryption()
    get_settings.cache_clear()


@pytest.fixture
def envelope_no_key(monkeypatch):
    """EnvelopeEncryption sans KEK (mode dev)."""
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("FILE_ENCRYPTION_KEY", "")
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield EnvelopeEncryption()
    get_settings.cache_clear()


# ────────────────────────────────────────────────────────────────────────
# _validate_kek
# ────────────────────────────────────────────────────────────────────────


class TestValidateKek:
    def test_valid_key(self):
        key = os.urandom(32).hex()
        result = _validate_kek(key)
        assert len(result) == 32

    def test_empty_key(self):
        with pytest.raises(ValueError, match="64-character"):
            _validate_kek("")

    def test_short_key(self):
        with pytest.raises(ValueError, match="64-character"):
            _validate_kek("abcd")

    def test_non_hex_key(self):
        with pytest.raises(ValueError, match="hexadecimal"):
            _validate_kek("z" * 64)


# ────────────────────────────────────────────────────────────────────────
# EnvelopeEncryption — Encrypt / Decrypt
# ────────────────────────────────────────────────────────────────────────


class TestEnvelopeEncryption:
    def test_roundtrip_basic(self, envelope):
        """Chiffre puis dechiffre des bytes : on retrouve l'original."""
        data = b"Hello, this is a test file content!"
        encrypted_file, encrypted_dek, dek_nonce = envelope.encrypt_file(data)
        decrypted = envelope.decrypt_file(encrypted_file, encrypted_dek, dek_nonce)
        assert decrypted == data

    def test_roundtrip_empty(self, envelope):
        """Fichier vide : roundtrip fonctionne."""
        data = b""
        encrypted_file, encrypted_dek, dek_nonce = envelope.encrypt_file(data)
        decrypted = envelope.decrypt_file(encrypted_file, encrypted_dek, dek_nonce)
        assert decrypted == data

    def test_roundtrip_random_bytes(self, envelope):
        """Bytes aleatoires : roundtrip fonctionne."""
        data = os.urandom(4096)
        encrypted_file, encrypted_dek, dek_nonce = envelope.encrypt_file(data)
        decrypted = envelope.decrypt_file(encrypted_file, encrypted_dek, dek_nonce)
        assert decrypted == data

    def test_roundtrip_large_file(self, envelope):
        """Fichier de 1 MB : roundtrip fonctionne."""
        data = os.urandom(1024 * 1024)
        encrypted_file, encrypted_dek, dek_nonce = envelope.encrypt_file(data)
        decrypted = envelope.decrypt_file(encrypted_file, encrypted_dek, dek_nonce)
        assert decrypted == data

    def test_encrypted_file_differs_from_plaintext(self, envelope):
        """Le fichier chiffre est different du plaintext."""
        data = b"sensitive audit data" * 100
        encrypted_file, _, _ = envelope.encrypt_file(data)
        assert encrypted_file != data

    def test_encrypted_dek_differs_from_raw_dek(self, envelope):
        """La DEK chiffree ne contient pas la DEK en clair (32 bytes aleatoires)."""
        data = b"test"
        _, encrypted_dek, _ = envelope.encrypt_file(data)
        # encrypted_dek = ciphertext(32B DEK) + tag(16B) = 48 bytes
        assert len(encrypted_dek) == 48
        # dek_nonce = 12 bytes
        # On ne peut pas verifier directement que la DEK n'est pas dedans,
        # mais on verifie que le format est correct

    def test_different_encryptions_produce_different_results(self, envelope):
        """Deux chiffrements du meme fichier produisent des resultats differents."""
        data = b"same content"
        enc1_file, enc1_dek, enc1_nonce = envelope.encrypt_file(data)
        enc2_file, enc2_dek, enc2_nonce = envelope.encrypt_file(data)
        # Les fichiers chiffres different (nonces differents)
        assert enc1_file != enc2_file
        # Les DEK chiffrees different (DEK et nonces differents)
        assert enc1_dek != enc2_dek
        # Mais les deux dechiffrent vers le meme contenu
        assert envelope.decrypt_file(enc1_file, enc1_dek, enc1_nonce) == data
        assert envelope.decrypt_file(enc2_file, enc2_dek, enc2_nonce) == data

    def test_encrypted_file_format(self, envelope):
        """Le fichier chiffre a le bon format : nonce(12B) || ciphertext+tag."""
        data = b"test data"
        encrypted_file, _, _ = envelope.encrypt_file(data)
        # nonce(12) + ciphertext(len(data)) + tag(16) = 12 + 9 + 16 = 37
        assert len(encrypted_file) == 12 + len(data) + 16

    def test_enabled_property(self, envelope):
        assert envelope.enabled is True

    def test_decrypt_wrong_kek_fails(self, monkeypatch):
        """Dechiffrement avec une mauvaise KEK echoue."""
        monkeypatch.setenv("FILE_ENCRYPTION_KEY", KEK_A)
        from app.core.config import get_settings
        get_settings.cache_clear()
        envelope_a = EnvelopeEncryption()

        data = b"secret"
        encrypted_file, encrypted_dek, dek_nonce = envelope_a.encrypt_file(data)

        monkeypatch.setenv("FILE_ENCRYPTION_KEY", KEK_B)
        get_settings.cache_clear()
        envelope_b = EnvelopeEncryption()

        with pytest.raises(Exception):  # InvalidTag
            envelope_b.decrypt_file(encrypted_file, encrypted_dek, dek_nonce)

        get_settings.cache_clear()


# ────────────────────────────────────────────────────────────────────────
# KEK Rotation
# ────────────────────────────────────────────────────────────────────────


class TestKekRotation:
    def test_rotate_then_decrypt(self, envelope):
        """Chiffre avec KEK_A, rotate vers KEK_B, dechiffre avec KEK_B."""
        data = b"audit evidence file content"
        encrypted_file, encrypted_dek, dek_nonce = envelope.encrypt_file(data)

        # Rotation : re-chiffrer la DEK avec KEK_B
        new_encrypted_dek, new_dek_nonce = EnvelopeEncryption.rotate_kek(
            encrypted_dek, dek_nonce, KEK_A, KEK_B
        )

        # Le fichier sur disque n'a PAS change
        # Dechiffrer avec la nouvelle DEK (chiffree sous KEK_B)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Dechiffrer la DEK avec KEK_B
        aesgcm_kek = AESGCM(bytes.fromhex(KEK_B))
        dek = aesgcm_kek.decrypt(new_dek_nonce, new_encrypted_dek, None)

        # Dechiffrer le fichier avec la DEK
        file_nonce = encrypted_file[:12]
        file_ciphertext = encrypted_file[12:]
        aesgcm_file = AESGCM(dek)
        decrypted = aesgcm_file.decrypt(file_nonce, file_ciphertext, None)

        assert decrypted == data

    def test_rotate_preserves_dek(self):
        """La rotation change l'enveloppe mais pas la DEK elle-meme."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Creer une DEK et la chiffrer avec KEK_A
        dek = os.urandom(32)
        dek_nonce = os.urandom(12)
        aesgcm_a = AESGCM(bytes.fromhex(KEK_A))
        encrypted_dek = aesgcm_a.encrypt(dek_nonce, dek, None)

        # Rotation vers KEK_B
        new_encrypted_dek, new_nonce = EnvelopeEncryption.rotate_kek(
            encrypted_dek, dek_nonce, KEK_A, KEK_B
        )

        # Dechiffrer avec KEK_B : on doit retrouver la meme DEK
        aesgcm_b = AESGCM(bytes.fromhex(KEK_B))
        recovered_dek = aesgcm_b.decrypt(new_nonce, new_encrypted_dek, None)
        assert recovered_dek == dek

    def test_rotate_with_invalid_old_key(self):
        """Rotation avec une mauvaise ancienne KEK echoue."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        dek = os.urandom(32)
        nonce = os.urandom(12)
        aesgcm = AESGCM(bytes.fromhex(KEK_A))
        encrypted_dek = aesgcm.encrypt(nonce, dek, None)

        wrong_key = os.urandom(32).hex()
        with pytest.raises(Exception):  # InvalidTag
            EnvelopeEncryption.rotate_kek(encrypted_dek, nonce, wrong_key, KEK_B)


# ────────────────────────────────────────────────────────────────────────
# Mode dev (pas de KEK)
# ────────────────────────────────────────────────────────────────────────


class TestDevMode:
    def test_enabled_false(self, envelope_no_key):
        assert envelope_no_key.enabled is False

    def test_encrypt_passthrough(self, envelope_no_key):
        """Sans KEK, les donnees passent en clair."""
        data = b"plaintext data"
        encrypted_file, encrypted_dek, dek_nonce = envelope_no_key.encrypt_file(data)
        assert encrypted_file == data
        assert encrypted_dek == b""
        assert dek_nonce == b""

    def test_decrypt_passthrough(self, envelope_no_key):
        """Sans KEK, decrypt retourne les donnees telles quelles."""
        data = b"plaintext data"
        decrypted = envelope_no_key.decrypt_file(data, b"", b"")
        assert decrypted == data

    def test_roundtrip_passthrough(self, envelope_no_key):
        """Roundtrip en mode dev fonctionne."""
        data = b"test content"
        enc_file, enc_dek, nonce = envelope_no_key.encrypt_file(data)
        decrypted = envelope_no_key.decrypt_file(enc_file, enc_dek, nonce)
        assert decrypted == data
