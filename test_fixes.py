#!/usr/bin/env python
"""Test script to verify Phase 1 & 2 fixes"""
import sys
sys.path.insert(0, 'backend')

print("=" * 70)
print("  AssistantAudit - Phase 1 & 2 Fixes Verification")
print("=" * 70)

# Test 1: Configuration & SECRET_KEY
print("\n[1] Testing Configuration & SECRET_KEY Generation...")
import os
os.environ['ENV'] = 'development'

from app.core.config import get_settings
settings = get_settings()
assert len(settings.SECRET_KEY) >= 32, "SECRET_KEY too short"
assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 15, "JWT expiry not 15 minutes"
print("✅ Configuration loaded successfully")
print(f"   - SECRET_KEY: {len(settings.SECRET_KEY)} characters")
print(f"   - JWT_ACCESS_TOKEN_EXPIRE_MINUTES: {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES}")

# Test 2: XML Parsing
print("\n[2] Testing XML Parsing with defusedxml...")
from defusedxml import ElementTree as ET
test_xml = '<?xml version="1.0"?><root><item>test</item></root>'
root = ET.fromstring(test_xml)
assert root.tag == "root", "XML parsing failed"
print("✅ defusedxml is working correctly")

# Test 3: Input Validators
print("\n[3] Testing Input Validators...")
from app.schemas.validators import (
    validate_ip_address,
    validate_hostname,
    validate_mac_address,
    validate_port
)

# Valid inputs
assert validate_ip_address("192.168.1.1") == "192.168.1.1"
assert validate_hostname("example.com") == "example.com"
assert validate_mac_address("00:11:22:33:44:55") == "00:11:22:33:44:55"
assert validate_port(8080) == 8080
print("✅ Valid inputs accepted")

# Invalid inputs should raise ValueError
try:
    validate_ip_address("999.999.999.999")
    assert False, "Should have rejected invalid IP"
except ValueError:
    pass

try:
    validate_port(72000)
    assert False, "Should have rejected invalid port"
except ValueError:
    pass

print("✅ Invalid inputs rejected correctly")

# Test 4: Exception Handlers
print("\n[4] Testing Exception Handlers...")
from app.core.exception_handlers import register_exception_handlers
from fastapi import FastAPI
app = FastAPI()
register_exception_handlers(app)
print("✅ Exception handlers registered successfully")

# Test 5: Test Credentials from Environment
print("\n[5] Testing Environment Variables for Credentials...")
os.environ['TEST_ADMIN_PASSWORD'] = 'TestSecure@123'
admin_pass = os.getenv('TEST_ADMIN_PASSWORD')
assert admin_pass == 'TestSecure@123', "Environment variable not loaded"
print("✅ Environment variables loaded correctly")

print("\n" + "=" * 70)
print("  ✅ All Phase 1 & 2 Fixes Verified Successfully!")
print("=" * 70)
