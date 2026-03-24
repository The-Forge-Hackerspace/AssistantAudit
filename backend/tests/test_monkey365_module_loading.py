"""
Tests for Monkey365 module loading and verification.

Covers ensure_monkey365_ready() which verifies the Monkey365 PowerShell module
is available and can be imported before running scans.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor


def test_ensure_monkey365_ready_module_exists(tmp_path):
    config = Monkey365Config()

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")

    executor = Monkey365Executor(config, str(monkey365_dir))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Invoke-Monkey365\nOther commands...",
            stderr=""
        )

        result = executor.ensure_monkey365_ready()
        assert result.exists()
        assert result == monkey365_dir / "Invoke-Monkey365.ps1"


def test_ensure_monkey365_ready_clones_if_missing(tmp_path):
    config = Monkey365Config()

    monkey365_dir = tmp_path / "monkey365"
    assert not monkey365_dir.exists()

    executor = Monkey365Executor(config, str(tmp_path))

    with patch('subprocess.run') as mock_run:
        def side_effect(*args, **kwargs):
            if 'git' in args[0]:
                monkey365_dir.mkdir()
                (monkey365_dir / "monkey365.psm1").write_text("# Module")
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(
                returncode=0,
                stdout="Invoke-Monkey365",
                stderr=""
            )

        mock_run.side_effect = side_effect

        result = executor.ensure_monkey365_ready()
        assert result.exists()
        assert mock_run.call_count >= 2


def test_module_import_failure_raises_error(tmp_path):
    config = Monkey365Config()

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")

    executor = Monkey365Executor(config, str(monkey365_dir))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Import-Module : The specified module 'monkey365.psm1' was not loaded"
        )

        with pytest.raises(RuntimeError, match="Monkey365 module import failed"):
            executor.ensure_monkey365_ready()


def test_module_import_command_not_found_raises_error(tmp_path):
    config = Monkey365Config()

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")

    executor = Monkey365Executor(config, str(monkey365_dir))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Some-Other-Command\nGet-Help",
            stderr=""
        )

        with pytest.raises(RuntimeError, match="Monkey365 module import failed"):
            executor.ensure_monkey365_ready()


def test_module_verification_with_verbose_output(tmp_path):
    config = Monkey365Config()

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")

    executor = Monkey365Executor(config, str(monkey365_dir))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""CommandType     Name                Version    Source
-----------     ----                -------    ------
Function        Get-MonkeyConfig    1.0        monkey365
Function        Invoke-Monkey365    1.0        monkey365
Function        Set-MonkeyVerbose   1.0        monkey365""",
            stderr=""
        )

        result = executor.ensure_monkey365_ready()
        assert result.exists()


def test_git_clone_failure_raises_error(tmp_path):
    config = Monkey365Config()

    monkey365_dir = tmp_path / "monkey365"
    assert not monkey365_dir.exists()

    executor = Monkey365Executor(config, str(tmp_path))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: repository not found"
        )

        with pytest.raises(RuntimeError, match="Failed to clone Monkey365 repository"):
            executor.ensure_monkey365_ready()


def test_ensure_monkey365_ready_uses_execution_policy_bypass(tmp_path):
    config = Monkey365Config()

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    (monkey365_dir / "monkey365.psm1").write_text("# Mock module", encoding="utf-8")

    executor = Monkey365Executor(config, str(monkey365_dir))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Invoke-Monkey365", stderr="")
        executor.ensure_monkey365_ready()

    command_args = mock_run.call_args.args[0]
    assert "-ExecutionPolicy" in command_args
    assert "Bypass" in command_args
