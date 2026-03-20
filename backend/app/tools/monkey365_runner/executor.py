"""
Monkey365 Executor — Bridge Python → PowerShell pour l'audit M365/Azure.

CRITICAL FIX: Authentication modes are now properly conditional.
- INTERACTIVE: Requires ONLY PromptBehavior (no credentials)
- DEVICE_CODE: Requires ONLY DeviceCode flag (no credentials)
- ROPC: Requires username + password + tenant_id
- CLIENT_CREDENTIALS: Requires client_id + client_secret + tenant_id
"""
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, cast

from .config import Monkey365AuthMode, M365Provider

logger = logging.getLogger(__name__)
DEFAULT_MONKEY365_DIR = Path("D:\\AssistantAudit\\tools\\monkey365")


class Monkey365ExecutionError(RuntimeError):
    """Raised when Monkey365 PowerShell execution fails."""


# ── Sanitisation des paramètres PowerShell ───────────────────────────────────

# UUID / GUID pattern (tenant_id, client_id)
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
# Client secret : alphanumériques, tirets, tildes, points, underscores (Azure AD format)
_SECRET_PATTERN = re.compile(r"^[a-zA-Z0-9_.~\-]{1,256}$")
# Email format for username validation
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
# Nom d'analyse / ruleset : alphanum, underscores, tirets
_SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")
_SCAN_SITE_PATTERN = re.compile(r"^https://[a-zA-Z0-9._/-]+$")

# Valid Monkey365 modules for data collection
_ALLOWED_COLLECT_MODULES = {
    "ExchangeOnline",
    "SharePointOnline",
    "Purview",
    "MicrosoftTeams",
    "AdminPortal",
}

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


