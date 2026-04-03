"""
Validateurs métier pour les schémas Pydantic.
Centralise les validations réutilisables pour IP, hostname, MAC, fichiers, etc.
"""

import re
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from typing import Annotated

from pydantic import BeforeValidator
from pydantic.functional_validators import PlainValidator


def validate_ip_address(ip: str) -> str:
    """Valide une adresse IPv4 ou IPv6."""
    ip = ip.strip()
    try:
        # Essayer IPv4
        IPv4Address(ip)
        return ip
    except AddressValueError:
        try:
            # Essayer IPv6
            IPv6Address(ip)
            return ip
        except AddressValueError:
            raise ValueError(f"Adresse IP invalide: {ip}")


def validate_hostname(hostname: str) -> str:
    """Valide un nom d'hôte FQDN."""
    hostname = hostname.strip()
    # RFC 1123 : lettres, chiffres, tirets, points (pas @ ou /)
    if not re.match(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.?$", hostname):
        raise ValueError(f"Nom d'hôte invalide: {hostname}. Utiliser alphanumeriques, tirets et points.")
    return hostname


def validate_mac_address(mac: str) -> str:
    """Valide une adresse MAC (format XX:XX:XX:XX:XX:XX ou XX-XX-XX-XX-XX-XX)."""
    mac = mac.strip().upper()
    if not re.match(r"^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$", mac):
        raise ValueError(f"Adresse MAC invalide: {mac}")
    return mac


def validate_port(port: int) -> int:
    """Valide un numero de port reseau."""
    if not (1 <= port <= 65535):
        raise ValueError(f"Port invalide: {port} (1-65535)")
    return port


def validate_vlan(vlan: int) -> int:
    """Valide un numero de VLAN."""
    if not (1 <= vlan <= 4094):
        raise ValueError(f"VLAN invalide: {vlan} (1-4094)")
    return vlan


def validate_filename(filename: str) -> str:
    """Valide un nom de fichier (pas de path traversal)."""
    filename = filename.strip()
    forbidden = ["../", "..", "<", ">", "|", "*", "?"]
    for char in forbidden:
        if char in filename:
            raise ValueError(f"Caractere interdit dans le nom: {char}")
    return filename


def validate_http_url(url: str) -> str:
    """Valide une URL HTTP/HTTPS."""
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValueError(f"URL invalide: {url}")
    return url


def validate_description(desc: str, max_length: int = 1000) -> str:
    """Valide une description (longueur max et pas de caracteres dangereux)."""
    desc = desc.strip()
    if len(desc) > max_length:
        raise ValueError(f"Description trop longue (max {max_length})")
    return desc


def validate_username(username: str) -> str:
    """Valide un nom d'utilisateur."""
    username = username.strip()
    if not re.match(r"^[a-zA-Z0-9._-]{3,32}$", username):
        raise ValueError("Username debe tener 3-32 caracteres alphanumericos")
    return username


# Types Pydantic annotes pour utilisation simple
IPAddress = Annotated[str, BeforeValidator(validate_ip_address)]
Hostname = Annotated[str, BeforeValidator(validate_hostname)]
MACAddress = Annotated[str, BeforeValidator(validate_mac_address)]
PortNumber = Annotated[int, PlainValidator(validate_port)]
VLANNumber = Annotated[int, PlainValidator(validate_vlan)]
Filename = Annotated[str, BeforeValidator(validate_filename)]
HTTPURL = Annotated[str, BeforeValidator(validate_http_url)]
Description = Annotated[str, BeforeValidator(validate_description)]
Username = Annotated[str, BeforeValidator(validate_username)]
