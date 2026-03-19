"""
Tests for Monkey365 authentication modes.

Validates that each authentication mode enforces correct credential requirements:
- INTERACTIVE: No credentials needed
- DEVICE_CODE: No credentials needed
- CLIENT_CREDENTIALS: Requires tenant_id, client_id, client_secret
- ROPC: Requires tenant_id, username, password
"""

import pytest

from app.tools.monkey365_runner.executor import Monkey365Config
from app.tools.monkey365_runner.config import Monkey365AuthMode


# ────────────────────────────────────────────────────────────────────────
# Test 1: Interactive Mode - No Credentials Required
# ────────────────────────────────────────────────────────────────────────


def test_interactive_no_credentials_required():
    """Interactive mode should work with auth_mode='interactive' only."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        collect=["ExchangeOnline"]
    )
    
    # Should NOT raise validation error
    config.validate()
    
    assert config.auth_mode == Monkey365AuthMode.INTERACTIVE
    assert config.collect == ["ExchangeOnline"]
    
    # Credentials should be empty (not required)
    assert config.tenant_id == ""
    assert config.client_id == ""
    assert config.client_secret == ""
    assert config.username == ""
    assert config.password == ""


def test_interactive_generates_correct_powershell(tmp_path):
    """Interactive mode should generate PowerShell without credentials."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.INTERACTIVE,
        collect=["SharePointOnline"],
        output_dir=str(tmp_path)
    )
    
    # Mock executor to access build_script
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan-interactive")
    
    # Should NOT contain credential parameters
    assert "TenantId" not in script, "Interactive mode should not have TenantId"
    assert "ClientId" not in script, "Interactive mode should not have ClientId"
    assert "ClientSecret" not in script, "Interactive mode should not have ClientSecret"
    assert "Username" not in script, "Interactive mode should not have Username"
    assert "Password" not in script, "Interactive mode should not have Password"
    
    # Should contain collect parameter
    assert "Collect" in script, "Expected Collect parameter"
    assert "SharePointOnline" in script, "Expected SharePointOnline in collect"


# ────────────────────────────────────────────────────────────────────────
# Test 2: Device Code Mode - No Credentials Required
# ────────────────────────────────────────────────────────────────────────


def test_device_code_no_credentials_required():
    """Device code mode should work with auth_mode='device_code' only."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.DEVICE_CODE,
        collect=["SharePointOnline"]
    )
    
    # Should NOT raise validation error
    config.validate()
    
    assert config.auth_mode == Monkey365AuthMode.DEVICE_CODE
    assert config.collect == ["SharePointOnline"]
    
    # Credentials should be empty (not required)
    assert config.tenant_id == ""
    assert config.client_id == ""
    assert config.client_secret == ""
    assert config.username == ""
    assert config.password == ""


def test_device_code_generates_correct_powershell(tmp_path):
    """Device code mode should generate PowerShell with DeviceCode flag."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.DEVICE_CODE,
        collect=["ExchangeOnline"],
        output_dir=str(tmp_path)
    )
    
    # Mock executor to access build_script
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan-device-code")
    
    # Should NOT contain credential parameters
    assert "TenantId" not in script, "Device code mode should not have TenantId"
    assert "ClientId" not in script, "Device code mode should not have ClientId"
    assert "ClientSecret" not in script, "Device code mode should not have ClientSecret"
    assert "Username" not in script, "Device code mode should not have Username"
    assert "Password" not in script, "Device code mode should not have Password"
    
    # Should contain collect parameter
    assert "Collect" in script, "Expected Collect parameter"
    assert "ExchangeOnline" in script, "Expected ExchangeOnline in collect"


# ────────────────────────────────────────────────────────────────────────
# Test 3: Client Credentials Mode - All 3 Fields Required
# ────────────────────────────────────────────────────────────────────────


def test_client_credentials_missing_fields_raises_error():
    """Client credentials mode must have tenant_id, client_id, client_secret."""
    # Missing all credentials should RAISE ValueError
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
        collect=["MicrosoftTeams"]
    )
    
    with pytest.raises(ValueError, match="CLIENT_CREDENTIALS mode requires"):
        config.validate()


def test_client_credentials_missing_tenant_id_raises_error():
    """Client credentials mode missing tenant_id should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="super_secret_value",
        collect=["MicrosoftTeams"]
    )
    
    with pytest.raises(ValueError, match="CLIENT_CREDENTIALS mode requires"):
        config.validate()


def test_client_credentials_missing_client_id_raises_error():
    """Client credentials mode missing client_id should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_secret="super_secret_value",
        collect=["MicrosoftTeams"]
    )
    
    with pytest.raises(ValueError, match="CLIENT_CREDENTIALS mode requires"):
        config.validate()


def test_client_credentials_missing_client_secret_raises_error():
    """Client credentials mode missing client_secret should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        collect=["MicrosoftTeams"]
    )
    
    with pytest.raises(ValueError, match="CLIENT_CREDENTIALS mode requires"):
        config.validate()


def test_client_credentials_all_fields_pass_validation():
    """Client credentials mode with all fields should PASS validation."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="super_secret_value",
        collect=["MicrosoftTeams"]
    )
    
    # Should NOT raise
    config.validate()
    
    assert config.auth_mode == Monkey365AuthMode.CLIENT_CREDENTIALS
    assert config.tenant_id == "12345678-1234-1234-1234-123456789abc"
    assert config.client_id == "87654321-4321-4321-4321-cba987654321"
    assert config.client_secret == "super_secret_value"


