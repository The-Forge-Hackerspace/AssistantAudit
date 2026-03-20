"""
Tests for Monkey365 module loading and verification.

Covers ensure_monkey365_ready() which verifies the Monkey365 PowerShell module
is available and can be imported before running scans.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor
from app.tools.monkey365_runner.config import Monkey365AuthMode


def test_ensure_monkey365_ready_module_exists(tmp_path):
    """Test that ensure_monkey365_ready succeeds when module is already available."""
    config = Monkey365Config(auth_mode=Monkey365AuthMode.INTERACTIVE)
    
    # Create a mock Monkey365 directory
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")
    
    executor = Monkey365Executor(config, str(monkey365_dir))
    
    with patch('subprocess.run') as mock_run:
        # Simulate successful Import-Module
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Invoke-Monkey365\nOther commands...",
            stderr=""
        )
        
        # Should not raise
        result = executor.ensure_monkey365_ready()
        assert result.exists(), "Should return existing path"
        assert result == monkey365_dir / "Invoke-Monkey365.ps1"


def test_ensure_monkey365_ready_clones_if_missing(tmp_path):
    """Test that ensure_monkey365_ready clones repo if directory doesn't exist."""
    config = Monkey365Config(auth_mode=Monkey365AuthMode.INTERACTIVE)
    
    # Directory doesn't exist yet
    monkey365_dir = tmp_path / "monkey365"
    assert not monkey365_dir.exists(), "Directory should not exist initially"
    
    executor = Monkey365Executor(config, str(tmp_path))
    
    with patch('subprocess.run') as mock_run:
        def side_effect(*args, **kwargs):
            # First call: git clone (create directory)
            if 'git' in args[0]:
                monkey365_dir.mkdir()
                (monkey365_dir / "monkey365.psm1").write_text("# Module")
                return MagicMock(returncode=0, stdout="", stderr="")
            # Second call: Import-Module verification
            return MagicMock(
                returncode=0,
                stdout="Invoke-Monkey365",
                stderr=""
            )
        
        mock_run.side_effect = side_effect
        
        result = executor.ensure_monkey365_ready()
        assert result.exists(), "Should return cloned path"
        assert mock_run.call_count >= 2, "Should call git clone and Import-Module"


def test_module_import_failure_raises_error(tmp_path):
    """Test that module import failure raises RuntimeError."""
    config = Monkey365Config(auth_mode=Monkey365AuthMode.INTERACTIVE)
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")
    
    executor = Monkey365Executor(config, str(monkey365_dir))
    
    with patch('subprocess.run') as mock_run:
        # Simulate Import-Module failure
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Import-Module : The specified module 'monkey365.psm1' was not loaded"
        )
        
        with pytest.raises(RuntimeError, match="Monkey365 module import failed"):
            executor.ensure_monkey365_ready()


def test_module_import_command_not_found_raises_error(tmp_path):
    """Test that missing Invoke-Monkey365 command raises RuntimeError."""
    config = Monkey365Config(auth_mode=Monkey365AuthMode.INTERACTIVE)
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")
    
    executor = Monkey365Executor(config, str(monkey365_dir))
    
    with patch('subprocess.run') as mock_run:
        # Simulate successful import but Invoke-Monkey365 not found
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Some-Other-Command\nGet-Help",  # Missing Invoke-Monkey365
            stderr=""
        )
        
        with pytest.raises(RuntimeError, match="Monkey365 module import failed"):
            executor.ensure_monkey365_ready()


def test_module_verification_with_verbose_output(tmp_path):
    """Test that module verification works even with verbose PowerShell output."""
    config = Monkey365Config(auth_mode=Monkey365AuthMode.INTERACTIVE)
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    module_file = monkey365_dir / "monkey365.psm1"
    module_file.write_text("# Mock module")
    
    executor = Monkey365Executor(config, str(monkey365_dir))
    
    with patch('subprocess.run') as mock_run:
        # Simulate verbose output with Invoke-Monkey365 present
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""CommandType     Name                Version    Source
-----------     ----                -------    ------
Function        Get-MonkeyConfig    1.0        monkey365
Function        Invoke-Monkey365    1.0        monkey365
Function        Set-MonkeyVerbose   1.0        monkey365""",
            stderr=""
        )
        
        # Should not raise — Invoke-Monkey365 is in the output
        result = executor.ensure_monkey365_ready()
        assert result.exists()


def test_git_clone_failure_raises_error(tmp_path):
    """Test that git clone failure raises RuntimeError."""
    config = Monkey365Config(auth_mode=Monkey365AuthMode.INTERACTIVE)
    
    monkey365_dir = tmp_path / "monkey365"
    assert not monkey365_dir.exists()
    
    executor = Monkey365Executor(config, str(tmp_path))
    
    with patch('subprocess.run') as mock_run:
        # Simulate git clone failure
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: repository not found"
        )
        
        with pytest.raises(RuntimeError, match="Failed to clone Monkey365 repository"):
            executor.ensure_monkey365_ready()
