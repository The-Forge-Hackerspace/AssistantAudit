"""
Tests unitaires pour core/cert_manager.py
- Generation CA, signature certificats agent, fingerprint, serial, chain of trust.
Utilise tmp_path pour tous les fichiers — ne touche pas aux vrais certs/.
"""
from pathlib import Path

from datetime import datetime, timedelta, timezone
import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from app.core.cert_manager import CertManager

# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def ca_paths(tmp_path) -> tuple[Path, Path]:
    """Chemins pour la CA dans un dossier temporaire."""
    return tmp_path / "ca.pem", tmp_path / "ca.key"


@pytest.fixture
def ca(ca_paths) -> CertManager:
    """CA generee dans un dossier temporaire."""
    cert_path, key_path = ca_paths
    CertManager.generate_ca(cert_path, key_path)
    return CertManager(cert_path, key_path)


# ────────────────────────────────────────────────────────────────────────
# generate_ca
# ────────────────────────────────────────────────────────────────────────


class TestGenerateCA:
    def test_creates_files(self, ca_paths):
        cert_path, key_path = ca_paths
        CertManager.generate_ca(cert_path, key_path)
        assert cert_path.exists()
        assert key_path.exists()

    def test_cert_is_valid_ca(self, ca_paths):
        cert_path, key_path = ca_paths
        CertManager.generate_ca(cert_path, key_path)
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())

        # BasicConstraints: ca=True
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.value.ca is True
        assert bc.value.path_length == 0
        assert bc.critical is True

    def test_cert_key_usage(self, ca_paths):
        cert_path, key_path = ca_paths
        CertManager.generate_ca(cert_path, key_path)
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())

        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
        assert ku.value.key_cert_sign is True
        assert ku.value.crl_sign is True
        assert ku.value.digital_signature is False
        assert ku.critical is True

    def test_cert_cn(self, ca_paths):
        cert_path, key_path = ca_paths
        CertManager.generate_ca(cert_path, key_path, cn="Test CA")
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())

        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "Test CA"

    def test_cert_self_signed(self, ca_paths):
        cert_path, key_path = ca_paths
        CertManager.generate_ca(cert_path, key_path)
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())

        assert cert.subject == cert.issuer

    def test_key_is_rsa_4096(self, ca_paths):
        _, key_path = ca_paths
        CertManager.generate_ca(ca_paths[0], key_path)
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        key = load_pem_private_key(key_path.read_bytes(), password=None)
        assert isinstance(key, rsa.RSAPrivateKey)
        assert key.key_size == 4096

    def test_cert_validity_10_years(self, ca_paths):
        cert_path, key_path = ca_paths
        CertManager.generate_ca(cert_path, key_path)
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())

        delta = cert.not_valid_after_utc - cert.not_valid_before_utc
        assert delta.days >= 3649  # ~10 years

    def test_creates_parent_dirs(self, tmp_path):
        deep_cert = tmp_path / "a" / "b" / "ca.pem"
        deep_key = tmp_path / "a" / "b" / "ca.key"
        CertManager.generate_ca(deep_cert, deep_key)
        assert deep_cert.exists()


# ────────────────────────────────────────────────────────────────────────
# sign_agent_cert
# ────────────────────────────────────────────────────────────────────────