def _validate_email(value: str, field_name: str) -> str:
    """Valide un email format pour username."""
    if not _EMAIL_PATTERN.match(value):
        raise ValueError(
            f"{field_name} invalide : format email attendu (ex: user@domain.com)"
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


def _mask_password(password: str) -> str:
    """Masque un mot de passe pour les logs (NEVER log plaintext passwords)."""
    return "***" if password else ""


@dataclass
class Monkey365Config:
    """
    Configuration for Monkey365 execution.
    
    Auth modes have different credential requirements:
    - INTERACTIVE: No credentials needed (browser popup)
    - DEVICE_CODE: No credentials needed (device code flow)
    - ROPC: Requires username + password + tenant_id
    - CLIENT_CREDENTIALS: Requires client_id + client_secret + tenant_id
    """
    provider: M365Provider | str = M365Provider.MICROSOFT365
    auth_mode: Monkey365AuthMode | str = Monkey365AuthMode.INTERACTIVE
    
    # Optional credentials (required based on auth_mode)
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    
    output_dir: str = "./monkey365_output"
    rulesets: list[str] = field(default_factory=lambda: ["cis_m365_benchmark"])
    plugins: list[str] = field(default_factory=list)
    collect: list[str] = field(default_factory=list)
    include_entra_id: bool = True
    export_to: list[str] = field(default_factory=lambda: ["JSON", "HTML"])
    scan_sites: list[str] = field(default_factory=list)
    verbose: bool = False

    def validate(self) -> None:
        """Validate configuration based on auth_mode."""
        # Normalize auth_mode to enum value
        auth_mode_value = (
            self.auth_mode.value
            if hasattr(self.auth_mode, "value")
            else str(self.auth_mode)
        )
        
        # CRITICAL: Validate credentials based on auth mode
        if auth_mode_value == Monkey365AuthMode.CLIENT_CREDENTIALS.value:
            if not self.tenant_id or not self.client_id or not self.client_secret:
                raise ValueError(
                    "CLIENT_CREDENTIALS mode requires: tenant_id, client_id, client_secret"
                )
            _validate_uuid(self.tenant_id, "tenant_id")
            _validate_uuid(self.client_id, "client_id")
            _validate_secret(self.client_secret)
        
        elif auth_mode_value == Monkey365AuthMode.ROPC.value:
            if not self.tenant_id or not self.username or not self.password:
                raise ValueError(
                    "ROPC mode requires: tenant_id, username, password"
                )
            _validate_uuid(self.tenant_id, "tenant_id")
            _validate_email(self.username, "username")
            # Password validation: just ensure it's not empty, don't log it
            if len(self.password) < 1:
                raise ValueError("Password cannot be empty for ROPC mode")
        
        elif auth_mode_value in [Monkey365AuthMode.INTERACTIVE.value, Monkey365AuthMode.DEVICE_CODE.value]:
            # These modes require NO credentials
            pass
        
        else:
            raise ValueError(
                f"Invalid auth_mode: {auth_mode_value}. Must be one of: "
                f"interactive, device_code, ropc, client_credentials"
            )

        # Validate collect modules
        for item in self.collect:
            if item not in _ALLOWED_COLLECT_MODULES:
                raise ValueError(
                    f"collect invalide : '{item}' n'est pas un module valide. "
                    f"Modules autorisés : {', '.join(sorted(_ALLOWED_COLLECT_MODULES))}"
                )

        # Validate export formats
        for fmt in self.export_to:
            if fmt not in _ALLOWED_EXPORT_FORMATS:
                raise ValueError(
                    "export_to invalide : formats autorisés = JSON, HTML, CSV, CLIXML"
                )

        if "JSON" not in self.export_to:
            self.export_to.append("JSON")

        # Validate scan sites
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
    _active_scan_id: str | None = None

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
            self.monkey365_path = self._resolve_path(config if monkey365_path is None else monkey365_path)
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str | None) -> Path:
        """Localise Monkey365"""
        if path:
            candidate = Path(path)
            if candidate.is_dir():
                direct_invoke = candidate / "Invoke-Monkey365.ps1"
                direct_module = candidate / "monkey365.psm1"
                if direct_invoke.exists() or direct_module.exists():
                    return direct_invoke

                nested_dir = candidate / "monkey365"
                nested_invoke = nested_dir / "Invoke-Monkey365.ps1"
                nested_module = nested_dir / "monkey365.psm1"
                if nested_invoke.exists() or nested_module.exists():
                    return nested_invoke

                return nested_invoke
            return candidate

        default_invoke = DEFAULT_MONKEY365_DIR / "Invoke-Monkey365.ps1"
        if default_invoke.exists():
            return default_invoke

        integrations_invoke = Path(".\\integrations\\monkey365\\Invoke-Monkey365.ps1")
        if integrations_invoke.exists():
            return integrations_invoke

        # Default to the expected Monkey365 location; ensure_monkey365_ready will auto-install.
        return default_invoke

    def ensure_monkey365_ready(self) -> Path:
        """Ensure Monkey365 is installed and module can be loaded."""
        monkey365_dir = self.monkey365_path.parent if self.monkey365_path else DEFAULT_MONKEY365_DIR

        if not monkey365_dir.exists():
            logger.info("Monkey365 missing. Auto-cloning...")
            monkey365_dir.parent.mkdir(parents=True, exist_ok=True)
            clone_result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    "https://github.com/silverhack/monkey365.git",
                    str(monkey365_dir),
                ],
                capture_output=True,
                text=True,
                cwd=monkey365_dir.parent,
            )
            if clone_result.returncode != 0:
                raise RuntimeError(
                    "Failed to clone Monkey365 repository:\n"
                    + (clone_result.stderr or clone_result.stdout)
                )

        module_path = monkey365_dir / "monkey365.psm1"
        if not module_path.exists():
            logger.warning("Monkey365 module missing at %s; skipping import verification.", monkey365_dir)
            if self.monkey365_path and not self.monkey365_path.exists():
                self.monkey365_path.write_text(
                    "# Auto-generated placeholder for Monkey365 execution script\n",
                    encoding="utf-8",
                )
            return self.monkey365_path

        safe_dir = _escape_ps_string(str(monkey365_dir))
        test_ps = f"""
        Set-Location '{safe_dir}'
        Import-Module .\\monkey365.psm1 -Force -Verbose
        Get-Command Invoke-Monkey365
        """
        result = subprocess.run(
            ["powershell.exe", "-Command", test_ps],
            capture_output=True,
            text=True,
            cwd=monkey365_dir,
        )

        if result.returncode != 0 or "Invoke-Monkey365" not in result.stdout:
            raise RuntimeError("Monkey365 module import failed:\n" + result.stderr)

        logger.info("Monkey365 module verified at %s", monkey365_dir)

        monkey365_script = monkey365_dir / "Invoke-Monkey365.ps1"
        if not monkey365_script.exists():
            monkey365_script.write_text(
                "# Auto-generated placeholder for Monkey365 execution script\n",
                encoding="utf-8",
            )

        self.monkey365_path = monkey365_script
        return monkey365_script

    def parse_results(self, stdout: str) -> list[dict[str, object]]:
        """Parse results from stdout or output directory."""
        if stdout:
            try:
                data = json.loads(stdout)
                if isinstance(data, list):
                    return cast(list[dict[str, object]], data)
                if isinstance(data, dict):
                    return [cast(dict[str, object], data)]
            except json.JSONDecodeError:
                pass

        if self._active_scan_id:
            return self._parse_output(self._active_scan_id)
        return []

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
        
        CRITICAL FIX: PowerShell parameters are now CONDITIONAL based on auth_mode:
        - INTERACTIVE: Only PromptBehavior (NO credentials)
        - DEVICE_CODE: Only DeviceCode flag (NO credentials)
        - ROPC: Username + Password + TenantId
        - CLIENT_CREDENTIALS: ClientId + ClientSecret + TenantId
        
        All user parameters are validated AND escaped.
        """
        # ── Validation des paramètres sensibles ──────────────────────────
        active_config = self.config
        effective_scan_id = scan_id if isinstance(scan_id, str) else "manual_scan"

        if isinstance(scan_id, Monkey365Config):
            active_config = scan_id

        # Validate configuration (includes auth-mode-specific credential checks)
        active_config.validate()

        # Normalize auth_mode to enum value
        auth_mode_value = (
            active_config.auth_mode.value
            if hasattr(active_config.auth_mode, "value")
            else str(active_config.auth_mode)
        )

        # Valider les noms d'analyses et rulesets
        for analysis in self._get_analyses(active_config):
            _ = _validate_safe_name(analysis, "analysis")

        if active_config.rulesets:
            for ruleset in active_config.rulesets:
                _ = _validate_safe_name(ruleset, "ruleset")

        # ── Construction du script avec échappement ──────────────────────
        output_path = self.output_dir / effective_scan_id
        
        safe_monkey365_dir = _escape_ps_string(str(self.monkey365_path.parent))
        provider_value = str(active_config.provider)
        if isinstance(active_config.provider, M365Provider):
            provider_value = active_config.provider.value
        safe_provider = _escape_ps_string(provider_value)
        safe_output = _escape_ps_string(str(output_path))
        export_to = ", ".join(f"'{_escape_ps_string(fmt)}'" for fmt in active_config.export_to)
        include_entra_id = "$true" if active_config.include_entra_id else "$false"

        # Optional collect parameter
        collect_param = ""
        if active_config.collect:
            collect_items = ", ".join(
                f"'{_escape_ps_string(item)}'" for item in active_config.collect
            )
            collect_param = f"\n    Collect         = @({collect_items});"

        # Optional scan sites parameter
        scan_sites_param = ""
        if active_config.scan_sites:
            scan_sites_items = ", ".join(
                f"'{_escape_ps_string(site)}'" for site in active_config.scan_sites
            )
            scan_sites_param = f"\n    ScanSites       = @({scan_sites_items});"

        verbose_param = "\n    Verbose         = $true;" if active_config.verbose else ""

        # ── Build script header (common for all auth modes) ──────────────
        script = f"""
 Set-Location '{safe_monkey365_dir}'
 Import-Module .\\monkey365.psm1 -Force

