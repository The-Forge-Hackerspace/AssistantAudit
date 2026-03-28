"""
Schémas Pydantic pour les scans réseau (Nmap) et les outils intégrés.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from ..models.equipement import EQUIPEMENT_TYPE_VALUES


EQUIPEMENT_TYPE_PATTERN = "^(" + "|".join(EQUIPEMENT_TYPE_VALUES) + ")$"


# ─── Scan Réseau ──────────────────────────────────────────────

class ScanCreate(BaseModel):
    """Paramètres pour lancer un scan Nmap."""
    nom: Optional[str] = Field(None, description="Nom du scan (ex: VLAN 10 - MGT)")
    site_id: int
    target: str = Field(
        ...,
        description="IP, CIDR ou hostname à scanner",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/\-]{0,254}$",
        examples=["192.168.1.0/24", "10.0.0.1", "server.local"],
    )
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
    statut: str = "running"
    error_message: Optional[str] = None
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
    statut: str = "running"
    error_message: Optional[str] = None
    nombre_hosts_trouves: int = 0
    nombre_ports_ouverts: int = 0
    duree_scan_secondes: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ScanHostDecision(BaseModel):
    """Décision sur un host découvert : garder, ignorer, lier à un équipement."""
    decision: str = Field(..., description="kept | ignored")
    chosen_type: Optional[str] = Field(
        None,
        pattern=EQUIPEMENT_TYPE_PATTERN,
        description="Type d'équipement choisi",
    )
    hostname: Optional[str] = None
    create_equipement: bool = Field(False, description="Créer automatiquement un équipement")


class ScanHostLink(BaseModel):
    equipement_id: Optional[int] = None
    source_interface: Optional[str] = Field(default=None, max_length=100)
    target_interface: Optional[str] = Field(default=None, max_length=100)
    link_type: str = Field(default="ethernet", pattern=r"^(ethernet|fiber|wifi|vpn|wan|serial|other)$")
    bandwidth: Optional[str] = Field(default=None, max_length=50)
    vlan: Optional[str] = Field(default=None, max_length=100)
    network_segment: Optional[str] = Field(default=None, max_length=100)


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
    config_analysis_id: Optional[int] = None
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


# ─── Config Analysis (liée à un équipement) ──────────────────

class ConfigAnalysisRead(BaseModel):
    """Analyse de configuration persistée et liée à un équipement."""
    id: int
    equipement_id: int
    filename: str
    vendor: str
    device_type: str = "firewall"
    hostname: Optional[str] = None
    firmware_version: Optional[str] = None
    serial_number: Optional[str] = None
    interfaces: list[InterfaceInfo] = []
    firewall_rules: list[FirewallRuleInfo] = []
    findings: list[SecurityFinding] = []
    summary: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigAnalysisSummary(BaseModel):
    """Résumé d'une analyse de configuration."""
    id: int
    equipement_id: int
    filename: str
    vendor: str
    hostname: Optional[str] = None
    firmware_version: Optional[str] = None
    findings_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PrefillResult(BaseModel):
    """Résultat du pré-remplissage d'audit depuis une analyse de config."""
    controls_prefilled: int
    controls_compliant: int
    controls_non_compliant: int
    controls_partial: int
    details: list[dict] = []


# ─── Collecte SSH / WinRM ─────────────────────────────────────

class CollectCreate(BaseModel):
    """Paramètres pour lancer une collecte SSH ou WinRM."""
    equipement_id: int
    method: str = Field(..., description="ssh ou winrm")
    target_host: str = Field(..., description="IP ou hostname du serveur")
    target_port: int = Field(22, description="Port SSH (22) ou WinRM (5985/5986)")
    username: str = Field(..., description="Utilisateur de connexion")
    password: Optional[str] = Field(None, description="Mot de passe")
    private_key: Optional[str] = Field(None, description="Clé privée SSH (PEM)")
    passphrase: Optional[str] = Field(None, description="Passphrase de la clé privée")
    use_ssl: bool = Field(False, description="WinRM: utiliser HTTPS (port 5986)")
    transport: str = Field("ntlm", description="WinRM: méthode d'auth (ntlm, kerberos, basic)")
    device_profile: str = Field("linux_server", description="Profil collecte SSH: linux_server, opnsense, stormshield, fortigate")


class CollectResultSummary(BaseModel):
    """Résumé d'une collecte pour la liste."""
    id: int
    equipement_id: int
    method: str
    status: str
    target_host: str
    target_port: int
    username: str
    device_profile: Optional[str] = "linux_server"
    hostname_collected: Optional[str] = None
    summary: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