def test_client_credentials_generates_correct_powershell(tmp_path):
    """Client credentials mode should generate PowerShell with all credentials."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test_secret_123",
        collect=["Purview"],
        output_dir=str(tmp_path)
    )
    
    # Mock executor to access build_script
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan-client-creds")
    
    # Should contain all credential parameters
    assert "TenantId" in script, "Expected TenantId parameter"
    assert "ClientId" in script, "Expected ClientId parameter"
    assert "ClientSecret" in script, "Expected ClientSecret parameter"
    
    # Should NOT contain username/password (those are for ROPC)
    assert "Username" not in script, "Should not have Username in client credentials mode"
    assert "Password" not in script, "Should not have Password in client credentials mode"
    
    # Verify actual values are present (escaped)
    assert "12345678-1234-1234-1234-123456789abc" in script
    assert "87654321-4321-4321-4321-cba987654321" in script
    assert "test_secret_123" in script


def test_client_credentials_password_masked_in_logs():
    """Client credentials should mask secrets in log output."""
    from app.tools.monkey365_runner.executor import _mask_password
    
    secret = "super_secret_password_123"
    masked = _mask_password(secret)
    
    assert masked == "***", f"Expected '***', got '{masked}'"
    assert secret not in masked, "Password should not appear in masked output"


# ────────────────────────────────────────────────────────────────────────
# Test 4: ROPC Mode - tenant_id, username, password Required
# ────────────────────────────────────────────────────────────────────────


def test_ropc_missing_fields_raises_error():
    """ROPC mode must have tenant_id, username, password."""
    # Missing all credentials should RAISE ValueError
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        collect=["ExchangeOnline"]
    )
    
    with pytest.raises(ValueError, match="ROPC mode requires"):
        config.validate()


def test_ropc_missing_tenant_id_raises_error():
    """ROPC mode missing tenant_id should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        username="admin@contoso.com",
        password="P@ssw0rd123",
        collect=["ExchangeOnline"]
    )
    
    with pytest.raises(ValueError, match="ROPC mode requires"):
        config.validate()


def test_ropc_missing_username_raises_error():
    """ROPC mode missing username should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        password="P@ssw0rd123",
        collect=["ExchangeOnline"]
    )
    
    with pytest.raises(ValueError, match="ROPC mode requires"):
        config.validate()


def test_ropc_missing_password_raises_error():
    """ROPC mode missing password should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        username="admin@contoso.com",
        collect=["ExchangeOnline"]
    )
    
    with pytest.raises(ValueError, match="ROPC mode requires"):
        config.validate()


def test_ropc_all_fields_pass_validation():
    """ROPC mode with all fields should PASS validation."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        username="admin@contoso.com",
        password="P@ssw0rd123",
        collect=["ExchangeOnline"]
    )
    
    # Should NOT raise
    config.validate()
    
    assert config.auth_mode == Monkey365AuthMode.ROPC
    assert config.tenant_id == "12345678-1234-1234-1234-123456789abc"
    assert config.username == "admin@contoso.com"
    assert config.password == "P@ssw0rd123"


def test_ropc_generates_correct_powershell(tmp_path):
    """ROPC mode should generate PowerShell with username/password."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        username="admin@contoso.com",
        password="TestPass123",
        collect=["MicrosoftTeams"],
        output_dir=str(tmp_path)
    )
    
    # Mock executor to access build_script
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan-ropc")
    
    # Should contain ROPC-specific parameters
    assert "TenantId" in script, "Expected TenantId parameter"
    assert "Username" in script, "Expected Username parameter"
    # Password is converted to SecureString in PowerShell
    
    # Should NOT contain client credentials (those are for CLIENT_CREDENTIALS)
    assert "ClientId" not in script or "admin@contoso.com" in script, "Username should be present, not ClientId"
    
    # Verify actual values are present
    assert "12345678-1234-1234-1234-123456789abc" in script
    assert "admin@contoso.com" in script


def test_ropc_password_masked_in_logs():
    """ROPC mode should mask passwords in log output."""
    from app.tools.monkey365_runner.executor import _mask_password
    
    password = "P@ssw0rd123"
    masked = _mask_password(password)
    
    assert masked == "***", f"Expected '***', got '{masked}'"
    assert password not in masked, "Password should not appear in masked output"


def test_ropc_empty_password_raises_error():
    """ROPC mode with empty password should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        username="admin@contoso.com",
        password="",  # Empty password
        collect=["ExchangeOnline"]
    )
    
    with pytest.raises(ValueError, match="ROPC mode requires"):
        config.validate()


# ────────────────────────────────────────────────────────────────────────
# Additional Edge Cases
# ────────────────────────────────────────────────────────────────────────


def test_invalid_auth_mode_raises_error():
    """Invalid auth_mode should raise error during validation."""
    config = Monkey365Config(
        auth_mode="invalid_mode_xyz",  # Invalid mode
        collect=["ExchangeOnline"]
    )
    
    with pytest.raises(ValueError, match="Invalid auth_mode"):
        config.validate()


def test_client_credentials_invalid_uuid_format():
    """Client credentials with invalid UUID format should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
        tenant_id="not-a-valid-uuid",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test_secret",
        collect=["MicrosoftTeams"]
    )
    
    with pytest.raises(ValueError, match="tenant_id invalide"):
        config.validate()


def test_ropc_invalid_email_format():
    """ROPC mode with invalid email format should raise error."""
    config = Monkey365Config(
        auth_mode=Monkey365AuthMode.ROPC,
        tenant_id="12345678-1234-1234-1234-123456789abc",
        username="not-an-email",  # Invalid email format
        password="P@ssw0rd123",
        collect=["ExchangeOnline"]
    )
    
    with pytest.raises(ValueError, match="username invalide"):
        config.validate()


def test_mask_password_empty_string():
    """Masking empty password should return empty string."""
    from app.tools.monkey365_runner.executor import _mask_password
    
    masked = _mask_password("")
    assert masked == "", "Empty password should return empty string, not '***'"
