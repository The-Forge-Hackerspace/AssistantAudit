"""
Tests for Monkey365 executor and configuration.

Covers Monkey365Config defaults, validation rules, and PowerShell script generation.
"""

import pytest

from app.tools.monkey365_runner.executor import (
    Monkey365Config,
    M365Provider,
)
from app.tools.monkey365_runner.config import Monkey365AuthMode


# ────────────────────────────────────────────────────────────────────────
# Monkey365Config Defaults Tests
# ────────────────────────────────────────────────────────────────────────


def test_monkey365_config_defaults():
    """Test Monkey365Config has correct defaults for new fields."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-secret-123",
    )
    
    # Verify new field defaults
    assert config.collect == [], f"Expected empty collect, got {config.collect}"
    assert config.include_entra_id == True, f"Expected True, got {config.include_entra_id}"
    assert config.export_to == ["JSON", "HTML"], f"Expected ['JSON', 'HTML'], got {config.export_to}"
    assert config.scan_sites == [], f"Expected empty scan_sites, got {config.scan_sites}"
    assert config.verbose == False, f"Expected False, got {config.verbose}"


def test_monkey365_config_minimal():
    """Test minimal Monkey365Config works with required fields only."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="abcdef123456",
    )
    
    # Should not raise, defaults should be set
    assert config.provider == "Microsoft365"
    assert config.auth_mode == "client_credentials"
    assert config.collect == []


# ────────────────────────────────────────────────────────────────────────
# Validation Tests - collect
# ────────────────────────────────────────────────────────────────────────


def test_validation_invalid_collect():
    """Test validation rejects invalid collect items with special chars."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        collect=["bad chars!"]
    )
    
    with pytest.raises(ValueError, match="collect invalide"):
        config.validate()


def test_validation_valid_collect():
    """Test validation accepts valid collect items."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        collect=["SharePointOnline", "ExchangeOnline"]
    )
    
    # Should not raise
    config.validate()
    assert config.collect == ["SharePointOnline", "ExchangeOnline"]


# ────────────────────────────────────────────────────────────────────────
# Validation Tests - export_to
# ────────────────────────────────────────────────────────────────────────


def test_validation_invalid_export_to():
    """Test validation rejects invalid export_to formats."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        export_to=["UNKNOWN"]
    )
    
    with pytest.raises(ValueError, match="export_to invalide"):
        config.validate()


def test_validation_json_auto_append():
    """Test validation auto-appends JSON to export_to if not present."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        export_to=["CSV"]
    )
    
    config.validate()
    
    # JSON should be auto-appended
    assert "JSON" in config.export_to, f"Expected JSON in export_to, got {config.export_to}"
    assert "CSV" in config.export_to, f"Expected CSV in export_to, got {config.export_to}"


def test_validation_json_not_duplicated():
    """Test validation does not duplicate JSON if already present."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        export_to=["JSON", "HTML"]
    )
    
    config.validate()
    
    # Should have JSON only once
    json_count = config.export_to.count("JSON")
    assert json_count == 1, f"Expected 1 JSON, got {json_count} in {config.export_to}"


# ────────────────────────────────────────────────────────────────────────
# Validation Tests - scan_sites
# ────────────────────────────────────────────────────────────────────────


def test_validation_invalid_scan_sites_http():
    """Test validation rejects HTTP URLs (requires HTTPS)."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        scan_sites=["http://test.com"]
    )
    
    with pytest.raises(ValueError, match="scan_sites invalide"):
        config.validate()


def test_validation_valid_scan_sites():
    """Test validation accepts valid HTTPS URLs."""
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        scan_sites=["https://sharepoint.example.com/sites/test"]
    )
    
    # Should not raise
    config.validate()
    assert config.scan_sites == ["https://sharepoint.example.com/sites/test"]


# ────────────────────────────────────────────────────────────────────────
# build_script() Tests - Conditional Parameters
# ────────────────────────────────────────────────────────────────────────


def test_build_script_collect_present_when_non_empty(tmp_path):
    """Test build_script includes Collect when collect is non-empty."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        collect=["SharePointOnline"],
        output_dir=str(tmp_path)
    )
    
    # Create executor (will fail to find Monkey365, but we only need build_script)
    # Mock the path resolution
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    assert "Collect" in script, "Expected 'Collect' parameter in script"
    assert "SharePointOnline" in script, "Expected 'SharePointOnline' in script"


def test_build_script_collect_absent_when_empty(tmp_path):
    """Test build_script omits Collect when collect is empty."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        collect=[],  # Empty
        output_dir=str(tmp_path)
    )
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    # Collect should not be in the script
    # Look for the parameter line (with indentation)
    assert "Collect" not in script, "Did not expect 'Collect' parameter in script when empty"


def test_build_script_prompt_behavior_present(tmp_path):
    """Test build_script includes PromptBehavior for interactive auth."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        output_dir=str(tmp_path)
    )
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    assert "PromptBehavior" in script, "Expected 'PromptBehavior' parameter in script"
    assert "SelectAccount" in script, "Expected 'SelectAccount' value in script"


def test_build_script_export_to_dynamic(tmp_path):
    """Test build_script generates ExportTo with custom formats."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        export_to=["JSON", "CSV"],
        output_dir=str(tmp_path)
    )
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    assert "ExportTo" in script, "Expected 'ExportTo' parameter in script"
    assert "'JSON'" in script, "Expected 'JSON' in ExportTo"
    assert "'CSV'" in script, "Expected 'CSV' in ExportTo"


def test_build_script_verbose_present_when_true(tmp_path):
    """Test build_script includes Verbose when verbose=True."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        verbose=True,
        output_dir=str(tmp_path)
    )
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    assert "Verbose" in script, "Expected 'Verbose' parameter in script"
    assert "$true" in script, "Expected '$true' value for Verbose"


def test_build_script_verbose_absent_when_false(tmp_path):
    """Test build_script omits Verbose when verbose=False."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        provider="Microsoft365",
        auth_mode="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        verbose=False,  # Default
        output_dir=str(tmp_path)
    )
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    
    # Verbose = $true should not be in the script
    # (checking for the full parameter line with $true)
    assert "Verbose         = $true" not in script, "Did not expect 'Verbose = $true' when False"


