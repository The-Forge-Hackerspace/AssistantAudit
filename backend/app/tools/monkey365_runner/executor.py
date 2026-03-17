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
from typing import ClassVar, cast

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
_COLLECT_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")
_SCAN_SITE_PATTERN = re.compile(r"^https://[a-zA-Z0-9._/-]+$")

_ALLOWED_PROMPT_BEHAVIORS = {"Auto", "SelectAccount", "Always", "Never"}
_ALLOWED_EXPORT_FORMATS = {"JSON", "HTML", "CSV", "CLIXML"}


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
            "Client secret contient des caractères non autorisés. Seuls les caractères "
            + "alphanumériques, points, tirets, tildes et underscores sont acceptés."
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
            f"{field_name} invalide : seuls les caractères alphanumériques, tirets "
            + "et underscores sont autorisés."
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
    provider: M365Provider | str = M365Provider.MICROSOFT365
    auth_method: AuthMethod | str = AuthMethod.CLIENT_CREDENTIALS
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    certificate_path: str | None = None
    output_dir: str = "./monkey365_output"
    rulesets: list[str] = field(default_factory=lambda: ["cis_m365_benchmark"])
    plugins: list[str] = field(default_factory=list)
    collect: list[str] = field(default_factory=list)
    prompt_behavior: str = "Auto"
    include_entra_id: bool = True
    export_to: list[str] = field(default_factory=lambda: ["JSON", "HTML"])
    scan_sites: list[str] = field(default_factory=list)
    force_msal_desktop: bool = False
    verbose: bool = False

    def validate(self) -> None:
        for item in self.collect:
            if not _COLLECT_PATTERN.match(item):
                raise ValueError(
                    "collect invalide : chaque élément doit respecter ^[a-zA-Z0-9]+$"
                )

        if self.prompt_behavior not in _ALLOWED_PROMPT_BEHAVIORS:
            raise ValueError(
                "prompt_behavior invalide : valeurs autorisées = Auto, SelectAccount, "
                + "Always, Never"
            )

        for fmt in self.export_to:
            if fmt not in _ALLOWED_EXPORT_FORMATS:
                raise ValueError(
                    "export_to invalide : formats autorisés = JSON, HTML, CSV, CLIXML"
                )

        if "JSON" not in self.export_to:
            self.export_to.append("JSON")

        for site in self.scan_sites:
            if not _SCAN_SITE_PATTERN.match(site):
                raise ValueError(
                    "scan_sites invalide : chaque URL doit respecter ^https://"
                    + "[a-zA-Z0-9._/-]+$"
                )