class TestSignAgentCert:
    def test_returns_pem_bytes(self, ca):
        cert_pem, key_pem = ca.sign_agent_cert("test-uuid-1234")
        assert cert_pem.startswith(b"-----BEGIN CERTIFICATE-----")
        assert key_pem.startswith(b"-----BEGIN PRIVATE KEY-----")

    def test_cert_cn(self, ca):
        cert_pem, _ = ca.sign_agent_cert("my-uuid")
        cert = x509.load_pem_x509_certificate(cert_pem)
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "agent-my-uuid"

    def test_cert_extended_key_usage_client_auth(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-1")
        cert = x509.load_pem_x509_certificate(cert_pem)
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        assert ExtendedKeyUsageOID.CLIENT_AUTH in eku.value
        assert eku.critical is True

    def test_cert_san_contains_agent_uri(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-abc")
        cert = x509.load_pem_x509_certificate(cert_pem)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        uris = san.value.get_values_for_type(x509.UniformResourceIdentifier)
        assert "urn:agent:uuid-abc" in uris

    def test_cert_signed_by_ca(self, ca):
        """Le certificat agent est signe par la CA (chain of trust)."""
        cert_pem, _ = ca.sign_agent_cert("uuid-chain")
        agent_cert = x509.load_pem_x509_certificate(cert_pem)
        ca_cert = x509.load_pem_x509_certificate(ca.ca_cert_path.read_bytes())

        # Issuer du cert agent == Subject de la CA
        assert agent_cert.issuer == ca_cert.subject

        # Verification cryptographique : la cle publique de la CA verifie la signature
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
        ca_cert.public_key().verify(
            agent_cert.signature,
            agent_cert.tbs_certificate_bytes,
            asym_padding.PKCS1v15(),
            agent_cert.signature_hash_algorithm,
        )

    def test_cert_validity_1_year(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-validity")
        cert = x509.load_pem_x509_certificate(cert_pem)
        delta = cert.not_valid_after_utc - cert.not_valid_before_utc
        assert 364 <= delta.days <= 366

    def test_key_is_rsa_2048(self, ca):
        _, key_pem = ca.sign_agent_cert("uuid-key")
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        key = load_pem_private_key(key_pem, password=None)
        assert isinstance(key, rsa.RSAPrivateKey)
        assert key.key_size == 2048

    def test_two_certs_different_serials(self, ca):
        cert1_pem, _ = ca.sign_agent_cert("uuid-a")
        cert2_pem, _ = ca.sign_agent_cert("uuid-b")
        cert1 = x509.load_pem_x509_certificate(cert1_pem)
        cert2 = x509.load_pem_x509_certificate(cert2_pem)
        assert cert1.serial_number != cert2.serial_number

    def test_not_a_ca(self, ca):
        """Le cert agent ne doit PAS etre une CA."""
        cert_pem, _ = ca.sign_agent_cert("uuid-notca")
        cert = x509.load_pem_x509_certificate(cert_pem)
        # Should not have BasicConstraints with ca=True
        try:
            bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
            assert bc.value.ca is False
        except x509.ExtensionNotFound:
            pass  # No BasicConstraints at all is also fine


# ────────────────────────────────────────────────────────────────────────
# Utility methods
# ────────────────────────────────────────────────────────────────────────


class TestUtilities:
    def test_fingerprint_format(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-fp")
        fp = CertManager.get_cert_fingerprint(cert_pem)
        assert isinstance(fp, str)
        assert len(fp) == 64  # SHA-256 = 32 bytes = 64 hex chars
        bytes.fromhex(fp)  # Must be valid hex

    def test_fingerprint_deterministic(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-det")
        fp1 = CertManager.get_cert_fingerprint(cert_pem)
        fp2 = CertManager.get_cert_fingerprint(cert_pem)
        assert fp1 == fp2

    def test_fingerprint_different_certs(self, ca):
        cert1_pem, _ = ca.sign_agent_cert("uuid-1")
        cert2_pem, _ = ca.sign_agent_cert("uuid-2")
        assert CertManager.get_cert_fingerprint(cert1_pem) != CertManager.get_cert_fingerprint(cert2_pem)

    def test_serial_format(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-ser")
        serial = CertManager.get_cert_serial(cert_pem)
        assert isinstance(serial, str)
        assert len(serial) > 0
        int(serial, 16)  # Must be valid hex

    def test_serial_matches_cert(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-match")
        cert = x509.load_pem_x509_certificate(cert_pem)
        assert CertManager.get_cert_serial(cert_pem) == format(cert.serial_number, "x")


# ────────────────────────────────────────────────────────────────────────
# CRL (Certificate Revocation List)
# ────────────────────────────────────────────────────────────────────────


class TestCRL:
    def test_generate_crl_creates_file(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        cert_pem, _ = ca.sign_agent_cert("uuid-revoke-1")
        serial = int(CertManager.get_cert_serial(cert_pem), 16)
        now = datetime.now(timezone.utc)

        ca.generate_crl([(serial, now)], crl_path)
        assert crl_path.exists()

    def test_generate_crl_content_valid(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        cert_pem, _ = ca.sign_agent_cert("uuid-crl-valid")
        serial = int(CertManager.get_cert_serial(cert_pem), 16)
        now = datetime.now(timezone.utc)

        crl_pem = ca.generate_crl([(serial, now)], crl_path)
        crl = x509.load_pem_x509_crl(crl_pem)
        assert len(list(crl)) == 1
        revoked = crl.get_revoked_certificate_by_serial_number(serial)
        assert revoked is not None

    def test_generate_empty_crl(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        crl_pem = ca.generate_crl([], crl_path)
        crl = x509.load_pem_x509_crl(crl_pem)
        assert len(list(crl)) == 0

    def test_crl_signed_by_ca(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        crl_pem = ca.generate_crl([], crl_path)
        crl = x509.load_pem_x509_crl(crl_pem)
        ca_cert = x509.load_pem_x509_certificate(ca.ca_cert_path.read_bytes())
        assert crl.issuer == ca_cert.subject

    def test_crl_next_update_30_days(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        crl_pem = ca.generate_crl([], crl_path)
        crl = x509.load_pem_x509_crl(crl_pem)
        delta = crl.next_update_utc - crl.last_update_utc
        assert 29 <= delta.days <= 31

    def test_load_crl_nonexistent(self, tmp_path):
        assert CertManager.load_crl(tmp_path / "nope.pem") is None

    def test_load_crl_existing(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        ca.generate_crl([], crl_path)
        crl = CertManager.load_crl(crl_path)
        assert crl is not None

    def test_is_cert_revoked_true(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        cert_pem, _ = ca.sign_agent_cert("uuid-rev-check")
        serial_hex = CertManager.get_cert_serial(cert_pem)
        serial_int = int(serial_hex, 16)
        now = datetime.now(timezone.utc)

        ca.generate_crl([(serial_int, now)], crl_path)
        assert CertManager.is_cert_revoked(serial_hex, crl_path) is True

    def test_is_cert_revoked_false(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        cert_pem, _ = ca.sign_agent_cert("uuid-not-rev")
        serial_hex = CertManager.get_cert_serial(cert_pem)

        # CRL vide — aucun cert revoque
        ca.generate_crl([], crl_path)
        assert CertManager.is_cert_revoked(serial_hex, crl_path) is False

    def test_is_cert_revoked_no_crl(self, tmp_path):
        assert CertManager.is_cert_revoked("abc123", tmp_path / "missing.pem") is False

    def test_multiple_revoked_certs(self, ca, tmp_path):
        crl_path = tmp_path / "crl.pem"
        now = datetime.now(timezone.utc)
        serials = []
        for i in range(3):
            cert_pem, _ = ca.sign_agent_cert(f"uuid-multi-{i}")
            serial_hex = CertManager.get_cert_serial(cert_pem)
            serials.append((int(serial_hex, 16), now))

        ca.generate_crl(serials, crl_path)
        crl = CertManager.load_crl(crl_path)
        assert len(list(crl)) == 3


# ────────────────────────────────────────────────────────────────────────
# get_cert_expiry
# ────────────────────────────────────────────────────────────────────────


class TestCertExpiry:
    def test_expiry_returns_datetime(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-expiry")
        expiry = CertManager.get_cert_expiry(cert_pem)
        assert isinstance(expiry, datetime)

    def test_expiry_is_about_1_year(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-expiry-yr")
        expiry = CertManager.get_cert_expiry(cert_pem)
        delta = expiry - datetime.now(timezone.utc)
        assert 363 <= delta.days <= 366

    def test_expiry_matches_cert(self, ca):
        cert_pem, _ = ca.sign_agent_cert("uuid-expiry-match")
        cert = x509.load_pem_x509_certificate(cert_pem)
        assert CertManager.get_cert_expiry(cert_pem) == cert.not_valid_after_utc