$param = @{{
    Instance       = '{safe_provider}';{collect_param}
    IncludeEntraID = {include_entra_id};
    ExportTo       = @({export_to});
    OutPath        = '{safe_output}';{scan_sites_param}{verbose_param}
"""

        # ── CONDITIONAL: Add auth-specific parameters ────────────────────
        if auth_mode_value == Monkey365AuthMode.INTERACTIVE.value:
            # INTERACTIVE: ONLY PromptBehavior (NO credentials)
            script += """    PromptBehavior = 'SelectAccount';
"""
            logger.info(f"Building INTERACTIVE auth script (no credentials required)")

        elif auth_mode_value == Monkey365AuthMode.DEVICE_CODE.value:
            # DEVICE CODE: ONLY DeviceCode flag (NO credentials)
            script += """    DeviceCode     = $true;
"""
            logger.info(f"Building DEVICE_CODE auth script (no credentials required)")

        elif auth_mode_value == Monkey365AuthMode.ROPC.value:
            # ROPC: Username + Password + TenantId
            safe_tenant = _escape_ps_string(active_config.tenant_id)
            safe_username = _escape_ps_string(active_config.username)
            safe_password = _escape_ps_string(active_config.password)
            script += f"""    TenantId       = '{safe_tenant}';
    Username       = '{safe_username}';
    Password       = (ConvertTo-SecureString '{safe_password}' -AsPlainText -Force);
"""
            logger.info(
                f"Building ROPC auth script (tenant={active_config.tenant_id}, "
                f"username={active_config.username})"
            )

        elif auth_mode_value == Monkey365AuthMode.CLIENT_CREDENTIALS.value:
            # CLIENT CREDENTIALS: ClientId + ClientSecret + TenantId
            safe_tenant = _escape_ps_string(active_config.tenant_id)
            safe_client_id = _escape_ps_string(active_config.client_id)
            safe_secret = _escape_ps_string(active_config.client_secret)
            script += f"""    TenantId       = '{safe_tenant}';
    ClientId       = '{safe_client_id}';
    ClientSecret   = (ConvertTo-SecureString '{safe_secret}' -AsPlainText -Force);
"""
            logger.info(
                f"Building CLIENT_CREDENTIALS auth script (tenant={active_config.tenant_id}, "
                f"client_id={active_config.client_id}, secret={_mask_password(active_config.client_secret)})"
            )

        # Close the parameter hashtable
        script += "}\n"

        # Optional rulesets
        if active_config.rulesets:
            ruleset_paths = ", ".join(
                f"'{_escape_ps_string(str(self.monkey365_path.parent / 'rulesets' / r))}.json'"
                for r in active_config.rulesets
            )
            script += f"\n$param['RuleSets'] = @({ruleset_paths})\n"

        # Invoke Monkey365
        script += "\nInvoke-Monkey365 @param\n"
        return script

    def run_scan(self, scan_id: str) -> dict[str, object]:
        """Lance le scan Monkey365 (synchrone)"""
        self.ensure_monkey365_ready()
        self._active_scan_id = scan_id

        script = self.build_script(scan_id)
        ps1_path = Path("D:\\AssistantAudit\\temp\\monkey365_scan.ps1")
        ps1_path.parent.mkdir(parents=True, exist_ok=True)
        _ = ps1_path.write_text(script, encoding="utf-8")
        start_time = time.time()
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1_path),
                ],
                capture_output=True,
                text=True,
                timeout=3600,
                cwd=self.monkey365_path.parent,
                env=env,
            )

            raw_output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "duration_seconds": time.time() - start_time,
            }

            (output_path / "powershell_raw_output.json").write_text(
                json.dumps(raw_output, indent=2),
                encoding="utf-8",
            )

            if result.returncode != 0:
                error = Monkey365ExecutionError(
                    "PowerShell failed (code "
                    + str(result.returncode)
                    + "):\nSTDOUT:\n"
                    + result.stdout
                    + "\nSTDERR:\n"
                    + result.stderr
                )
                return {"status": "error", "scan_id": scan_id, "error": str(error)}

            results = self.parse_results(result.stdout)
            return {"status": "success", "scan_id": scan_id, "results": results}

        except subprocess.TimeoutExpired as exc:
            raw_output = {
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "returncode": None,
                "duration_seconds": time.time() - start_time,
            }
            (output_path / "powershell_raw_output.json").write_text(
                json.dumps(raw_output, indent=2),
                encoding="utf-8",
            )
            return {"status": "timeout", "scan_id": scan_id, "error": "Timeout 1h dépassé"}
        except FileNotFoundError:
            return {"status": "error", "scan_id": scan_id, "error": "powershell.exe introuvable"}
        finally:
            if ps1_path.exists():
                ps1_path.unlink()

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
