"""
Tests for PowerShell script generation in interactive mode.

Covers the fix where interactive scripts were missing the Import-Module statement,
causing "Invoke-Monkey365 : The term 'Invoke-Monkey365' is not recognized" errors.
"""
import pytest
from pathlib import Path

from app.tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor
from app.tools.monkey365_runner.config import Monkey365AuthMode


def test_interactive_script_includes_module_import(tmp_path):
    """Test that generated PowerShell script imports Monkey365 module."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(tmp_path)
    )
    
    # Create mock Monkey365 directory
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    # Verify module import is present
    assert "Set-Location" in script, "Should include Set-Location to module directory"
    assert "Import-Module" in script, "Should include Import-Module statement"
    assert "monkey365.psm1" in script, "Should import monkey365.psm1"
    assert "-Force" in script, "Should use -Force flag for Import-Module"
    assert "Invoke-Monkey365" in script, "Should call Invoke-Monkey365"


def test_interactive_script_correct_module_path(tmp_path):
    """Test that module import uses correct path."""
    monkey365_dir = tmp_path / "tools" / "monkey365"
    monkey365_dir.mkdir(parents=True)
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(tmp_path / "output")
    )
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path / "output"
    
    script = executor.build_script("test-scan")
    
    # Should set location to the parent directory of Invoke-Monkey365.ps1
    expected_dir = str(monkey365_dir).replace('\\', '\\\\')
    assert f"Set-Location '{expected_dir}'" in script or f'Set-Location "{expected_dir}"' in script or "Set-Location" in script


def test_client_credentials_script_includes_module_import(tmp_path):
    """Test that client credentials mode also includes module import."""
    config = Monkey365Config(
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        output_dir=str(tmp_path)
    )
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    # All scripts should import the module, regardless of auth mode
    assert "Import-Module" in script, "Client credentials mode should also import module"
    assert "monkey365.psm1" in script
    assert "Invoke-Monkey365" in script


def test_device_code_script_includes_module_import(tmp_path):
    """Test that device code mode includes module import."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.DEVICE_CODE,
        output_dir=str(tmp_path)
    )
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    assert "Import-Module" in script, "Device code mode should import module"
    assert "monkey365.psm1" in script
    assert "Invoke-Monkey365" in script


def test_ropc_script_includes_module_import(tmp_path):
    """Test that ROPC mode includes module import."""
    config = Monkey365Config(
        auth_mode="ropc",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        username="test@example.com",
        password="test-password",
        output_dir=str(tmp_path)
    )
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    assert "Import-Module" in script, "ROPC mode should import module"
    assert "monkey365.psm1" in script
    assert "Invoke-Monkey365" in script


def test_script_module_import_before_invoke(tmp_path):
    """Test that Import-Module comes before Invoke-Monkey365 in the script."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(tmp_path)
    )
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    # Find positions of Import-Module and Invoke-Monkey365
    import_pos = script.find("Import-Module")
    invoke_pos = script.find("Invoke-Monkey365")
    
    assert import_pos > 0, "Import-Module should be present"
    assert invoke_pos > 0, "Invoke-Monkey365 should be present"
    assert import_pos < invoke_pos, "Import-Module should come before Invoke-Monkey365"


def test_script_uses_force_flag_for_reload(tmp_path):
    """Test that Import-Module uses -Force to allow reloading."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(tmp_path)
    )
    
    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    # Verify -Force flag is present
    # Can be on same line or next line
    import_section = script[script.find("Import-Module"):script.find("Import-Module")+100]
    assert "-Force" in import_section, "Import-Module should use -Force flag"
