import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)
# Derived from this file's location: backend/app/tools/monkey365_runner/executor.py
# parents[4] → project root (AssistantAudit/)
DEFAULT_MONKEY365_DIR = Path(__file__).resolve().parents[4] / "tools" / "monkey365"


class Monkey365ExecutionError(RuntimeError):
    pass


def _escape_ps_string(value: str) -> str:
    return value.replace("'", "''")


_ANSI_RE = re.compile(r"\x1B\[[0-9;]*[a-zA-Z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


@dataclass
class Monkey365Config:
    output_dir: str = "./monkey365_output"
    spo_sites: list[str] = field(default_factory=list)
    export_to: list[str] = field(default_factory=lambda: ["JSON", "HTML"])
    device_code: bool = False


class Monkey365Executor:

    COLLECT_MODULES = ["ExchangeOnline", "MicrosoftTeams", "Purview", "SharePointOnline", "AdminPortal"]

    def __init__(self, config: Monkey365Config, monkey365_path: str | None = None, allow_auto_clone: bool = False):
        self.config = config
        self.allow_auto_clone = allow_auto_clone
        self.monkey365_path = self._resolve_path(monkey365_path)
        self.monkey365_base_dir: Path = self.monkey365_path.parent
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
            if not self.allow_auto_clone:
                raise RuntimeError(
                    f"Monkey365 not found at {monkey365_dir}. "
                    "Set MONKEY365_PATH to the correct location or enable MONKEY365_AUTO_CLONE."
                )
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
            "pwsh",
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

    def build_script(self, scan_id: str, log_path: Path | None = None) -> str:
        safe_monkey365_dir = _escape_ps_string(str(self.monkey365_path.parent))

        export_to = ", ".join(f"'{_escape_ps_string(fmt)}'" for fmt in self.config.export_to)
        collect_items = ", ".join(f"'{module}'" for module in self.COLLECT_MODULES)

        param_lines = [
            "    Instance        = 'Microsoft365';",
            f"    Collect         = @({collect_items});",
            "    IncludeEntraID  = $true;",
            f"    ExportTo        = @({export_to});",
        ]

        if self.config.device_code:
            param_lines.append("    DeviceCode      = $true;")
        else:
            param_lines.append("    PromptBehavior  = 'SelectAccount';")
            param_lines.append("    ForceMSALDesktop = $true;")

        if self.config.spo_sites:
            sites = ", ".join(f"'{_escape_ps_string(s)}'" for s in self.config.spo_sites)
            param_lines.append(f"    SpoSites        = @({sites});")

        param_block = "\n".join(param_lines)

        # In device code mode, stdout is piped and written to the log file by
        # run_scan() directly — Start-Transcript would conflict (file lock).
        # In interactive mode, Start-Transcript captures all PS streams.
        transcript_start = ""
        transcript_stop = ""
        if log_path and not self.config.device_code:
            safe_log = _escape_ps_string(str(log_path))
            transcript_start = f"Start-Transcript -Path '{safe_log}' -Force | Out-Null"
            transcript_stop = "Stop-Transcript | Out-Null"

        script = f"""
Set-Location '{safe_monkey365_dir}'
Import-Module .\\monkey365.psm1 -Force
{transcript_start}

$VerbosePreference = 'Continue'
$param = @{{
{param_block}
}}

Invoke-Monkey365 @param -Verbose
{transcript_stop}
"""
        return script

    def run_scan(self, scan_id: str) -> dict[str, object]:
        self.ensure_monkey365_ready()

        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        log_file = output_path / "monkey365.log"
        script = self.build_script(scan_id, log_path=log_file)

        params_snapshot: dict[str, object] = {
            "scan_id": scan_id,
            "Instance": "Microsoft365",
            "Collect": self.COLLECT_MODULES,
            "IncludeEntraID": True,
            "ExportTo": self.config.export_to,
            "SpoSites": self.config.spo_sites or [],
        }
        if self.config.device_code:
            params_snapshot["DeviceCode"] = True
        else:
            params_snapshot["PromptBehavior"] = "SelectAccount"
            params_snapshot["ForceMSALDesktop"] = True
        (output_path / "scan_params.json").write_text(
            json.dumps(params_snapshot, indent=2),
            encoding="utf-8",
        )

        temp_dir_env = os.getenv("ASSISTANTAUDIT_TEMP_DIR", "").strip()
        temp_dir = Path(temp_dir_env) if temp_dir_env else (self.output_dir.parent / "temp")
        ps1_path = temp_dir / f"monkey365_scan_{scan_id}.ps1"
        ps1_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("[MONKEY365] Generated script:\n%s", script)
        ps1_path.write_text(script, encoding="utf-8")

        start_time = time.time()
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            powershell_command = [
                "pwsh",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1_path),
            ]
            logger.info("[MONKEY365] Running PowerShell with args: %s", powershell_command)

            if self.config.device_code:
                # Device Code mode: MSAL prints the code to stdout (no popup).
                # Start-Transcript does NOT capture .NET MSAL output, so we
                # pipe stdout+stderr and write each line to monkey365.log ourselves.
                proc = subprocess.Popen(
                    powershell_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self.monkey365_path.parent,
                    env=env,
                )
                with open(log_file, "w", encoding="utf-8") as lf:
                    assert proc.stdout is not None
                    for raw_line in proc.stdout:
                        decoded = _strip_ansi(raw_line.decode("utf-8", errors="replace"))
                        lf.write(decoded)
                        lf.flush()
                proc.wait(timeout=3600)
                returncode = proc.returncode
            else:
                # Interactive mode: stdin/stdout/stderr inherited so MSAL
                # browser popup stays visible. Logs via Start-Transcript.
                result = subprocess.run(
                    powershell_command,
                    timeout=3600,
                    cwd=self.monkey365_path.parent,
                    env=env,
                )
                returncode = result.returncode

            ps_stdout = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
            ps_stderr = ""

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
                    + ")"
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
            return {"status": "error", "scan_id": scan_id, "error": "pwsh not found — PowerShell 7+ is required"}
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

        _INTERNAL_FILES = {"powershell_raw_output.json", "scan_params.json"}
        for json_file in output_path.rglob("*.json"):
            if json_file.name in _INTERNAL_FILES:
                continue
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
