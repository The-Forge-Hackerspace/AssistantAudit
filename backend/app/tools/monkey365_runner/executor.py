import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from .config import M365Provider

logger = logging.getLogger(__name__)
DEFAULT_MONKEY365_DIR = Path("D:\\AssistantAudit\\tools\\monkey365")


class Monkey365ExecutionError(RuntimeError):
    pass


def _escape_ps_string(value: str) -> str:
    return value.replace("'", "''")


def _to_ps_value(value: object) -> str:
    """Convert a Python value to a PowerShell literal."""
    if value is None:
        return "$null"
    if isinstance(value, bool):
        return "$true" if value else "$false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        items = ", ".join(f"'{_escape_ps_string(str(v))}'" for v in value)
        return f"@({items})"
    return f"'{_escape_ps_string(str(value))}'"


@dataclass
class Monkey365Config:
    output_dir: str = "./monkey365_output"
    spo_sites: list[str] = field(default_factory=list)
    export_to: list[str] = field(default_factory=lambda: ["JSON", "HTML"])
    auth_mode: str | None = None
    force_msal_desktop: bool = False
    powershell_config: dict | None = None


class Monkey365Executor:
    
    COLLECT_MODULES = ["ExchangeOnline", "MicrosoftTeams", "Purview", "SharePointOnline", "AdminPortal"]
    
    def __init__(self, config: Monkey365Config, monkey365_path: str | None = None):
        self.config = config
        self.monkey365_path = self._resolve_path(monkey365_path)
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str | None) -> Path:
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

        return default_invoke

    def ensure_monkey365_ready(self) -> Path:
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
            logger.warning("Monkey365 module missing at %s", monkey365_dir)
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
        verify_command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            test_ps,
        ]
        logger.info("[MONKEY365] Verifying module with command args: %s", verify_command)
        result = subprocess.run(
            verify_command,
            capture_output=True,
            text=True,
            cwd=monkey365_dir,
        )

        stderr = result.stderr or ""
        if (
            "exécution de scripts est désactivée" in stderr.lower()
            or "execution of scripts is disabled" in stderr.lower()
        ):
            logger.error(
                "[MONKEY365] Execution policy blocked module import. STDERR:\n%s",
                result.stderr,
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

    # Maps Python auth_mode values to Monkey365 PromptBehavior values
    _PROMPT_BEHAVIOR_MAP = {
        "interactive": "SelectAccount",
        "device_code": "DeviceCode",
        "ropc": "UserPasswordCredential",
        "client_credentials": "ClientCredentials",
    }

    def build_script(self, scan_id: str) -> str:
        safe_monkey365_dir = _escape_ps_string(str(self.monkey365_path.parent))

        export_to = ", ".join(f"'{_escape_ps_string(fmt)}'" for fmt in self.config.export_to)
        collect_items = ", ".join(f"'{module}'" for module in self.COLLECT_MODULES)

        auth_mode = self.config.auth_mode or "interactive"
        prompt_behavior = self._PROMPT_BEHAVIOR_MAP.get(auth_mode, "SelectAccount")

        param_lines = [
            f"    Instance        = 'Microsoft365';",
            f"    Collect         = @({collect_items});",
            f"    PromptBehavior  = '{prompt_behavior}';",
            f"    IncludeEntraID  = $true;",
            f"    ExportTo        = @({export_to});",
        ]

        if self.config.force_msal_desktop:
            param_lines.append("    ForceMSALDesktop = $true;")

        # Merge any extra PowerShell params from powershell_config (e.g. TenantId, ClientId, …)
        if self.config.powershell_config:
            for key, value in self.config.powershell_config.items():
                param_lines.append(f"    {key} = {_to_ps_value(value)};")

        param_block = "\n".join(param_lines)
        script = f"""
Set-Location '{safe_monkey365_dir}'
Import-Module .\\monkey365.psm1 -Force

$param = @{{
{param_block}
}}

Invoke-Monkey365 @param
"""
        return script

    def _find_powershell(self) -> str:
        """Find PowerShell executable, preferring pwsh (7+) over powershell (5.1)"""
        # Try PowerShell 7+ (Core) first
        try:
            result = subprocess.run(
                ["pwsh.exe", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip().startswith("7"):
                logger.info("[MONKEY365] Using PowerShell 7+ (pwsh.exe)")
                return "pwsh.exe"
        except FileNotFoundError:
            pass

        # Fall back to Windows PowerShell 5.1
        logger.info("[MONKEY365] Using Windows PowerShell 5.1 (powershell.exe)")
        return "powershell.exe"

    def run_scan(self, scan_id: str) -> dict[str, object]:
        self.ensure_monkey365_ready()

        script = self.build_script(scan_id)
        temp_dir_env = os.getenv("ASSISTANTAUDIT_TEMP_DIR", "").strip()
        temp_dir = Path(temp_dir_env) if temp_dir_env else (self.output_dir.parent / "temp")
        ps1_path = temp_dir / "monkey365_scan.ps1"
        ps1_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("[MONKEY365] Generated script:\n%s", script)
        ps1_path.write_text(script, encoding="utf-8")
        
        start_time = time.time()
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            ps_executable = self._find_powershell()
            powershell_command = [
                ps_executable,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1_path),
            ]
            logger.info("[MONKEY365] Running PowerShell with args: %s", powershell_command)

            # Interactive and device_code modes need a live terminal:
            # - interactive: browser popup must be able to open
            # - device_code: auth code must be printed to the user's console
            # For these modes we do NOT capture stdout/stderr so the prompt is visible;
            # results are read back from the output files written by Monkey365.
            non_interactive_modes = {"ropc", "client_credentials"}
            auth_mode = self.config.auth_mode or "interactive"
            is_automated = auth_mode in non_interactive_modes

            if is_automated:
                result = subprocess.run(
                    powershell_command,
                    capture_output=True,
                    text=True,
                    timeout=3600,
                    cwd=self.monkey365_path.parent,
                    env=env,
                )
                ps_stdout = result.stdout
                ps_stderr = result.stderr
                returncode = result.returncode
            else:
                # Let stdin/stdout/stderr inherit from the parent process so the
                # user sees log output and any auth prompt in the server terminal.
                result = subprocess.run(
                    powershell_command,
                    stdin=None,
                    stdout=None,
                    stderr=None,
                    timeout=3600,
                    cwd=self.monkey365_path.parent,
                    env=env,
                )
                ps_stdout = ""
                ps_stderr = ""
                returncode = result.returncode

            stderr = ps_stderr
            if (
                "exécution de scripts est désactivée" in stderr.lower()
                or "execution of scripts is disabled" in stderr.lower()
            ):
                logger.error(
                    "[MONKEY365] Execution policy blocked. STDERR:\n%s",
                    ps_stderr,
                )

            raw_output = {
                "stdout": ps_stdout,
                "stderr": ps_stderr,
                "returncode": returncode,
                "duration_seconds": time.time() - start_time,
            }

            (output_path / "powershell_raw_output.json").write_text(
                json.dumps(raw_output, indent=2),
                encoding="utf-8",
            )

            if returncode != 0:
                error = Monkey365ExecutionError(
                    "PowerShell failed (code "
                    + str(returncode)
                    + "):\nSTDOUT:\n"
                    + ps_stdout
                    + "\nSTDERR:\n"
                    + ps_stderr
                )
                return {"status": "error", "scan_id": scan_id, "error": str(error)}

            results = self.parse_results(ps_stdout, scan_id)
            return {"status": "success", "scan_id": scan_id, "results": results}

        except subprocess.TimeoutExpired as exc:
            raw_output = {
                "stdout": (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                "stderr": (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                "returncode": None,
                "duration_seconds": time.time() - start_time,
            }
            (output_path / "powershell_raw_output.json").write_text(
                json.dumps(raw_output, indent=2),
                encoding="utf-8",
            )
            return {"status": "timeout", "scan_id": scan_id, "error": "Timeout 1h exceeded"}
        except FileNotFoundError:
            return {"status": "error", "scan_id": scan_id, "error": "powershell.exe not found"}
        finally:
            if ps1_path.exists():
                ps1_path.unlink()

    def parse_results(self, stdout: str, scan_id: str) -> list[dict[str, object]]:
        if stdout:
            try:
                data = json.loads(stdout)
                if isinstance(data, list):
                    return cast(list[dict[str, object]], data)
                if isinstance(data, dict):
                    return [cast(dict[str, object], data)]
            except json.JSONDecodeError:
                pass

        return self._parse_output_files(scan_id)

    def _parse_output_files(self, scan_id: str) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        output_path = self.output_dir

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