class CollectResultRead(BaseModel):
    """Détail complet d'une collecte."""
    id: int
    equipement_id: int
    method: str
    status: str
    target_host: str
    target_port: int
    username: str
    device_profile: Optional[str] = "linux_server"
    hostname_collected: Optional[str] = None
    error_message: Optional[str] = None
    os_info: Optional[dict] = None
    network: Optional[dict] = None
    users: Optional[dict] = None
    services: Optional[dict] = None
    security: Optional[dict] = None
    storage: Optional[dict] = None
    updates: Optional[dict] = None
    findings: Optional[list] = None
    summary: Optional[dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


# ─── Audit Active Directory (LDAP) ────────────────────────────

class ADAuditCreate(BaseModel):
    """Paramètres pour lancer un audit AD."""
    equipement_id: Optional[int] = Field(None, description="Équipement (DC) associé")
    target_host: str = Field(..., description="IP ou hostname du contrôleur de domaine")
    target_port: int = Field(389, description="Port LDAP (389) ou LDAPS (636)")
    use_ssl: bool = Field(False, description="Utiliser LDAPS (SSL)")
    username: str = Field(..., description="Utilisateur pour la connexion LDAP")
    password: str = Field(..., description="Mot de passe")
    domain: str = Field(..., description="Nom du domaine AD (ex: corp.local)")
    auth_method: str = Field("ntlm", description="Méthode d'auth : ntlm ou simple")


class ADAuditFindingRead(BaseModel):
    """Un constat d'audit AD."""
    control_ref: str
    title: str
    description: str = ""
    severity: str
    category: str
    status: str
    evidence: str = ""
    remediation: str = ""
    details: dict = {}


class ADAuditResultSummary(BaseModel):
    """Résumé d'un audit AD pour la liste."""
    id: int
    equipement_id: Optional[int] = None
    status: str
    target_host: str
    target_port: int
    username: str
    domain: str
    domain_name: Optional[str] = None
    domain_functional_level: Optional[str] = None
    total_users: Optional[int] = None
    summary: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


class ADAuditResultRead(BaseModel):
    """Détail complet d'un audit AD."""
    id: int
    equipement_id: Optional[int] = None
    status: str
    target_host: str
    target_port: int
    username: str
    domain: str
    domain_name: Optional[str] = None
    domain_functional_level: Optional[str] = None
    forest_functional_level: Optional[str] = None
    total_users: Optional[int] = None
    enabled_users: Optional[int] = None
    disabled_users: Optional[int] = None
    dc_list: Optional[list] = None
    domain_admins: Optional[list] = None
    enterprise_admins: Optional[list] = None
    schema_admins: Optional[list] = None
    inactive_users: Optional[list] = None
    never_expire_password: Optional[list] = None
    never_logged_in: Optional[list] = None
    admin_account_status: Optional[dict] = None
    password_policy: Optional[dict] = None
    fine_grained_policies: Optional[list] = None
    gpo_list: Optional[list] = None
    laps_deployed: Optional[bool] = None
    findings: Optional[list] = None
    summary: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


# ─── Monkey365 Audit ─────────────────────────────────────────

class Monkey365ExportFormat(str, Enum):
    JSON = "JSON"
    HTML = "HTML"
    CSV = "CSV"


class Monkey365ConfigSchema(BaseModel):
    spo_sites: list[str] = Field(default_factory=list, description="SharePoint sites to scan (e.g., https://domain.sharepoint.com)")
    export_to: list[Monkey365ExportFormat] = Field(default_factory=lambda: [Monkey365ExportFormat.JSON, Monkey365ExportFormat.HTML], description="Formats d'export : JSON, HTML, CSV")
    device_code: bool = Field(default=False, description="Utiliser Device Code Flow au lieu de l'auth interactive")

    @field_validator("export_to", mode="after")
    @classmethod
    def ensure_json_included(cls, v: list[Monkey365ExportFormat]) -> list[Monkey365ExportFormat]:
        if Monkey365ExportFormat.JSON not in v:
            return [Monkey365ExportFormat.JSON] + v
        return v


class Monkey365ScanCreate(BaseModel):
    """Paramètres pour lancer un audit Monkey365."""
    entreprise_id: int = Field(..., description="ID de l'entreprise")
    config: Monkey365ConfigSchema = Field(..., description="Configuration Monkey365")


class Monkey365ScanResultSummary(BaseModel):
    """Résumé d'un audit Monkey365 pour la liste."""
    id: int
    entreprise_id: int
    status: str
    scan_id: str
    entreprise_slug: Optional[str] = None
    findings_count: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


class Monkey365ScanResultRead(BaseModel):
    """Détail complet d'un audit Monkey365."""
    id: int
    entreprise_id: int
    status: str
    scan_id: str
    config_snapshot: Optional[dict] = None
    output_path: Optional[str] = None
    entreprise_slug: Optional[str] = None
    findings_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


class Monkey365ScanLogs(BaseModel):
    """Logs PowerShell d'un scan Monkey365 (lecture en direct du fichier log)."""
    lines: list[str]
    total_lines: int


class Monkey365ImportRequest(BaseModel):
    """Paramètres pour importer un scan Monkey365 dans un audit existant."""
    audit_id: int = Field(..., description="ID de l'audit cible")


class Monkey365ImportResult(BaseModel):
    """Résultat de l'import d'un scan Monkey365 dans un audit."""
    campaign_id: int
    assessment_id: int
    controls_mapped: int
    controls_total: int


# ─── Monkey365 Streaming (Device Code Flow) ─────────────────

class Monkey365AuthMethod(str, Enum):
    DEVICE_CODE = "device_code"
    CERTIFICATE = "certificate"
    CLIENT_SECRET = "client_secret"


class Monkey365StreamingScanCreate(BaseModel):
    """Parametres pour lancer un scan Monkey365 streaming avec Device Code Flow."""
    entreprise_id: int = Field(..., description="ID de l'entreprise")
    tenant_id: str = Field(..., min_length=1, description="Azure AD tenant ID")
    auth_method: Monkey365AuthMethod = Field(
        default=Monkey365AuthMethod.DEVICE_CODE,
        description="Methode d'authentification",
    )
    subscriptions: list[str] = Field(default_factory=list, description="Azure subscriptions a auditer")
    ruleset: str = Field(default="cis", description="Ruleset (cis, etc.)")
    config: Monkey365ConfigSchema = Field(
        default_factory=Monkey365ConfigSchema,
        description="Configuration Monkey365 (spo_sites, export_to)",
    )


class Monkey365StreamingScanResponse(BaseModel):
    """Reponse immediate au lancement d'un scan streaming."""
    id: int
    scan_id: str
    status: str
    auth_method: Optional[str] = None
    message: str = "Scan lance. Ecoutez les evenements WebSocket pour le device code."

    model_config = {"from_attributes": True}
