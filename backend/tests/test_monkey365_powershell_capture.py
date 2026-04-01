"""
Tests for PowerShell stdout/stderr capture to output directory.

Covers the fix where PowerShell output was being discarded.
Now all subprocess output is saved to powershell_raw_output.json.
"""
import json
from unittest.mock import MagicMock, patch

from app.tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor


def _mock_popen(returncode=0, *, write_log_content=None, output_dir=None):
    """Create a MagicMock that behaves like subprocess.Popen for interactive mode."""
    mock_proc = MagicMock()
    mock_proc.returncode = returncode

    def wait_side_effect(timeout=None):
        # Simulate Start-Transcript writing to monkey365.log
        if write_log_content is not None and output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "monkey365.log").write_text(write_log_content, encoding="utf-8")

    mock_proc.wait = MagicMock(side_effect=wait_side_effect)
    return mock_proc


def test_powershell_output_captured_to_file(tmp_path):
    output_dir = tmp_path / "scan_1"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    log_content = "Monkey365 scan completed successfully\nResults written to disk\n"

    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value = _mock_popen(
            returncode=0, write_log_content=log_content, output_dir=output_dir
        )

        executor.run_scan("scan_1")

        output_file = output_dir / "powershell_raw_output.json"
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert "stdout" in output_data
        assert "stderr" in output_data
        assert "returncode" in output_data
        assert output_data["returncode"] == 0
        # stdout comes from Start-Transcript log file, not subprocess.stdout
        assert "Monkey365 scan completed" in output_data["stdout"]
        # stderr is always empty; PowerShell errors are captured in the transcript
        assert output_data["stderr"] == ""


def test_powershell_output_captured_on_failure(tmp_path):
    output_dir = tmp_path / "scan_failed"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    log_content = "Starting scan...\nFATAL ERROR: Authentication failed\n"

    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value = _mock_popen(
            returncode=1, write_log_content=log_content, output_dir=output_dir
        )

        executor.run_scan("scan_failed")

        output_file = output_dir / "powershell_raw_output.json"
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert output_data["returncode"] == 1
        # Errors are captured via Start-Transcript in stdout, not in stderr
        assert "FATAL ERROR" in output_data["stdout"]
        assert output_data["stderr"] == ""


def test_powershell_output_empty_stdout_stderr(tmp_path):
    output_dir = tmp_path / "scan_empty"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value = _mock_popen(returncode=0)

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

    # Start-Transcript captures all PS streams in a single log file
    log_content = 'Output with "quotes" and\nnewlines\nError with \'apostrophes\' and\ttabs\n'

    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value = _mock_popen(
            returncode=0, write_log_content=log_content, output_dir=output_dir
        )

        executor.run_scan("scan_json")

        output_file = output_dir / "powershell_raw_output.json"
        output_data = json.loads(output_file.read_text())

        assert '"quotes"' in output_data["stdout"]
        assert '\n' in output_data["stdout"]
        assert "'apostrophes'" in output_data["stdout"]


def test_run_scan_uses_execution_policy_bypass(tmp_path):
    output_dir = tmp_path / "scan_policy"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))

    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock PowerShell script", encoding="utf-8")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(returncode=0)
        executor.run_scan("scan_policy")

    command_args = mock_popen.call_args.args[0]
    assert "-ExecutionPolicy" in command_args
    assert "Bypass" in command_args


def test_powershell_raw_output_not_in_findings(tmp_path):
    """powershell_raw_output.json is an internal file and should not be parsed as findings."""
    output_dir = tmp_path / "scan_archive"
    output_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(output_dir))
    monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    monkey365_path.write_text("# Mock", encoding="utf-8")

    executor = Monkey365Executor(config, str(monkey365_path.parent))

    # Create internal + real result files
    (output_dir / "powershell_raw_output.json").write_text(
        json.dumps({"stdout": "data", "stderr": "", "returncode": 0})
    )
    (output_dir / "result.json").write_text('[{"status": "ok"}]')
    nested_dir = output_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "nested_result.json").write_text('[{"nested": true}]')

    results = executor._parse_output_files("scan_archive")
    names = [r.get("status") or r.get("nested") for r in results]
    assert "ok" in names
    assert True in names
    # Internal file should not be included
    assert not any(r.get("stdout") == "data" for r in results)
