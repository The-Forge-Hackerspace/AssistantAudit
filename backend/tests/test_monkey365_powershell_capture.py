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
