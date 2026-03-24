"""
Tests for Monkey365 executor and configuration.

Covers Monkey365Config defaults and PowerShell script generation
with the simplified interactive-only configuration.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.tools.monkey365_runner.executor import (
    Monkey365Config,
    Monkey365Executor,
)


# ────────────────────────────────────────────────────────────────────────
# Monkey365Config Defaults Tests
# ────────────────────────────────────────────────────────────────────────


def test_monkey365_config_defaults():
    config = Monkey365Config()
    assert config.output_dir == "./monkey365_output"
    assert config.spo_sites == []
    assert config.export_to == ["JSON", "HTML"]


def test_monkey365_config_custom_values():
    config = Monkey365Config(
        output_dir="/tmp/scan",
        spo_sites=["https://contoso.sharepoint.com"],
        export_to=["JSON"],
    )
    assert config.output_dir == "/tmp/scan"
    assert config.spo_sites == ["https://contoso.sharepoint.com"]
    assert config.export_to == ["JSON"]


# ────────────────────────────────────────────────────────────────────────
# build_script() Tests
# ────────────────────────────────────────────────────────────────────────


def test_build_script_always_includes_select_account(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "PromptBehavior" in script
    assert "SelectAccount" in script


def test_build_script_always_includes_force_msal_desktop(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "ForceMSALDesktop" in script
    assert "$true" in script


def test_build_script_always_includes_include_entra_id(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "IncludeEntraID" in script


def test_build_script_always_includes_instance_microsoft365(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "Instance" in script
    assert "Microsoft365" in script


def test_build_script_includes_5_collect_modules(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "Collect" in script
    assert "ExchangeOnline" in script
    assert "MicrosoftTeams" in script
    assert "Purview" in script
    assert "SharePointOnline" in script
    assert "AdminPortal" in script


def test_build_script_export_to_default(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "ExportTo" in script
    assert "'JSON'" in script
    assert "'HTML'" in script


def test_build_script_export_to_custom(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path), export_to=["JSON"])

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "ExportTo" in script
    assert "'JSON'" in script


def test_build_script_spo_sites_included(tmp_path):
    config = Monkey365Config(
        output_dir=str(tmp_path),
        spo_sites=["https://contoso.sharepoint.com"],
    )

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "SpoSites" in script
    assert "contoso.sharepoint.com" in script


def test_build_script_no_spo_sites_when_empty(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path), spo_sites=[])

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "SpoSites" not in script


def test_build_script_no_credentials(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "TenantId" not in script
    assert "ClientId" not in script
    assert "ClientSecret" not in script
    assert "Username" not in script
    assert "Password" not in script


# ────────────────────────────────────────────────────────────────────────
# run_scan() Tests
# ────────────────────────────────────────────────────────────────────────


def test_run_scan_captures_output_and_imports_module(tmp_path):
    output_dir = tmp_path / "output"
    config = Monkey365Config(output_dir=str(output_dir))

    executor = Monkey365Executor(config, str(tmp_path))
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = output_dir

    script = executor.build_script("scan-1")
    assert "Import-Module .\\monkey365.psm1" in script

    with (
        patch.object(executor, "ensure_monkey365_ready", return_value=executor.monkey365_path),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Scan completed",
            stderr="Warning: minor issue",
        )
        executor.run_scan("scan-1")

    output_file = output_dir / "powershell_raw_output.json"
    assert output_file.exists()
    output_data = json.loads(output_file.read_text(encoding="utf-8"))
    assert output_data["stdout"] == "Scan completed"
    assert output_data["stderr"] == "Warning: minor issue"


def test_ensure_monkey365_ready_creates_directory(tmp_path):
    config = Monkey365Config()
    monkey365_dir = tmp_path / "monkey365"
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    def run_side_effect(*args, **kwargs):
        command = args[0]
        if command[0] == "git":
            monkey365_dir.mkdir()
            (monkey365_dir / "monkey365.psm1").write_text("# Module", encoding="utf-8")
            return MagicMock(returncode=0, stdout="", stderr="")
        return MagicMock(returncode=0, stdout="Invoke-Monkey365", stderr="")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = run_side_effect
        result = executor.ensure_monkey365_ready()

    assert monkey365_dir.exists()
    assert (monkey365_dir / "monkey365.psm1").exists()
    assert result.exists()
