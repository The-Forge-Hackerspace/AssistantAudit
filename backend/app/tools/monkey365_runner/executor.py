"""
Monkey365 Executor — Bridge Python → PowerShell pour l'audit M365/Azure.
"""
import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Sanitisation des paramètres PowerShell ───────────────────────────────────

# UUID / GUID pattern (tenant_id, client_id)
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
# Client secret : alphanumériques, tirets, tildes, points, underscores (Azure AD format)
_SECRET_PATTERN = re.compile(r"^[a-zA-Z0-9_.~\-]{1,256}$")
# Certificate thumbprint : hexadécimal 40 chars (SHA-1)
_THUMBPRINT_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
# Nom d'analyse / ruleset : alphanum, underscores, tirets
_SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _escape_ps_string(value: str) -> str:
    """
    Échappe une valeur pour insertion sûre dans une string PowerShell
    entourée de guillemets simples.

    En PowerShell, le seul échappement dans une single-quoted string est
    de doubler les apostrophes : ' → ''
    """
    return value.replace("'", "''")


def _validate_uuid(value: str, field_name: str) -> str:
    """Valide qu'une valeur est un UUID valide."""
    if not _UUID_PATTERN.match(value):
        raise ValueError(
            f"{field_name} invalide : format UUID attendu (ex: 12345678-1234-1234-1234-123456789abc)"
        )
    return value


def _validate_secret(value: str) -> str:
    """Valide un client secret (pas d'injection possible)."""
    if not _SECRET_PATTERN.match(value):
        raise ValueError(
            "Client secret contient des caractères non autorisés. "
            "Seuls les caractères alphanumériques, points, tirets, tildes "
            "et underscores sont acceptés."
        )
    return value


def _validate_thumbprint(value: str) -> str:
    """Valide un thumbprint de certificat."""
    if not _THUMBPRINT_PATTERN.match(value):
        raise ValueError(
            "Thumbprint de certificat invalide : 40 caractères hexadécimaux attendus."
        )
    return value


def _validate_safe_name(value: str, field_name: str) -> str:
    """Valide un nom (analyse, ruleset) pour éviter l'injection."""
    if not _SAFE_NAME_PATTERN.match(value):
        raise ValueError(
            f"{field_name} invalide : seuls les caractères alphanumériques, "
            f"tirets et underscores sont autorisés."
        )
    return value


class M365Provider(str, Enum):
    MICROSOFT365 = "Microsoft365"
    AZURE = "Azure"
    ENTRA_ID = "EntraID"


class AuthMethod(str, Enum):
    INTERACTIVE = "interactive"
    CLIENT_CREDENTIALS = "client_credentials"
    CERTIFICATE = "certificate"


@dataclass
class Monkey365Config:
    provider: M365Provider = M365Provider.MICROSOFT365
    auth_method: AuthMethod = AuthMethod.CLIENT_CREDENTIALS
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    certificate_path: Optional[str] = None
    output_dir: str = "./monkey365_output"
    rulesets: list[str] = field(default_factory=lambda: ["cis_m365_benchmark"])
    plugins: list[str] = field(default_factory=list)


