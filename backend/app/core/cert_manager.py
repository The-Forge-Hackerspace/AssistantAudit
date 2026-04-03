"""
Gestion des certificats pour l'infrastructure mTLS serveur <-> agent.
CA privee interne — ne PAS utiliser de CA publique pour les agents.

Usage :
    # Une seule fois, a l'installation du serveur :
    CertManager.generate_ca(ca_cert_path, ca_key_path)

    # Pour chaque nouvel agent :
    mgr = CertManager(ca_cert_path, ca_key_path)
    cert_pem, key_pem = mgr.sign_agent_cert(agent_uuid)
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import CertificateRevocationListBuilder, RevokedCertificateBuilder
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


class CertManager:
    def __init__(self, ca_cert_path: Path, ca_key_path: Path):
        self.ca_cert_path = Path(ca_cert_path)
        self.ca_key_path = Path(ca_key_path)

        if self.ca_key_path.exists():
            try:
                mode = self.ca_key_path.stat().st_mode & 0o777
                if mode != 0o600:
                    logger.warning(
                        "CA private key %s has insecure permissions %o, should be 600",
                        self.ca_key_path,
                        mode,
                    )
            except OSError:
                pass

    @staticmethod
    def generate_ca(
        ca_cert_path: Path,
        ca_key_path: Path,
        cn: str = "AssistantAudit Internal CA",
    ) -> None:
        """Genere la paire CA (une seule fois, a l'installation du serveur)."""
        ca_cert_path = Path(ca_cert_path)
        ca_key_path = Path(ca_key_path)

        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, cn),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AssistantAudit"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(
                x509.KeyUsage(
                    key_cert_sign=True,
                    crl_sign=True,
                    digital_signature=False,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )

        ca_cert_path.parent.mkdir(parents=True, exist_ok=True)
        ca_cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        ca_key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        try:
            os.chmod(ca_key_path, 0o600)
        except OSError:
            pass  # Windows

    def sign_agent_cert(self, agent_uuid: str) -> tuple[bytes, bytes]:
        """
        Genere et signe un certificat client pour un agent.

        Returns:
            (cert_pem, key_pem)
        """
        ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
        ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)

        agent_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, f"agent-{agent_uuid}"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AssistantAudit"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(agent_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True,
            )
            .add_extension(
                x509.SubjectAlternativeName([x509.UniformResourceIdentifier(f"urn:agent:{agent_uuid}")]),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = agent_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        return cert_pem, key_pem

    def generate_crl(
        self,
        revoked_serials: list[tuple[int, datetime]],
        crl_path: Path,
    ) -> bytes:
        """
        Genere une CRL (Certificate Revocation List) signee par la CA.
        revoked_serials: liste de (serial_number, revocation_date)
        Retourne le PEM de la CRL.
        """
        ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
        ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)

        now = datetime.now(timezone.utc)
        builder = CertificateRevocationListBuilder()
        builder = builder.issuer_name(ca_cert.subject)
        builder = builder.last_update(now)
        builder = builder.next_update(now + timedelta(days=30))

        for serial, revoked_at in revoked_serials:
            revoked_cert = RevokedCertificateBuilder().serial_number(serial).revocation_date(revoked_at).build()
            builder = builder.add_revoked_certificate(revoked_cert)

        crl = builder.sign(ca_key, hashes.SHA256())
        crl_pem = crl.public_bytes(serialization.Encoding.PEM)

        crl_path = Path(crl_path)
        crl_path.parent.mkdir(parents=True, exist_ok=True)
        crl_path.write_bytes(crl_pem)
        logger.info("CRL generated with %d revoked certificates at %s", len(revoked_serials), crl_path)
        return crl_pem

    @staticmethod
    def load_crl(crl_path: Path) -> x509.CertificateRevocationList | None:
        """Charge la CRL depuis le disque. Retourne None si absente."""
        crl_path = Path(crl_path)
        if not crl_path.exists():
            return None
        return x509.load_pem_x509_crl(crl_path.read_bytes())

    @staticmethod
    def is_cert_revoked(
        cert_serial_hex: str,
        crl_path: Path,
    ) -> bool:
        """
        Verifie si un certificat (par son serial hex) est dans la CRL.
        Retourne False si la CRL n'existe pas (pas encore de revocation).
        """
        crl = CertManager.load_crl(crl_path)
        if crl is None:
            return False
        serial = int(cert_serial_hex, 16)
        return crl.get_revoked_certificate_by_serial_number(serial) is not None

    @staticmethod
    def get_cert_expiry(cert_pem: bytes) -> datetime:
        """Retourne la date d'expiration du certificat."""
        cert = x509.load_pem_x509_certificate(cert_pem)
        return cert.not_valid_after_utc

    @staticmethod
    def get_cert_fingerprint(cert_pem: bytes) -> str:
        """Retourne le SHA-256 fingerprint du certificat en hex (64 chars)."""
        cert = x509.load_pem_x509_certificate(cert_pem)
        return cert.fingerprint(hashes.SHA256()).hex()

    @staticmethod
    def get_cert_serial(cert_pem: bytes) -> str:
        """Retourne le serial number du certificat en hex."""
        cert = x509.load_pem_x509_certificate(cert_pem)
        return format(cert.serial_number, "x")