class Monkey365Executor:
    """Exécute Monkey365 via PowerShell et récupère les résultats JSON."""

    config: Monkey365Config
    monkey365_path: Path
    output_dir: Path

    DEFAULT_ANALYSES: ClassVar[dict[M365Provider, list[str]]] = {
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

    def __init__(self, config: Monkey365Config | str, monkey365_path: str | None = None):
        if isinstance(config, Monkey365Config):
            self.config = config
            self.monkey365_path = self._resolve_path(monkey365_path)
        else:
            self.config = Monkey365Config()
            self.monkey365_path = Path(config if monkey365_path is None else monkey365_path)
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str | None) -> Path:
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
            + "  git submodule add https://github.com/silverhack/monkey365 integrations/monkey365\n"
            + "  ou : Install-Module -Name monkey365 -Scope CurrentUser"
        )

    def _get_analyses(self, config: Monkey365Config | None = None) -> list[str]:
        active_config = config or self.config
        if active_config.plugins:
            return active_config.plugins

        try:
            provider = M365Provider(str(active_config.provider))
        except ValueError:
            return []
        return self.DEFAULT_ANALYSES.get(provider, [])

    def build_script(self, scan_id: str | Monkey365Config) -> str:
        """
        Génère le script PowerShell pour lancer le scan.
        Tous les paramètres utilisateur sont validés ET échappés.
        """
        # ── Validation des paramètres sensibles ──────────────────────────
        active_config = self.config
        effective_scan_id = scan_id if isinstance(scan_id, str) else "manual_scan"

        if isinstance(scan_id, Monkey365Config):
            active_config = scan_id

        active_config.validate()
        _ = _validate_uuid(active_config.tenant_id, "tenant_id")

        auth_method_value = str(active_config.auth_method)
        if isinstance(active_config.auth_method, AuthMethod):
            auth_method_value = active_config.auth_method.value

        if auth_method_value == AuthMethod.CLIENT_CREDENTIALS.value:
            _ = _validate_uuid(active_config.client_id, "client_id")
            _ = _validate_secret(active_config.client_secret)
        elif auth_method_value == AuthMethod.CERTIFICATE.value:
            _ = _validate_uuid(active_config.client_id, "client_id")
            if active_config.certificate_path:
                _ = _validate_thumbprint(active_config.certificate_path)

        # Valider les noms d'analyses et rulesets
        for analysis in self._get_analyses(active_config):
            _ = _validate_safe_name(analysis, "analysis")

        if active_config.rulesets:
            for ruleset in active_config.rulesets:
                _ = _validate_safe_name(ruleset, "ruleset")

        # ── Construction du script avec échappement ──────────────────────
        output_path = self.output_dir / effective_scan_id
        analyses = ", ".join(
            f"'{_escape_ps_string(a)}'" for a in self._get_analyses(active_config)
        )

        # Échapper toutes les valeurs interpolées
        safe_module_path = _escape_ps_string(str(self.monkey365_path.parent))
        provider_value = str(active_config.provider)
        if isinstance(active_config.provider, M365Provider):
            provider_value = active_config.provider.value
        safe_provider = _escape_ps_string(provider_value)
        safe_output = _escape_ps_string(str(output_path))
        safe_tenant = _escape_ps_string(active_config.tenant_id)
        export_to = ", ".join(f"'{_escape_ps_string(fmt)}'" for fmt in active_config.export_to)
        include_entra_id = "$true" if active_config.include_entra_id else "$false"
        safe_prompt_behavior = _escape_ps_string(active_config.prompt_behavior)

        collect_param = ""
        if active_config.collect:
            collect_items = ", ".join(
                f"'{_escape_ps_string(item)}'" for item in active_config.collect
            )
            collect_param = f"\n    Collect         = @({collect_items})"

        scan_sites_param = ""
        if active_config.scan_sites:
            scan_sites_items = ", ".join(
                f"'{_escape_ps_string(site)}'" for site in active_config.scan_sites
            )
            scan_sites_param = f"\n    ScanSites       = @({scan_sites_items})"

        force_msal_desktop_param = (
            "\n    ForceMSALDesktop = $true" if active_config.force_msal_desktop else ""
        )
        verbose_param = "\n    Verbose         = $true" if active_config.verbose else ""

        script = f"""
Import-Module '{safe_module_path}' -Force

$params = @{{
    Instance   = '{safe_provider}'
    Analysis   = @({analyses})
    ExportTo   = @({export_to})
    PromptBehavior = '{safe_prompt_behavior}'
    IncludeEntraID = {include_entra_id}{collect_param}{scan_sites_param}{force_msal_desktop_param}{verbose_param}
    OutDir     = '{safe_output}'
    TenantId   = '{safe_tenant}'
}}
"""
        if auth_method_value == AuthMethod.CLIENT_CREDENTIALS.value:
            safe_secret = _escape_ps_string(active_config.client_secret)
            safe_client_id = _escape_ps_string(active_config.client_id)
            script += f"""
$secret = ConvertTo-SecureString '{safe_secret}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential('{safe_client_id}', $secret)
$params['AppCredential'] = $cred
$params['ConfidentialApp'] = $true
"""
        elif auth_method_value == AuthMethod.CERTIFICATE.value:
            safe_client_id = _escape_ps_string(active_config.client_id)
            safe_cert = _escape_ps_string(active_config.certificate_path or "")
            script += f"""
$params['ClientId'] = '{safe_client_id}'
$params['CertificateThumbprint'] = '{safe_cert}'
"""

        if active_config.rulesets:
            ruleset_paths = ", ".join(
                f"'{_escape_ps_string(str(self.monkey365_path.parent / 'rulesets' / r))}.json'"
                for r in active_config.rulesets
            )
            script += f"\n$params['RuleSets'] = @({ruleset_paths})\n"

        script += "\nInvoke-Monkey365 @params\n"
        return script

    def run_scan(self, scan_id: str) -> dict[str, object]:
        """Lance le scan Monkey365 (synchrone)"""
        script = self.build_script(scan_id)
        script_path = self.output_dir / f"{scan_id}_script.ps1"
        _ = script_path.write_text(script, encoding="utf-8")

        try:
            process = subprocess.run(
                ["pwsh", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
                capture_output=True,
                text=True,
                timeout=3600,
            )
            _ = process.returncode
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

    def _parse_output(self, scan_id: str) -> list[dict[str, object]]:
        """Parse les JSON de sortie Monkey365"""
        results: list[dict[str, object]] = []
        output_path = self.output_dir / scan_id

        for json_file in output_path.rglob("*.json"):
            try:
                data: object = cast(object, json.loads(json_file.read_text(encoding="utf-8")))
                if isinstance(data, list):
                    for item in cast(list[object], data):
                        if isinstance(item, dict):
                            results.append(cast(dict[str, object], item))
                elif isinstance(data, dict):
                    results.append(cast(dict[str, object], data))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        return results
