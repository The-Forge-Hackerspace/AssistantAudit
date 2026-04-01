"""
Tests unitaires pour core/cert_manager.py
- Generation CA, signature certificats agent, fingerprint, serial, chain of trust.
Utilise tmp_path pour tous les fichiers — ne touche pas aux vrais certs/.
"""
from pathlib import Path

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
