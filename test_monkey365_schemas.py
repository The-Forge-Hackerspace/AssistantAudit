#!/usr/bin/env python3
"""
QA Test Suite for Monkey365 Schemas
Task 5: Monkey365 Pydantic Schemas
"""
import sys
from datetime import datetime
from pydantic import ValidationError

# Add backend to path
sys.path.insert(0, '/mnt/e/AssistantAudit/backend')

from app.schemas.scan import (
    Monkey365ConfigSchema,
    Monkey365ScanCreate,
    Monkey365ScanResultSummary,
    Monkey365ScanResultRead
)


def test_scenario_1():
    """Scenario 1: Happy path - Valid Monkey365ScanCreate validates successfully"""
    print("\n" + "="*70)
    print("QA SCENARIO 1: Happy Path - Valid Monkey365ScanCreate")
    print("="*70)
    
    try:
        config = Monkey365ConfigSchema(
            provider="Microsoft365",
            auth_method="client_credentials",
            tenant_id="12345678-1234-1234-1234-123456789abc",
            client_id="87654321-4321-4321-4321-cba987654321",
            client_secret="my_secret_key",
            collect=["AzureAD", "M365"],
            prompt_behavior="Auto",
            export_to=["CSV"],
            scan_sites=["https://example.com", "https://test.org/path"]
        )
        print(f"✓ Monkey365ConfigSchema created successfully")
        print(f"  - collect: {config.collect}")
        print(f"  - prompt_behavior: {config.prompt_behavior}")
        print(f"  - export_to: {config.export_to} (JSON auto-appended: {'JSON' in config.export_to})")
        print(f"  - scan_sites: {config.scan_sites}")
        
        scan_create = Monkey365ScanCreate(
            entreprise_id=1,
            config=config
        )
        print(f"✓ Monkey365ScanCreate created successfully")
        print(f"  - entreprise_id: {scan_create.entreprise_id}")
        print(f"  - config valid: {scan_create.config is not None}")
        
        result_summary = Monkey365ScanResultSummary(
            id=1,
            entreprise_id=1,
            status="success",
            scan_id="scan_001",
            entreprise_slug="acme",
            findings_count=42,
            created_at=datetime.now(),
            completed_at=datetime.now(),
            duration_seconds=120
        )
        print(f"✓ Monkey365ScanResultSummary created successfully")
        
        result_read = Monkey365ScanResultRead(
            id=1,
            entreprise_id=1,
            status="success",
            scan_id="scan_001",
            config_snapshot={"tenant": "123"},
            output_path="/tmp/results",
            entreprise_slug="acme",
            findings_count=42,
            error_message=None,
            created_at=datetime.now(),
            completed_at=datetime.now(),
            duration_seconds=120
        )
        print(f"✓ Monkey365ScanResultRead created successfully")
        print(f"  - config_snapshot: {result_read.config_snapshot}")
        print(f"  - output_path: {result_read.output_path}")
        
        print("\n✅ SCENARIO 1 PASSED: All schemas validate with valid data")
        return True
    except Exception as e:
        print(f"\n❌ SCENARIO 1 FAILED: {type(e).__name__}: {e}")
        return False


