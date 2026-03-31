"""
Tests TD-002 : rotation KEK complète.
"""
import os

import pytest
from cryptography.exceptions import InvalidTag

from app.core.file_encryption import EnvelopeEncryption


class TestRotateKek:
    """TD-002 : rotation KEK complète."""

    def test_rotate_kek_changes_encrypted_dek(self):
        """La rotation doit produire un DEK chiffré différent."""
        old_kek = os.urandom(32).hex()
        new_kek = os.urandom(32).hex()

        enc = EnvelopeEncryption(old_kek)
        plaintext = b"test data for rotation"
        encrypted_file, encrypted_dek, dek_nonce = enc.encrypt_file(plaintext)

        # Rotation
        new_encrypted_dek, new_nonce = EnvelopeEncryption.rotate_kek(
            encrypted_dek, dek_nonce, old_kek, new_kek
        )

        # Le DEK chiffré a changé
        assert new_encrypted_dek != encrypted_dek

        # Déchiffrement avec la nouvelle KEK fonctionne
        enc_new = EnvelopeEncryption(new_kek)
        decrypted = enc_new.decrypt_file(encrypted_file, new_encrypted_dek, new_nonce)
        assert decrypted == plaintext

    def test_rotate_kek_old_key_still_decrypts_before_rotation(self):
        """Avant rotation, l'ancienne KEK fonctionne toujours."""
        old_kek = os.urandom(32).hex()
        enc = EnvelopeEncryption(old_kek)

        plaintext = b"data before rotation"
        encrypted_file, encrypted_dek, dek_nonce = enc.encrypt_file(plaintext)

        decrypted = enc.decrypt_file(encrypted_file, encrypted_dek, dek_nonce)
        assert decrypted == plaintext

    def test_rotate_kek_old_key_fails_after_rotation(self):
        """Après rotation, l'ancienne KEK ne déchiffre plus le nouveau DEK."""
        old_kek = os.urandom(32).hex()
        new_kek = os.urandom(32).hex()

        enc_old = EnvelopeEncryption(old_kek)
        plaintext = b"data for rotation test"
        encrypted_file, encrypted_dek, dek_nonce = enc_old.encrypt_file(plaintext)

        # Rotation
        new_encrypted_dek, new_nonce = EnvelopeEncryption.rotate_kek(
            encrypted_dek, dek_nonce, old_kek, new_kek
        )

        # L'ancienne KEK ne déchiffre plus le nouveau DEK
        with pytest.raises((InvalidTag, Exception)):
            enc_old.decrypt_file(encrypted_file, new_encrypted_dek, new_nonce)