class Monkey365Executor:
    """Exécute Monkey365 via PowerShell et récupère les résultats JSON."""

    DEFAULT_ANALYSES = {
        M365Provider.MICROSOFT365: [
            "ExchangeOnline", "SharePointOnline",
            "MicrosoftTeams", "MicrosoftForms", "Purview",
        ],
        M365Provider.ENTRA_ID: [
            "EntraID", "EntraIDIdentityGovernance", "ConditionalAccess",
        ],
        M365Provider.AZURE: [
            "Compute", "Networking", "Storage",
            "KeyVault", "RBAC", "Monitor",
        ],
    }

    def __init__(self, config: Monkey365Config, monkey365_path: Optional[str] = None):
        self.config = config
        self.monkey365_path = self._resolve_path(monkey365_path)
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: Optional[str]) -> Path:
        """Localise Monkey365"""
        candidates = [
            Path(path) if path else None,
            Path("./integrations/monkey365/Invoke-Monkey365.ps1"),
        ]
        for p in candidates:
            if p and p.exists():
                return p
        raise FileNotFoundError(
            "Monkey365 non trouvé. Installez-le avec :\n"
            "  git submodule add https://github.com/silverhack/monkey365 integrations/monkey365\n"
            "  ou : Install-Module -Name monkey365 -Scope CurrentUser"
        )

    def _get_analyses(self) -> list[str]:
        if self.config.plugins:
            return self.config.plugins
        return self.DEFAULT_ANALYSES.get(self.config.provider, [])

    def build_script(self, scan_id: str) -> str:
        """
        Génère le script PowerShell pour lancer le scan.
        Tous les paramètres utilisateur sont validés ET échappés.
        """
        # ── Validation des paramètres sensibles ──────────────────────────
        _validate_uuid(self.config.tenant_id, "tenant_id")

        if self.config.auth_method == AuthMethod.CLIENT_CREDENTIALS:
            _validate_uuid(self.config.client_id, "client_id")
            _validate_secret(self.config.client_secret)
        elif self.config.auth_method == AuthMethod.CERTIFICATE:
            _validate_uuid(self.config.client_id, "client_id")
            if self.config.certificate_path:
                _validate_thumbprint(self.config.certificate_path)

        # Valider les noms d'analyses et rulesets
        for analysis in self._get_analyses():
            _validate_safe_name(analysis, "analysis")

        if self.config.rulesets:
            for ruleset in self.config.rulesets:
                _validate_safe_name(ruleset, "ruleset")

        # ── Construction du script avec échappement ──────────────────────
        output_path = self.output_dir / scan_id
        analyses = ", ".join(
            f"'{_escape_ps_string(a)}'" for a in self._get_analyses()
        )

        # Échapper toutes les valeurs interpolées
        safe_module_path = _escape_ps_string(str(self.monkey365_path.parent))
        safe_provider = _escape_ps_string(self.config.provider.value)
        safe_output = _escape_ps_string(str(output_path))
        safe_tenant = _escape_ps_string(self.config.tenant_id)

        script = f"""
Import-Module '{safe_module_path}' -Force

$params = @{{
    Instance   = '{safe_provider}'
    Analysis   = @({analyses})
    ExportTo   = @('JSON', 'HTML')
    OutDir     = '{safe_output}'
    TenantId   = '{safe_tenant}'
}}
"""
        if self.config.auth_method == AuthMethod.CLIENT_CREDENTIALS:
            safe_secret = _escape_ps_string(self.config.client_secret)
            safe_client_id = _escape_ps_string(self.config.client_id)
            script += f"""
$secret = ConvertTo-SecureString '{safe_secret}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential('{safe_client_id}', $secret)
$params['AppCredential'] = $cred
$params['ConfidentialApp'] = $true
"""
        elif self.config.auth_method == AuthMethod.CERTIFICATE:
            safe_client_id = _escape_ps_string(self.config.client_id)
            safe_cert = _escape_ps_string(self.config.certificate_path or "")
            script += f"""
$params['ClientId'] = '{safe_client_id}'
$params['CertificateThumbprint'] = '{safe_cert}'
"""

        if self.config.rulesets:
            ruleset_paths = ", ".join(
                f"'{_escape_ps_string(str(self.monkey365_path.parent / 'rulesets' / r))}.json'"
                for r in self.config.rulesets
            )
            script += f"\n$params['RuleSets'] = @({ruleset_paths})\n"

        script += "\nInvoke-Monkey365 @params\n"
        return script

    def run_scan(self, scan_id: str) -> dict:
        """Lance le scan Monkey365 (synchrone)"""
        script = self.build_script(scan_id)
        script_path = self.output_dir / f"{scan_id}_script.ps1"
        script_path.write_text(script, encoding="utf-8")

        try:
            process = subprocess.run(
                ["pwsh", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
                capture_output=True,
                text=True,
                timeout=3600,
            )
            if process.returncode != 0:
                return {"status": "error", "scan_id": scan_id, "error": process.stderr}

            results = self._parse_output(scan_id)
            return {"status": "success", "scan_id": scan_id, "results": results}

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "scan_id": scan_id, "error": "Timeout 1h dépassé"}
        except FileNotFoundError:
            return {"status": "error", "scan_id": scan_id, "error": "pwsh introuvable"}
        finally:
            if script_path.exists():
                script_path.unlink()

    def _parse_output(self, scan_id: str) -> list[dict]:
        """Parse les JSON de sortie Monkey365"""
        results = []
        output_path = self.output_dir / scan_id

        for json_file in output_path.rglob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    results.extend(data)
                elif isinstance(data, dict):
                    results.append(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        return results
