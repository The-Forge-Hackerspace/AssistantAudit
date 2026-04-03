"""
Tests pour le streaming Monkey365 avec Device Code Flow.

Couvre :
- Detection du device code via regex
- Evenements WebSocket (device_code, scan_log, scan_complete, scan_error)
- Executor streaming async avec subprocess mocke
- Route POST /monkey365/stream (retour immediat, ownership)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import AuthMethod
from app.services.monkey365_streaming_executor import Monkey365StreamingExecutor

# ── Helpers ──────────────────────────────────────────────────────


def _make_executor(scan_id: int = 1) -> tuple[Monkey365StreamingExecutor, AsyncMock]:
    """Cree un executor avec un ws_callback mock."""
    ws_callback = AsyncMock()
    executor = Monkey365StreamingExecutor(scan_id=scan_id, ws_callback=ws_callback)
    return executor, ws_callback


# ── Device Code Regex ────────────────────────────────────────────


class TestDeviceCodeRegex:
    def test_detect_microsoft_devicelogin(self):
        line = "To sign in, use a web browser to open https://microsoft.com/devicelogin and enter code ABC123DEF"
        match = Monkey365StreamingExecutor.DEVICE_CODE_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == "https://microsoft.com/devicelogin"
        assert match.group(2) == "ABC123DEF"

    def test_detect_aka_ms_devicelogin(self):
        line = "Go to https://aka.ms/devicelogin and enter the code: GHIJ45"
        match = Monkey365StreamingExecutor.DEVICE_CODE_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == "https://aka.ms/devicelogin"
        assert match.group(2) == "GHIJ45"

    def test_detect_with_hyphen_code(self):
        line = "Open https://microsoft.com/devicelogin code: ABC-DEF-123"
        match = Monkey365StreamingExecutor.DEVICE_CODE_PATTERN.search(line)
        assert match is not None
        assert match.group(2) == "ABC-DEF-123"

    def test_no_match_on_unrelated_line(self):
        line = "Scanning ExchangeOnline module..."
        match = Monkey365StreamingExecutor.DEVICE_CODE_PATTERN.search(line)
        assert match is None

    def test_case_insensitive(self):
        line = "Visit HTTPS://MICROSOFT.COM/DEVICELOGIN and enter CODE: XYZ789"
        match = Monkey365StreamingExecutor.DEVICE_CODE_PATTERN.search(line)
        assert match is not None


# ── Streaming Executor ───────────────────────────────────────────


class TestStreamingExecutor:
    @pytest.mark.asyncio
    async def test_run_scan_streaming_device_code_detected(self):
        """Le device code est detecte et envoye via ws_callback."""
        executor, ws_callback = _make_executor(scan_id=42)

        # Simuler stdout avec un device code puis des logs
        stdout_lines = [
            b"Initializing Monkey365...\n",
            b"To sign in, use a web browser to open https://microsoft.com/devicelogin and enter code TESTCODE1\n",
            b"Waiting for authentication...\n",
            b"Authentication successful\n",
            b"Scanning ExchangeOnline...\n",
            b"Scan complete\n",
        ]

        mock_process = AsyncMock()
        mock_process.stdout.__aiter__ = lambda self: iter(stdout_lines).__aiter__()  # noqa: E731
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0

        # Async iterator pour stdout
        async def aiter_lines():
            for line in stdout_lines:
                yield line

        mock_process.stdout.__aiter__ = lambda self: aiter_lines()

        with patch("app.services.monkey365_streaming_executor.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(MONKEY365_PATH="/fake/path/Invoke-Monkey365.ps1")
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.run_scan_streaming(
                    tenant_id="test-tenant-id",
                    auth_method=AuthMethod.DEVICE_CODE,
                )

        assert result["status"] == "success"
        assert result["scan_id"] == 42

        # Verifier que device_code a ete envoye
        device_code_calls = [call for call in ws_callback.call_args_list if call.args[0] == "device_code"]
        assert len(device_code_calls) == 1
        data = device_code_calls[0].args[1]
        assert data["url"] == "https://microsoft.com/devicelogin"
        assert data["code"] == "TESTCODE1"
        assert data["scan_id"] == 42

    @pytest.mark.asyncio
    async def test_run_scan_streaming_logs_streamed(self):
        """Chaque ligne de log est streamee via ws_callback."""
        executor, ws_callback = _make_executor(scan_id=10)

        stdout_lines = [
            b"Line 1\n",
            b"Line 2\n",
            b"Line 3\n",
        ]

        mock_process = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0

        async def aiter_lines():
            for line in stdout_lines:
                yield line

        mock_process.stdout.__aiter__ = lambda self: aiter_lines()

        with patch("app.services.monkey365_streaming_executor.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(MONKEY365_PATH="/fake/path/Invoke-Monkey365.ps1")
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                await executor.run_scan_streaming(tenant_id="t", auth_method=AuthMethod.DEVICE_CODE)

        scan_log_calls = [call for call in ws_callback.call_args_list if call.args[0] == "scan_log"]
        assert len(scan_log_calls) == 3
        assert scan_log_calls[0].args[1]["line"] == "Line 1"
        assert scan_log_calls[2].args[1]["line"] == "Line 3"

    @pytest.mark.asyncio
    async def test_run_scan_streaming_complete_event(self):
        """scan_complete est envoye a la fin d'un scan reussi."""
        executor, ws_callback = _make_executor(scan_id=5)

        mock_process = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0

        async def aiter_lines():
            yield b"Done\n"

        mock_process.stdout.__aiter__ = lambda self: aiter_lines()

        with patch("app.services.monkey365_streaming_executor.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(MONKEY365_PATH="/fake/path/Invoke-Monkey365.ps1")
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.run_scan_streaming(tenant_id="t", auth_method=AuthMethod.DEVICE_CODE)

        assert result["status"] == "success"
        complete_calls = [call for call in ws_callback.call_args_list if call.args[0] == "scan_complete"]
        assert len(complete_calls) == 1
        assert complete_calls[0].args[1]["scan_id"] == 5

    @pytest.mark.asyncio
    async def test_run_scan_streaming_error_event_on_nonzero_exit(self):
        """scan_error est envoye si le process retourne un code non-zero."""
        executor, ws_callback = _make_executor(scan_id=7)

        mock_process = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"PowerShell error occurred\n")
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 1

        async def aiter_lines():
            yield b"Starting...\n"

        mock_process.stdout.__aiter__ = lambda self: aiter_lines()

        with patch("app.services.monkey365_streaming_executor.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(MONKEY365_PATH="/fake/path/Invoke-Monkey365.ps1")
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.run_scan_streaming(tenant_id="t", auth_method=AuthMethod.DEVICE_CODE)

        assert result["status"] == "error"
        assert result["returncode"] == 1

        error_calls = [call for call in ws_callback.call_args_list if call.args[0] == "scan_error"]
        assert len(error_calls) == 1
        assert "PowerShell error" in error_calls[0].args[1]["error"]

    @pytest.mark.asyncio
    async def test_run_scan_streaming_no_monkey365_path(self):
        """RuntimeError si MONKEY365_PATH n'est pas configure."""
        executor, ws_callback = _make_executor()

        with patch("app.services.monkey365_streaming_executor.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(MONKEY365_PATH="")
            with pytest.raises(RuntimeError, match="MONKEY365_PATH"):
                await executor.run_scan_streaming(tenant_id="t")

        error_calls = [c for c in ws_callback.call_args_list if c.args[0] == "scan_error"]
        assert len(error_calls) == 1

    @pytest.mark.asyncio
    async def test_run_scan_streaming_pwsh_not_found(self):
        """RuntimeError si pwsh n'est pas installe."""
        executor, ws_callback = _make_executor()

        with patch("app.services.monkey365_streaming_executor.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(MONKEY365_PATH="/fake/path/Invoke-Monkey365.ps1")
            with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("pwsh")):
                with pytest.raises(RuntimeError, match="pwsh"):
                    await executor.run_scan_streaming(tenant_id="t")

        error_calls = [c for c in ws_callback.call_args_list if c.args[0] == "scan_error"]
        assert len(error_calls) == 1

    @pytest.mark.asyncio
    async def test_device_code_sent_only_once(self):
        """Le device code n'est envoye qu'une seule fois meme si le pattern matche plusieurs fois."""
        executor, ws_callback = _make_executor()

        stdout_lines = [
            b"Visit https://microsoft.com/devicelogin and enter code ABCDEF1\n",
            b"Visit https://microsoft.com/devicelogin and enter code GHIJKL2\n",
        ]

        mock_process = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0

        async def aiter_lines():
            for line in stdout_lines:
                yield line

        mock_process.stdout.__aiter__ = lambda self: aiter_lines()

        with patch("app.services.monkey365_streaming_executor.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(MONKEY365_PATH="/fake/path/Invoke-Monkey365.ps1")
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                await executor.run_scan_streaming(tenant_id="t")

        device_calls = [c for c in ws_callback.call_args_list if c.args[0] == "device_code"]
        assert len(device_calls) == 1
        assert device_calls[0].args[1]["code"] == "ABCDEF1"


# ── Build PS Script ──────────────────────────────────────────────


class TestBuildPsScript:
    def test_device_code_flag(self):
        executor, _ = _make_executor()
        script = executor._build_ps_script(
            tenant_id="abc-123",
            subscriptions=[],
            ruleset="cis",
            auth_method=AuthMethod.DEVICE_CODE,
            monkey365_path="/opt/monkey365/Invoke-Monkey365.ps1",
        )
        assert "-DeviceCode" in script
        assert "abc-123" in script
        assert "cis" in script

    def test_certificate_flag(self):
        executor, _ = _make_executor()
        script = executor._build_ps_script(
            tenant_id="t",
            subscriptions=[],
            ruleset="cis",
            auth_method=AuthMethod.CERTIFICATE,
            monkey365_path="/opt/monkey365/Invoke-Monkey365.ps1",
        )
        assert "-Certificate" in script

    def test_subscriptions_included(self):
        executor, _ = _make_executor()
        script = executor._build_ps_script(
            tenant_id="t",
            subscriptions=["sub1", "sub2"],
            ruleset="cis",
            auth_method=AuthMethod.DEVICE_CODE,
            monkey365_path="/opt/monkey365/Invoke-Monkey365.ps1",
        )
        assert "'sub1'" in script
        assert "'sub2'" in script

    @pytest.mark.asyncio
    async def test_cancel(self):
        """cancel() termine le process."""
        executor, _ = _make_executor()
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        executor.process = mock_process

        await executor.cancel()
        mock_process.terminate.assert_called_once()


# ── API Route Tests ──────────────────────────────────────────────


class TestStreamingRoute:
    def _create_entreprise(self, db_session, owner_id):
        from app.models.entreprise import Entreprise

        ent = Entreprise(nom="TestCorp", secteur_activite="IT", owner_id=owner_id)
        db_session.add(ent)
        db_session.commit()
        db_session.refresh(ent)
        return ent

    def _create_audit_for_user(self, db_session, entreprise_id, user_id):
        from app.models.audit import Audit

        audit = Audit(
            nom_projet="Test Audit",
            entreprise_id=entreprise_id,
            owner_id=user_id,
        )
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(audit)
        return audit

    def test_streaming_route_returns_201(self, client, db_session, auditeur_user, auditeur_headers):
        """La route retourne immediatement avec scan_id et status=authenticating."""
        ent = self._create_entreprise(db_session, owner_id=auditeur_user.id)
        self._create_audit_for_user(db_session, ent.id, auditeur_user.id)

        with (
            patch("app.api.v1.tools.monkey365.Monkey365ScanService.create_streaming_scan") as mock_create,
            patch("app.api.v1.tools.monkey365.asyncio.create_task"),
        ):
            mock_result = MagicMock()
            mock_result.id = 99
            mock_result.scan_id = "fake-uuid"
            mock_result.status = MagicMock(value="authenticating")
            mock_result.auth_method = "device_code"
            mock_create.return_value = mock_result

            response = client.post(
                "/api/v1/tools/monkey365/stream",
                json={
                    "entreprise_id": ent.id,
                    "tenant_id": "test-tenant",
                    "auth_method": "device_code",
                },
                headers=auditeur_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["scan_id"] == "fake-uuid"
        assert data["status"] == "authenticating"
        assert data["auth_method"] == "device_code"

    def test_streaming_route_no_ownership_returns_404(
        self,
        client,
        db_session,
        auditeur_user,
        auditeur_headers,
        admin_user,
    ):
        """404 si l'utilisateur n'est ni proprietaire ni lie par audit."""
        ent = self._create_entreprise(db_session, owner_id=admin_user.id)
        # Entreprise appartient a admin, pas d'audit pour auditeur

        response = client.post(
            "/api/v1/tools/monkey365/stream",
            json={
                "entreprise_id": ent.id,
                "tenant_id": "test-tenant",
            },
            headers=auditeur_headers,
        )
        assert response.status_code == 404

    def test_streaming_route_admin_bypasses_ownership(self, client, db_session, admin_user, admin_headers):
        """Les admins peuvent lancer un scan sans ownership."""
        ent = self._create_entreprise(db_session, owner_id=admin_user.id)

        with (
            patch("app.api.v1.tools.monkey365.Monkey365ScanService.create_streaming_scan") as mock_create,
            patch("app.api.v1.tools.monkey365.asyncio.create_task"),
        ):
            mock_result = MagicMock()
            mock_result.id = 1
            mock_result.scan_id = "uuid"
            mock_result.status = MagicMock(value="authenticating")
            mock_result.auth_method = "device_code"
            mock_create.return_value = mock_result

            response = client.post(
                "/api/v1/tools/monkey365/stream",
                json={
                    "entreprise_id": ent.id,
                    "tenant_id": "test-tenant",
                },
                headers=admin_headers,
            )

        assert response.status_code == 201

    def test_streaming_route_unknown_entreprise_returns_404(self, client, auditeur_headers):
        """404 si l'entreprise n'existe pas."""
        response = client.post(
            "/api/v1/tools/monkey365/stream",
            json={
                "entreprise_id": 99999,
                "tenant_id": "test-tenant",
            },
            headers=auditeur_headers,
        )
        assert response.status_code == 404

    def test_streaming_route_requires_auth(self, client):
        """401 sans authentification."""
        response = client.post(
            "/api/v1/tools/monkey365/stream",
            json={
                "entreprise_id": 1,
                "tenant_id": "test-tenant",
            },
        )
        assert response.status_code in (401, 403)

    def test_streaming_route_lecteur_forbidden(self, client, lecteur_headers):
        """403 pour un lecteur (role insuffisant)."""
        response = client.post(
            "/api/v1/tools/monkey365/stream",
            json={
                "entreprise_id": 1,
                "tenant_id": "test-tenant",
            },
            headers=lecteur_headers,
        )
        assert response.status_code == 403
