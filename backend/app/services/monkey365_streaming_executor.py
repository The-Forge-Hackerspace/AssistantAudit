"""
Executeur Monkey365 avec streaming async pour le Device Code Flow.

Lance Monkey365 via asyncio.create_subprocess_exec, detecte le device code
dans la sortie stdout en temps reel, et streame les logs via un callback
WebSocket. Complementaire a l'executeur synchrone existant (tools/monkey365_runner/executor.py)
qui reste utilise pour le mode local Windows avec MSAL desktop.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.core.config import get_settings
from app.models.enums import AuthMethod

logger = logging.getLogger(__name__)


class Monkey365StreamingExecutor:
    """
    Execute Monkey365 via PowerShell sur le serveur (Ubuntu headless).

    Le scan utilise le Device Code Flow :
    1. Monkey365 demande a MSAL un device code
    2. Le code est capture depuis stdout en temps reel
    3. Streame via WebSocket au frontend du technicien
    4. Le tech s'authentifie dans son navigateur
    5. MSAL recoit le token -> scan demarre
    6. Logs streames en temps reel au frontend
    """

    DEVICE_CODE_PATTERN = re.compile(
        r"(https?://microsoft\.com/devicelogin|https?://aka\.ms/devicelogin)"
        r".*?code[:\s]+([A-Z0-9\-]{6,12})",
        re.IGNORECASE,
    )

    def __init__(
        self,
        scan_id: int,
        ws_callback: Callable[[str, dict], Awaitable[None]],
    ) -> None:
        """
        Args:
            scan_id: ID du scan en cours (DB primary key)
            ws_callback: async callable(event_type, data) pour streamer au frontend
        """
        self.scan_id = scan_id
        self.ws_callback = ws_callback
        self.process: asyncio.subprocess.Process | None = None

    async def run_scan_streaming(
        self,
        tenant_id: str,
        subscriptions: list[str] | None = None,
        ruleset: str = "cis",
        auth_method: AuthMethod = AuthMethod.DEVICE_CODE,
    ) -> dict:
        """
        Lance un scan Monkey365 avec streaming des logs.

        Returns:
            dict avec status, scan_id, et les lignes de sortie
        """
        settings = get_settings()
        monkey365_path = settings.MONKEY365_PATH
        if not monkey365_path:
            error_msg = "MONKEY365_PATH non configure"
            await self.ws_callback("scan_error", {
                "scan_id": self.scan_id,
                "error": error_msg,
            })
            raise RuntimeError(error_msg)

        ps_script = self._build_ps_script(
            tenant_id, subscriptions or [], ruleset, auth_method, monkey365_path
        )

        try:
            self.process = await asyncio.create_subprocess_exec(
                "pwsh", "-NoProfile", "-Command", ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            error_msg = "pwsh introuvable — PowerShell 7+ est requis"
            await self.ws_callback("scan_error", {
                "scan_id": self.scan_id,
                "error": error_msg,
            })
            raise RuntimeError(error_msg)

        output_lines: list[str] = []
        device_code_sent = False

        assert self.process.stdout is not None
        async for line_bytes in self.process.stdout:
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            output_lines.append(line)

            # Detecter le device code
            if not device_code_sent:
                match = self.DEVICE_CODE_PATTERN.search(line)
                if match:
                    url = match.group(1)
                    code = match.group(2)
                    await self.ws_callback("device_code", {
                        "scan_id": self.scan_id,
                        "url": url,
                        "code": code,
                        "message": f"Authentifiez-vous sur {url} avec le code : {code}",
                    })
                    device_code_sent = True
                    continue

            # Streamer les logs
            await self.ws_callback("scan_log", {
                "scan_id": self.scan_id,
                "line": line,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # Attendre la fin du process
        assert self.process.stderr is not None
        stderr_data = await self.process.stderr.read()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=3600)
        except asyncio.TimeoutError:
            self.process.terminate()
            await self.ws_callback("scan_error", {
                "scan_id": self.scan_id,
                "error": "Timeout (1h) depasse — scan arrete",
            })
            return {"status": "timeout", "scan_id": self.scan_id, "error": "Timeout 1h exceeded"}

        if self.process.returncode != 0:
            error = stderr_data.decode("utf-8", errors="replace")[:500]
            await self.ws_callback("scan_error", {
                "scan_id": self.scan_id,
                "error": error,
                "returncode": self.process.returncode,
            })
            return {
                "status": "error",
                "scan_id": self.scan_id,
                "error": error,
                "returncode": self.process.returncode,
            }

        await self.ws_callback("scan_complete", {
            "scan_id": self.scan_id,
            "summary": {
                "status": "completed",
                "lines_count": len(output_lines),
            },
        })

        return {
            "status": "success",
            "scan_id": self.scan_id,
            "output_lines": output_lines,
        }

    def _build_ps_script(
        self,
        tenant_id: str,
        subscriptions: list[str],
        ruleset: str,
        auth_method: AuthMethod,
        monkey365_path: str,
    ) -> str:
        """Construit le script PowerShell Monkey365 pour le serveur."""
        from pathlib import Path
        monkey365_dir = str(Path(monkey365_path).parent).replace("'", "''")

        subs_str = ", ".join(f"'{s.replace(chr(39), chr(39)*2)}'" for s in subscriptions) if subscriptions else ""

        auth_param = ""
        if auth_method == AuthMethod.DEVICE_CODE:
            auth_param = "-DeviceCode"
        elif auth_method == AuthMethod.CERTIFICATE:
            auth_param = "-Certificate"
        elif auth_method == AuthMethod.CLIENT_SECRET:
            auth_param = "-ClientSecret"

        return f"""
Set-Location '{monkey365_dir}'
Import-Module .\\monkey365.psm1 -Force

$VerbosePreference = 'Continue'
$param = @{{
    TenantId      = '{tenant_id.replace("'", "''")}';
    Instance      = 'Microsoft365';
    Analysis      = '{ruleset.replace("'", "''")}';
    ExportTo      = @('JSON');
    {f"Subscriptions = @({subs_str});" if subs_str else ""}
}}

Invoke-Monkey365 @param {auth_param} -Verbose
"""

    async def cancel(self) -> None:
        """Annule le scan en cours."""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self.process.kill()
