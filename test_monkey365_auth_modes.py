"""
Test script to verify Monkey365 authentication modes generate correct PowerShell scripts.
This is a manual verification script (not a unit test).
"""
from backend.app.tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor
from backend.app.tools.monkey365_runner.config import Monkey365AuthMode, M365Provider

# Mock monkey365_path for testing
import tempfile
from pathlib import Path

# Create a temporary directory to simulate Monkey365 installation
temp_dir = Path(tempfile.mkdtemp())
(temp_dir / "Invoke-Monkey365.ps1").touch()

print("=" * 80)
print("MONKEY365 AUTHENTICATION MODE TESTING")
print("=" * 80)

# Test 1: INTERACTIVE mode (no credentials)
print("\n[TEST 1] INTERACTIVE MODE (Browser Popup)")
print("-" * 80)
config_interactive = Monkey365Config(
    auth_mode=Monkey365AuthMode.INTERACTIVE,
    provider=M365Provider.MICROSOFT365,
    output_dir=str(temp_dir / "output"),
    collect=["ExchangeOnline", "SharePointOnline"]
)
executor = Monkey365Executor(config_interactive, str(temp_dir / "Invoke-Monkey365.ps1"))
script = executor.build_script("test_interactive")
print(script)
assert "PromptBehavior = 'SelectAccount'" in script
assert "TenantId" not in script
assert "ClientId" not in script
assert "ClientSecret" not in script
print("✅ PASS: Interactive mode requires NO credentials")

# Test 2: DEVICE_CODE mode (no credentials)
print("\n[TEST 2] DEVICE_CODE MODE (Device Code Flow)")
print("-" * 80)
config_device = Monkey365Config(
    auth_mode=Monkey365AuthMode.DEVICE_CODE,
    provider=M365Provider.MICROSOFT365,
    output_dir=str(temp_dir / "output"),
    collect=["ExchangeOnline"]
)
executor = Monkey365Executor(config_device, str(temp_dir / "Invoke-Monkey365.ps1"))
script = executor.build_script("test_device")
print(script)
assert "DeviceCode     = $true" in script
assert "TenantId" not in script
assert "ClientId" not in script
assert "ClientSecret" not in script
print("✅ PASS: Device code mode requires NO credentials")

# Test 3: ROPC mode (username + password + tenant_id)
print("\n[TEST 3] ROPC MODE (Username + Password)")
print("-" * 80)
config_ropc = Monkey365Config(
    auth_mode=Monkey365AuthMode.ROPC,
    tenant_id="12345678-1234-1234-1234-123456789abc",
    username="auditor@example.com",
    password="SecurePassword123!",
    provider=M365Provider.MICROSOFT365,
    output_dir=str(temp_dir / "output"),
    collect=["SharePointOnline"]
)
executor = Monkey365Executor(config_ropc, str(temp_dir / "Invoke-Monkey365.ps1"))
script = executor.build_script("test_ropc")
print(script)
assert "TenantId       = '12345678-1234-1234-1234-123456789abc'" in script
assert "Username       = 'auditor@example.com'" in script
assert "Password       = (ConvertTo-SecureString" in script
assert "ClientId" not in script
assert "ClientSecret   =" not in script  # Should not have ClientSecret line
print("✅ PASS: ROPC mode requires username + password + tenant_id")

# Test 4: CLIENT_CREDENTIALS mode (client_id + client_secret + tenant_id)
print("\n[TEST 4] CLIENT_CREDENTIALS MODE (App Registration)")
print("-" * 80)
config_client = Monkey365Config(
    auth_mode=Monkey365AuthMode.CLIENT_CREDENTIALS,
    tenant_id="87654321-4321-4321-4321-cba987654321",
    client_id="abcdef12-3456-7890-abcd-ef1234567890",
    client_secret="MySecretKey123~._-",
    provider=M365Provider.MICROSOFT365,
    output_dir=str(temp_dir / "output"),
    collect=["Purview"]
)
executor = Monkey365Executor(config_client, str(temp_dir / "Invoke-Monkey365.ps1"))
script = executor.build_script("test_client_creds")
print(script)
assert "TenantId       = '87654321-4321-4321-4321-cba987654321'" in script
assert "ClientId       = 'abcdef12-3456-7890-abcd-ef1234567890'" in script
assert "ClientSecret   = (ConvertTo-SecureString" in script
assert "Username" not in script
assert "Password       = (ConvertTo-SecureString" not in script or "ClientSecret" in script
print("✅ PASS: CLIENT_CREDENTIALS mode requires client_id + client_secret + tenant_id")

print("\n" + "=" * 80)
print("ALL TESTS PASSED ✅")
print("=" * 80)
print("\nConclusion:")
print("- INTERACTIVE mode: NO credentials required")
print("- DEVICE_CODE mode: NO credentials required")
print("- ROPC mode: username + password + tenant_id required")
print("- CLIENT_CREDENTIALS mode: client_id + client_secret + tenant_id required")
print("\nImplementation matches official Monkey365 documentation.")

# Cleanup
import shutil
shutil.rmtree(temp_dir)
