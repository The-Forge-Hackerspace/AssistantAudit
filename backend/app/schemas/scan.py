"""
Schémas Pydantic pour les scans réseau (Nmap) et les outils intégrés.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Scan Réseau ──────────────────────────────────────────────

class ScanCreate(BaseModel):
    """Paramètres pour lancer un scan Nmap."""
    nom: Optional[str] = Field(None, description="Nom du scan (ex: VLAN 10 - MGT)")
    site_id: int
    target: str = Field(..., description="IP, CIDR ou hostname à scanner")
    scan_type: str = Field("discovery", description="discovery | port_scan | full | custom")
    custom_args: Optional[str] = Field(None, description="Arguments Nmap personnalisés (mode custom)")
    notes: Optional[str] = None


class ScanPortRead(BaseModel):
    id: int
    port_number: int
    protocol: Optional[str] = None
    state: Optional[str] = None
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    extra_info: Optional[str] = None

    model_config = {"from_attributes": True}


class ScanHostRead(BaseModel):
    id: int
    scan_id: int
    ip_address: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    os_guess: Optional[str] = None
    status: Optional[str] = None
    ports_open_count: int = 0
    decision: Optional[str] = None  # pending | kept | ignored
    chosen_type: Optional[str] = None
    equipement_id: Optional[int] = None
    date_decouverte: datetime
    ports: list[ScanPortRead] = []

    model_config = {"from_attributes": True}


class ScanRead(BaseModel):
    id: int
    nom: Optional[str] = None
    site_id: int
    date_scan: datetime
    type_scan: Optional[str] = None
    nmap_command: Optional[str] = None
    nombre_hosts_trouves: int = 0
    nombre_ports_ouverts: int = 0
    duree_scan_secondes: Optional[int] = None
    notes: Optional[str] = None
    hosts: list[ScanHostRead] = []

    model_config = {"from_attributes": True}


class ScanSummary(BaseModel):
    """Résumé d'un scan sans les hosts détaillés."""
    id: int
    nom: Optional[str] = None
    site_id: int
    date_scan: datetime
    type_scan: Optional[str] = None
    nmap_command: Optional[str] = None
    nombre_hosts_trouves: int = 0
    nombre_ports_ouverts: int = 0
    duree_scan_secondes: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ScanHostDecision(BaseModel):
    """Décision sur un host découvert : garder, ignorer, lier à un équipement."""
    decision: str = Field(..., description="kept | ignored")
    chosen_type: Optional[str] = Field(None, description="serveur | reseau | firewall | equipement")
    hostname: Optional[str] = None
    create_equipement: bool = Field(False, description="Créer automatiquement un équipement")


# ─── Config Parser ────────────────────────────────────────────

class InterfaceInfo(BaseModel):
    """Interface réseau découverte dans une config."""
    name: str
    ip_address: Optional[str] = None
    netmask: Optional[str] = None
    vlan: Optional[int] = None
    status: str = "up"
    allowed_access: list[str] = []
    description: Optional[str] = None


class FirewallRuleInfo(BaseModel):
    """Règle de pare-feu extraite d'une config."""
    rule_id: str
    name: Optional[str] = None
    source_interface: Optional[str] = None
    dest_interface: Optional[str] = None
    source_address: Optional[str] = None
    dest_address: Optional[str] = None
    service: Optional[str] = None
    action: str = "deny"
    schedule: Optional[str] = None
    enabled: bool = True
    log_traffic: bool = False


class SecurityFinding(BaseModel):
    """Constat de sécurité trouvé par un analyseur."""
    severity: str = "medium"  # critical | high | medium | low | info
    category: str = ""
    title: str
    description: str
    remediation: Optional[str] = None
    reference: Optional[str] = None


class ConfigAnalysisResult(BaseModel):
    """Résultat complet de l'analyse d'une configuration."""
    vendor: str
    device_type: str = "firewall"
    hostname: Optional[str] = None
    firmware_version: Optional[str] = None
    serial_number: Optional[str] = None
    interfaces: list[InterfaceInfo] = []
    firewall_rules: list[FirewallRuleInfo] = []
    findings: list[SecurityFinding] = []
    summary: dict = {}


class ConfigUploadResponse(BaseModel):
    """Réponse après upload et analyse d'une config."""
    filename: str
    vendor: str
    equipement_id: Optional[int] = None
    analysis: ConfigAnalysisResult


# ─── SSL/TLS Checker ─────────────────────────────────────────

class SSLCheckRequest(BaseModel):
    """Paramètres pour vérifier SSL/TLS d'un hôte."""
    host: str
    port: int = Field(443, ge=1, le=65535)
    timeout: Optional[int] = Field(10, ge=1, le=60)


class CertificateInfo(BaseModel):
    """Informations sur le certificat SSL."""
    subject: str
    issuer: str
    organization: str = ""
    not_before: Optional[str] = None
    not_after: Optional[str] = None
    days_remaining: int = -1
    is_expired: bool = False
    self_signed: bool = False
    is_trusted: bool = False
    san: list[str] = []
    serial_number: str = ""
    version: int = 0
    signature_algorithm: str = ""
    error: Optional[str] = None


class ProtocolInfo(BaseModel):
    """Support d'un protocole SSL/TLS."""
    name: str  # TLSv1.0, TLSv1.1, TLSv1.2, TLSv1.3
    supported: bool
    is_secure: bool


class SSLCheckResult(BaseModel):
    """Résultat complet d'une vérification SSL/TLS."""
    host: str
    port: int
    certificate: Optional[CertificateInfo] = None
    protocols: list[ProtocolInfo] = []
    findings: list[SecurityFinding] = []
