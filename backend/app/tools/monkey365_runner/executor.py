"""
Monkey365 Executor — Bridge Python → PowerShell pour l'audit M365/Azure.
"""
import json
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
        """Génère le script PowerShell pour lancer le scan"""
        output_path = self.output_dir / scan_id
        analyses = ", ".join(f"'{a}'" for a in self._get_analyses())

        script = f"""
Import-Module '{self.monkey365_path.parent}' -Force

$params = @{{
    Instance   = '{self.config.provider.value}'
    Analysis   = @({analyses})
    ExportTo   = @('JSON', 'HTML')
    OutDir     = '{output_path}'
    TenantId   = '{self.config.tenant_id}'
}}
"""
        if self.config.auth_method == AuthMethod.CLIENT_CREDENTIALS:
            script += f"""
$secret = ConvertTo-SecureString '{self.config.client_secret}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential('{self.config.client_id}', $secret)
$params['AppCredential'] = $cred
$params['ConfidentialApp'] = $true
"""
        elif self.config.auth_method == AuthMethod.CERTIFICATE:
            script += f"""
$params['ClientId'] = '{self.config.client_id}'
$params['CertificateThumbprint'] = '{self.config.certificate_path}'
"""

        if self.config.rulesets:
            ruleset_paths = ", ".join(
                f"'{self.monkey365_path.parent / 'rulesets' / r}.json'"
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
