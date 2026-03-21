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
from app.tools.monkey365_runner.config import Monkey365AuthMode


def test_powershell_output_captured_to_file(tmp_path):
    """Test that PowerShell stdout/stderr are saved to output dir."""
    output_dir = tmp_path / "scan_1"
    output_dir.mkdir(parents=True)
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(output_dir)
    )
    
    # Mock the Monkey365 path to exist
    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")
    
    executor = Monkey365Executor(config, str(monkey365_path.parent))
    
    # Mock subprocess.run to return fake output
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Monkey365 scan completed successfully\nResults written to disk",
            stderr="Warning: Some non-critical issue"
        )
        
        executor.run_scan("scan_1")
        
        # Verify powershell_raw_output.json was created
        output_file = output_dir / "powershell_raw_output.json"
        assert output_file.exists(), f"Expected {output_file} to exist"
        
        output_data = json.loads(output_file.read_text())
        assert "stdout" in output_data, "Expected 'stdout' in output"
        assert "stderr" in output_data, "Expected 'stderr' in output"
        assert "returncode" in output_data, "Expected 'returncode' in output"
        assert output_data["returncode"] == 0, "Expected returncode 0"
        assert "Monkey365 scan completed" in output_data["stdout"]
        assert "Warning" in output_data["stderr"]


def test_powershell_output_captured_on_failure(tmp_path):
    """Test that PowerShell output is captured even when scan fails."""
    output_dir = tmp_path / "scan_failed"
    output_dir.mkdir(parents=True)
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(output_dir)
    )
    
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
        
        # Verify output was still captured
        output_file = output_dir / "powershell_raw_output.json"
        assert output_file.exists(), "Output should be captured even on failure"
        
        output_data = json.loads(output_file.read_text())
        assert output_data["returncode"] == 1, "Expected returncode 1"
        assert "FATAL ERROR" in output_data["stderr"]


def test_powershell_output_empty_stdout_stderr(tmp_path):
    """Test that empty stdout/stderr are handled correctly."""
    output_dir = tmp_path / "scan_empty"
    output_dir.mkdir(parents=True)
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(output_dir)
    )
    
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
        assert output_file.exists(), "Output file should be created even with empty output"
        
        output_data = json.loads(output_file.read_text())
        assert output_data["stdout"] == "", "Empty stdout should be preserved"
        assert output_data["stderr"] == "", "Empty stderr should be preserved"
        assert output_data["returncode"] == 0


def test_powershell_output_json_format_valid(tmp_path):
    """Test that the output JSON format is valid and parseable."""
    output_dir = tmp_path / "scan_json"
    output_dir.mkdir(parents=True)
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(output_dir)
    )
    
    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")
    
    executor = Monkey365Executor(config, str(monkey365_path.parent))
    
    with patch('subprocess.run') as mock_run:
        # Include special characters that need proper JSON encoding
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Output with "quotes" and\nnewlines',
            stderr="Error with 'apostrophes' and\ttabs"
        )
        
        executor.run_scan("scan_json")
        
        output_file = output_dir / "powershell_raw_output.json"
        
        # Should not raise json.JSONDecodeError
        output_data = json.loads(output_file.read_text())
        
        # Verify special characters preserved
        assert '"quotes"' in output_data["stdout"]
        assert '\n' in output_data["stdout"]
        assert "'apostrophes'" in output_data["stderr"]


def test_run_scan_uses_execution_policy_bypass(tmp_path):
    """Scan execution should force process-scoped bypass in child PowerShell."""
    output_dir = tmp_path / "scan_policy"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(output_dir),
    )

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
    """Ensure powershell_raw_output.json is excluded from the archive."""
    from unittest.mock import patch as _patch
    from app.services.monkey365_scan_service import Monkey365ScanService

    scan_id = "test-archive-scan"
    scan_output_dir = tmp_path / "scan_output"
    scan_output_dir.mkdir(parents=True)

    raw_output_file = scan_output_dir / "powershell_raw_output.json"
    other_result_file = scan_output_dir / "result.json"
    nested_dir = scan_output_dir / "nested"
    nested_dir.mkdir()
    nested_file = nested_dir / "nested_result.json"

    raw_output_file.write_text(json.dumps({"stdout": "data", "stderr": "", "returncode": 0}))
    other_result_file.write_text('{"status": "ok"}')
    nested_file.write_text('{"nested": true}')

    archive_base = tmp_path / "archive"
    archive_base.mkdir(parents=True)

    with _patch("app.services.monkey365_scan_service.settings") as mock_settings:
        mock_settings.MONKEY365_ARCHIVE_PATH = str(archive_base)
        result_path = Monkey365ScanService.move_results_to_archive(scan_id, scan_output_dir)

    assert not (result_path / "powershell_raw_output.json").exists(), \
        "powershell_raw_output.json must not be copied to the archive"
    assert (result_path / "result.json").exists(), \
        "result.json should be present in the archive"
    assert (result_path / "nested" / "nested_result.json").exists(), \
        "nested files should be preserved in the archive"
