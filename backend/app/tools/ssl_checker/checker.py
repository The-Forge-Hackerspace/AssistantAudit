"""
SSL/TLS Checker — Vérification de certificats et protocoles.

Utilise uniquement la stdlib Python (ssl + socket).
Supporte SNI, vérification d'expiration, chaîne de confiance, protocoles supportés.
"""
import logging
import socket
import ssl
from datetime import datetime, timezone
from typing import Optional

from ...schemas.scan import (
    CertificateInfo,
    ProtocolInfo,
    SecurityFinding,
    SSLCheckResult,
)

logger = logging.getLogger(__name__)

# Protocoles à tester (du plus ancien au plus récent)
_PROTOCOL_MAP: list[tuple[str, int | None]] = []

# Build protocol list dynamically based on what's available in ssl module
for _name, _attr in [
    ("SSLv3", "PROTOCOL_SSLv3"),
    ("TLSv1.0", "PROTOCOL_TLSv1"),
    ("TLSv1.1", "PROTOCOL_TLSv1_1"),
    ("TLSv1.2", "PROTOCOL_TLSv1_2"),
]:
    val = getattr(ssl, _attr, None)
    if val is not None:
        _PROTOCOL_MAP.append((_name, val))

# TLSv1.3 is handled separately via TLS_CLIENT_METHOD
_PROTOCOL_MAP.append(("TLSv1.3", None))  # sentinel


def check_ssl(host: str, port: int = 443, timeout: int = 10) -> SSLCheckResult:
    """Effectue un audit SSL/TLS complet sur host:port."""
    cert_info = _get_certificate(host, port, timeout)
    protocols = _check_protocols(host, port, timeout)
    findings = _analyze(cert_info, protocols)

    return SSLCheckResult(
        host=host,
        port=port,
        certificate=cert_info,
        protocols=protocols,
        findings=findings,
    )


def _get_certificate(host: str, port: int, timeout: int) -> CertificateInfo:
    """Récupère les informations du certificat via TLS."""
    context = ssl.create_default_context()
    # We still want to retrieve the cert even if it's self-signed
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert_bin = ssock.getpeercert(binary_form=True)
                cert_dict = ssl.DER_cert_to_PEM_cert(cert_bin)

                # Re-connect with verification to get parsed cert
                ctx2 = ssl.create_default_context()
                ctx2.check_hostname = False
                ctx2.verify_mode = ssl.CERT_NONE

        # Get parsed certificate info
        with socket.create_connection((host, port), timeout=timeout) as sock2:
            ctx3 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx3.check_hostname = False
            ctx3.verify_mode = ssl.CERT_NONE
            with ctx3.wrap_socket(sock2, server_hostname=host) as ssock2:
                cert = ssock2.getpeercert()
                if not cert:
                    # getpeercert() returns {} when verify_mode=CERT_NONE on some versions
                    # Fallback: use binary cert for basic info
                    return _cert_from_binary(host, port, timeout)

                subject = dict(x[0] for x in cert.get("subject", ()))
                issuer = dict(x[0] for x in cert.get("issuer", ()))
                san = [entry[1] for entry in cert.get("subjectAltName", ())]

                not_before = _parse_ssl_date(cert.get("notBefore", ""))
                not_after = _parse_ssl_date(cert.get("notAfter", ""))

                now = datetime.now(timezone.utc)
                days_remaining = (not_after - now).days if not_after else -1
                is_expired = days_remaining < 0

                # Check if self-signed
                self_signed = subject == issuer

                # Try to validate trust chain
                is_trusted = _check_trusted(host, port, timeout)

                return CertificateInfo(
                    subject=subject.get("commonName", ""),
                    issuer=issuer.get("commonName", ""),
                    organization=issuer.get("organizationName", ""),
                    not_before=not_before.isoformat() if not_before else None,
                    not_after=not_after.isoformat() if not_after else None,
                    days_remaining=days_remaining,
                    is_expired=is_expired,
                    self_signed=self_signed,
                    is_trusted=is_trusted,
                    san=san,
                    serial_number=cert.get("serialNumber", ""),
                    version=cert.get("version", 0),
                    signature_algorithm="",
                )

    except Exception as exc:
        logger.warning("Impossible de récupérer le certificat de %s:%d : %s", host, port, exc)
        return CertificateInfo(
            subject="",
            issuer="",
            organization="",
            not_before=None,
            not_after=None,
            days_remaining=-1,
            is_expired=True,
            self_signed=False,
            is_trusted=False,
            san=[],
            serial_number="",
            version=0,
            signature_algorithm="",
            error=str(exc),
        )


def _cert_from_binary(host: str, port: int, timeout: int) -> CertificateInfo:
    """Fallback: extract minimal info when getpeercert() returns empty."""
    return CertificateInfo(
        subject=host,
        issuer="unknown",
        organization="",
        not_before=None,
        not_after=None,
        days_remaining=-1,
        is_expired=False,
        self_signed=False,
        is_trusted=_check_trusted(host, port, timeout),
        san=[],
        serial_number="",
        version=0,
        signature_algorithm="",
        error="Certificate details unavailable (binary only)",
    )