def test_scenario_2():
    """Scenario 2: Rejection - Invalid values rejected with ValidationError"""
    print("\n" + "="*70)
    print("QA SCENARIO 2: Rejection - Invalid Values")
    print("="*70)
    
    failures = []
    
    # Test 1: Invalid collect value
    print("\nTest 2.1: Invalid collect value (with special chars)")
    try:
        config = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            collect=["Valid", "Invalid@Name"]  # @ is invalid
        )
        failures.append("Should reject collect with '@' character")
        print("  ❌ Did not reject invalid collect")
    except ValidationError as e:
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    # Test 2: Invalid prompt_behavior value
    print("\nTest 2.2: Invalid prompt_behavior value")
    try:
        config = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            prompt_behavior="InvalidValue"
        )
        failures.append("Should reject invalid prompt_behavior")
        print("  ❌ Did not reject invalid prompt_behavior")
    except ValidationError as e:
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    # Test 3: Invalid export_to value
    print("\nTest 2.3: Invalid export_to format")
    try:
        config = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            export_to=["INVALID_FORMAT"]
        )
        failures.append("Should reject invalid export_to format")
        print("  ❌ Did not reject invalid export_to format")
    except ValidationError as e:
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    # Test 4: Invalid scan_sites (not https://)
    print("\nTest 2.4: Invalid scan_sites (not HTTPS)")
    try:
        config = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            scan_sites=["http://example.com"]  # http, not https
        )
        failures.append("Should reject non-HTTPS URLs")
        print("  ❌ Did not reject non-HTTPS URL")
    except ValidationError as e:
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    # Test 5: Invalid scan_sites (malformed)
    print("\nTest 2.5: Invalid scan_sites (malformed)")
    try:
        config = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            scan_sites=["https://example.com/path with spaces"]
        )
        failures.append("Should reject URLs with spaces")
        print("  ❌ Did not reject URL with spaces")
    except ValidationError as e:
        print(f"  ✓ Correctly rejected: {e.errors()[0]['msg']}")
    
    if failures:
        print(f"\n❌ SCENARIO 2 FAILED: {len(failures)} validation checks failed")
        for f in failures:
            print(f"  - {f}")
        return False
    else:
        print("\n✅ SCENARIO 2 PASSED: All invalid values correctly rejected")
        return True


def test_scenario_3():
    """Scenario 3: JSON Auto-Include - export_to auto-includes JSON when missing"""
    print("\n" + "="*70)
    print("QA SCENARIO 3: JSON Auto-Include")
    print("="*70)
    
    try:
        # Test without JSON in list
        config_without_json = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            export_to=["CSV", "HTML"]
        )
        print(f"Input export_to: ['CSV', 'HTML']")
        print(f"Output export_to: {config_without_json.export_to}")
        
        if "JSON" in config_without_json.export_to:
            print("✓ JSON was auto-appended")
        else:
            print("❌ JSON was NOT auto-appended")
            return False
        
        # Test with JSON already present
        config_with_json = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            export_to=["JSON", "CSV"]
        )
        print(f"\nInput export_to: ['JSON', 'CSV']")
        print(f"Output export_to: {config_with_json.export_to}")
        
        json_count = config_with_json.export_to.count("JSON")
        if json_count == 1:
            print("✓ JSON appears exactly once (no duplication)")
        else:
            print(f"❌ JSON appears {json_count} times (expected 1)")
            return False
        
        # Test with empty list
        config_empty = Monkey365ConfigSchema(
            tenant_id="123",
            client_id="456",
            client_secret="secret",
            export_to=[]
        )
        print(f"\nInput export_to: []")
        print(f"Output export_to: {config_empty.export_to}")
        
        if config_empty.export_to == ["JSON"]:
            print("✓ JSON was added to empty list")
        else:
            print(f"❌ Expected ['JSON'], got {config_empty.export_to}")
            return False
        
        print("\n✅ SCENARIO 3 PASSED: JSON auto-include works correctly")
        return True
    except Exception as e:
        print(f"\n❌ SCENARIO 3 FAILED: {type(e).__name__}: {e}")
        return False


def main():
    """Run all QA scenarios"""
    print("\n" + "="*70)
    print("MONKEY365 SCHEMAS - QA TEST SUITE")
    print("="*70)
    
    results = {
        "scenario_1": test_scenario_1(),
        "scenario_2": test_scenario_2(),
        "scenario_3": test_scenario_3(),
    }
    
    print("\n" + "="*70)
    print("QA SUMMARY")
    print("="*70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    for scenario, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {scenario.replace('_', ' ').upper()}")
    
    if passed == total:
        print("\n🎉 ALL SCENARIOS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} scenario(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
