"""
Tests pour les permissions du fichier ca.key (chmod 600).
"""
import logging
import os

from app.core.cert_manager import CertManager


class TestCaKeyPermissions:
    """Verifie que generate_ca applique chmod 600 sur ca.key."""

    def test_generate_ca_sets_600(self, tmp_path):
        """Apres generate_ca, ca.key a les permissions 0o600."""
        ca_cert = tmp_path / "ca.crt"
        ca_key = tmp_path / "ca.key"
        CertManager.generate_ca(ca_cert, ca_key)

        mode = ca_key.stat().st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    def test_generate_ca_cert_exists(self, tmp_path):
        """generate_ca cree bien les deux fichiers."""
        ca_cert = tmp_path / "ca.crt"
        ca_key = tmp_path / "ca.key"
        CertManager.generate_ca(ca_cert, ca_key)

        assert ca_cert.exists()
        assert ca_key.exists()

    def test_insecure_permissions_logs_warning(self, tmp_path, caplog):
        """Si ca.key a des permissions != 600, un WARNING est loggue."""
        ca_cert = tmp_path / "ca.crt"
        ca_key = tmp_path / "ca.key"
        CertManager.generate_ca(ca_cert, ca_key)

        # Mettre des permissions trop larges
        os.chmod(ca_key, 0o644)

        with caplog.at_level(logging.WARNING, logger="app.core.cert_manager"):
            CertManager(ca_cert, ca_key)

        assert any("insecure permissions" in r.message for r in caplog.records)

    def test_correct_permissions_no_warning(self, tmp_path, caplog):
        """Si ca.key a les bonnes permissions, pas de warning."""
        ca_cert = tmp_path / "ca.crt"
        ca_key = tmp_path / "ca.key"
        CertManager.generate_ca(ca_cert, ca_key)

        # Permissions deja correctes (600 apres generate_ca)
        with caplog.at_level(logging.WARNING, logger="app.core.cert_manager"):
            CertManager(ca_cert, ca_key)

        assert not any("insecure permissions" in r.message for r in caplog.records)

    def test_missing_key_no_crash(self, tmp_path):
        """Si ca.key n'existe pas encore, __init__ ne crashe pas."""
        ca_cert = tmp_path / "ca.crt"
        ca_key = tmp_path / "ca.key"
        # Pas de generate_ca — fichiers inexistants
        mgr = CertManager(ca_cert, ca_key)
        assert mgr.ca_key_path == ca_key