def _check_trusted(host: str, port: int, timeout: int) -> bool:
    """Vérifie si le certificat est signé par une CA de confiance."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                return True
    except ssl.SSLCertVerificationError:
        return False
    except Exception:
        return False


def _check_protocols(host: str, port: int, timeout: int) -> list[ProtocolInfo]:
    """Teste chaque version de TLS/SSL pour voir lesquelles sont supportées."""
    results: list[ProtocolInfo] = []

    for proto_name, proto_const in _PROTOCOL_MAP:
        if proto_name == "TLSv1.3":
            supported = _check_tls13(host, port, timeout)
            results.append(ProtocolInfo(
                name=proto_name,
                supported=supported,
                is_secure=True,
            ))
            continue

        try:
            ctx = ssl.SSLContext(proto_const)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            # Suppress deprecated protocol warnings
            ctx.options &= ~ssl.OP_NO_SSLv3  # type: ignore[attr-defined]

            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host):
                    supported = True
        except (ssl.SSLError, ConnectionRefusedError, OSError):
            supported = False

        is_secure = proto_name in ("TLSv1.2", "TLSv1.3")

        results.append(ProtocolInfo(
            name=proto_name,
            supported=supported,
            is_secure=is_secure,
        ))

    return results


def _check_tls13(host: str, port: int, timeout: int) -> bool:
    """Check TLS 1.3 support specifically."""
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3

        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                return True
    except (ssl.SSLError, ConnectionRefusedError, OSError, AttributeError):
        return False


def _analyze(cert: CertificateInfo, protocols: list[ProtocolInfo]) -> list[SecurityFinding]:
    """Génère des constats de sécurité à partir des résultats."""
    findings: list[SecurityFinding] = []

    # ── Certificat ──
    if cert.error:
        findings.append(SecurityFinding(
            severity="high",
            category="Certificat",
            title="Impossible de vérifier le certificat",
            description=f"Erreur lors de la récupération : {cert.error}",
            remediation="Vérifier que le service TLS est correctement configuré.",
        ))
    else:
        if cert.is_expired:
            findings.append(SecurityFinding(
                severity="critical",
                category="Certificat",
                title="Certificat expiré",
                description=(
                    f"Le certificat a expiré (expiration : {cert.not_after}). "
                    "Un certificat expiré provoque des erreurs de connexion et compromet la confiance."
                ),
                remediation="Renouveler le certificat immédiatement.",
            ))
        elif cert.days_remaining is not None and 0 < cert.days_remaining <= 30:
            findings.append(SecurityFinding(
                severity="high",
                category="Certificat",
                title=f"Certificat expire dans {cert.days_remaining} jours",
                description=(
                    f"Le certificat expirera le {cert.not_after}. "
                    "Un renouvellement urgent est nécessaire."
                ),
                remediation="Planifier le renouvellement du certificat.",
            ))
        elif cert.days_remaining is not None and 0 < cert.days_remaining <= 90:
            findings.append(SecurityFinding(
                severity="medium",
                category="Certificat",
                title=f"Certificat expire dans {cert.days_remaining} jours",
                description=f"Expiration prévue le {cert.not_after}.",
                remediation="Prévoir le renouvellement du certificat.",
            ))

        if cert.self_signed:
            findings.append(SecurityFinding(
                severity="high",
                category="Certificat",
                title="Certificat auto-signé",
                description=(
                    "Le certificat est auto-signé. Il ne sera pas reconnu par les navigateurs "
                    "et ne fournit aucune assurance sur l'identité du serveur."
                ),
                remediation="Obtenir un certificat auprès d'une autorité de certification reconnue.",
            ))

        if not cert.is_trusted and not cert.self_signed:
            findings.append(SecurityFinding(
                severity="high",
                category="Certificat",
                title="Certificat non approuvé",
                description=(
                    "Le certificat n'est pas signé par une autorité de certification de confiance. "
                    "La chaîne de confiance est rompue."
                ),
                remediation="Vérifier la chaîne de certificats et installer les certificats intermédiaires manquants.",
            ))

    # ── Protocoles ──
    deprecated_supported = []
    for proto in protocols:
        if proto.supported and not proto.is_secure:
            deprecated_supported.append(proto.name)

    if deprecated_supported:
        findings.append(SecurityFinding(
            severity="high" if "SSLv3" in deprecated_supported else "medium",
            category="Protocoles",
            title=f"Protocole(s) obsolète(s) supporté(s) : {', '.join(deprecated_supported)}",
            description=(
                f"Le serveur supporte les protocoles obsolètes : {', '.join(deprecated_supported)}. "
                "Ces protocoles contiennent des vulnérabilités connues (POODLE, BEAST, etc.)."
            ),
            remediation="Désactiver SSLv3, TLSv1.0, TLSv1.1. N'autoriser que TLSv1.2 et TLSv1.3.",
        ))

    tls13 = next((p for p in protocols if p.name == "TLSv1.3"), None)
    if tls13 and not tls13.supported:
        findings.append(SecurityFinding(
            severity="low",
            category="Protocoles",
            title="TLS 1.3 non supporté",
            description="Le serveur ne supporte pas TLS 1.3, le protocole le plus récent et le plus sûr.",
            remediation="Activer TLS 1.3 pour bénéficier des dernières améliorations de sécurité.",
        ))

    secure_protocols = [p for p in protocols if p.supported and p.is_secure]
    if not secure_protocols:
        findings.append(SecurityFinding(
            severity="critical",
            category="Protocoles",
            title="Aucun protocole sécurisé supporté",
            description="Le serveur ne supporte ni TLS 1.2 ni TLS 1.3.",
            remediation="Mettre à jour la configuration TLS pour supporter au minimum TLS 1.2.",
        ))

    return findings


def _parse_ssl_date(date_str: str) -> Optional[datetime]:
    """Parse ssl module date format: 'Jul 12 00:00:00 2024 GMT'."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
