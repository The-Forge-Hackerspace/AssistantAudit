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
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


class CertManager:
    def __init__(self, ca_cert_path: Path, ca_key_path: Path):
        self.ca_cert_path = Path(ca_cert_path)
        self.ca_key_path = Path(ca_key_path)

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

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AssistantAudit"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=0), critical=True
            )
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

    def sign_agent_cert(self, agent_uuid: str) -> tuple[bytes, bytes]:
        """
        Genere et signe un certificat client pour un agent.

        Returns:
            (cert_pem, key_pem)
        """
        ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
        ca_key = serialization.load_pem_private_key(
            self.ca_key_path.read_bytes(), password=None
        )

        agent_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"agent-{agent_uuid}"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AssistantAudit"),
        ])

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
                x509.SubjectAlternativeName([
                    x509.UniformResourceIdentifier(f"urn:agent:{agent_uuid}")
                ]),
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
