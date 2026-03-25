"""
Tests for PowerShell stdout/stderr capture to output directory.

Covers the fix where PowerShell output was being discarded.
Now all subprocess output is saved to powershell_raw_output.json.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor


def test_powershell_output_captured_to_file(tmp_path):
    output_dir = tmp_path / "scan_1"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Monkey365 scan completed successfully\nResults written to disk",
            stderr="Warning: Some non-critical issue"
        )

        executor.run_scan("scan_1")

        output_file = output_dir / "powershell_raw_output.json"
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert "stdout" in output_data
        assert "stderr" in output_data
        assert "returncode" in output_data
        assert output_data["returncode"] == 0
        assert "Monkey365 scan completed" in output_data["stdout"]
        assert "Warning" in output_data["stderr"]


def test_powershell_output_captured_on_failure(tmp_path):
    output_dir = tmp_path / "scan_failed"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="Starting scan...",
            stderr="FATAL ERROR: Authentication failed"
        )

        executor.run_scan("scan_failed")

        output_file = output_dir / "powershell_raw_output.json"
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert output_data["returncode"] == 1
        assert "FATAL ERROR" in output_data["stderr"]


def test_powershell_output_empty_stdout_stderr(tmp_path):
    output_dir = tmp_path / "scan_empty"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        executor.run_scan("scan_empty")

        output_file = output_dir / "powershell_raw_output.json"
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert output_data["stdout"] == ""
        assert output_data["stderr"] == ""
        assert output_data["returncode"] == 0


def test_powershell_output_json_format_valid(tmp_path):
    output_dir = tmp_path / "scan_json"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Output with "quotes" and\nnewlines',
            stderr="Error with 'apostrophes' and\ttabs"
        )

        executor.run_scan("scan_json")

        output_file = output_dir / "powershell_raw_output.json"
        output_data = json.loads(output_file.read_text())

        assert '"quotes"' in output_data["stdout"]
        assert '\n' in output_data["stdout"]
        assert "'apostrophes'" in output_data["stderr"]


def test_run_scan_uses_execution_policy_bypass(tmp_path):
    output_dir = tmp_path / "scan_policy"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script", encoding="utf-8")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        executor.run_scan("scan_policy")

    command_args = mock_run.call_args.args[0]
    assert "-ExecutionPolicy" in command_args
    assert "Bypass" in command_args


def test_powershell_raw_output_not_copied_to_archive(tmp_path):
    from unittest.mock import patch as _patch
    from app.services.monkey365_scan_service import Monkey365ScanService

    scan_id = "test-archive-scan"

    monkey365_base = tmp_path / "monkey365_tool"
    monkey365_base.mkdir()
    monkey_reports = monkey365_base / "monkey-reports" / scan_id
    monkey_reports.mkdir(parents=True)

    raw_output_file = monkey_reports / "powershell_raw_output.json"
    other_result_file = monkey_reports / "result.json"
    nested_dir = monkey_reports / "nested"
    nested_dir.mkdir()
    nested_file = nested_dir / "nested_result.json"

    raw_output_file.write_text(json.dumps({"stdout": "data", "stderr": "", "returncode": 0}))
    other_result_file.write_text('{"status": "ok"}')
    nested_file.write_text('{"nested": true}')

    dest = tmp_path / "output"
    dest.mkdir(parents=True)

    Monkey365ScanService.move_results_to_output(monkey_reports, dest)

    assert not (dest / "powershell_raw_output.json").exists(), \
        "powershell_raw_output.json must not be copied to the output"
    assert (dest / "result.json").exists(), \
        "result.json should be present in the output"
    assert (dest / "nested" / "nested_result.json").exists(), \
        "nested files should be preserved in the output"
