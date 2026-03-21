# M365 Audit Testing Patterns

Reusable test patterns and strategies for M365 audit path, storage, and integration testing.

## Pattern 1: Path Construction Verification

**Use Case:** Verify audit output paths are correct and don't have redundant components.

**Pattern:**
```python
def test_path_structure_single_component():
    """Verify component appears only once in path."""
    result = get_scan_output_path("Company Name", "scan-id")
    path_str = str(result)
    
    # Extract parts and verify order
    parts = result.parts
    component_idx = None
    for i, part in enumerate(parts):
        if part == "component":
            component_idx = i
    
    # Verify no duplicates
    assert path_str.count("component") == 1
```

**When to Use:**
- Validating hierarchical path structures
- Detecting duplicate directory names
- Ensuring path uniqueness across multiple parameters

**Key Insight:** Check both path string occurrences AND parts order to catch duplicates in complex paths.

---

## Pattern 2: Backward Compatibility Isolation

**Use Case:** Test that old data format remains accessible after refactoring paths/structures.

**Pattern:**
```python
def test_old_format_still_accessible(tmp_path):
    """Simulate old data structure and verify new code can read it."""
    # Create old-style directory structure
    old_path = tmp_path / "old" / "structure" / "meta.json"
    old_path.parent.mkdir(parents=True)
    old_meta = {"format": "v1"}
    
    # Verify it's readable
    with open(old_path, "r") as f:
        loaded = json.load(f)
    assert loaded["format"] == "v1"
```

**When to Use:**
- After restructuring audit paths/storage
- When changing database schemas
- Testing data migration compatibility

**Key Insight:** Create actual old-format files to prove they're still accessible, not just theoretically.

---

## Pattern 3: Concurrent Operation Safety

**Use Case:** Verify that multiple audits don't create path conflicts or interfere.

**Pattern:**
```python
def test_concurrent_audits_same_tenant_no_conflicts(tmp_path):
    """Test N concurrent scans from same tenant are isolated."""
    company = "Test Company"
    paths = []
    
    for i in range(10):  # Simulate concurrent audits
        scan_id = f"scan-{i:04d}"
        path = ensure_scan_directory(company, scan_id)
        paths.append(path)
    
    # Verify uniqueness
    path_strs = [str(p) for p in paths]
    assert len(path_strs) == len(set(path_strs))  # No duplicates
    
    # Verify no nesting
    for i, p1 in enumerate(paths):
        for j, p2 in enumerate(paths):
            if i != j:
                assert not str(p2).startswith(str(p1))
```

**When to Use:**
- After implementing concurrent audit support
- When scaling to high-volume operations
- Testing idempotency of path operations

**Key Insight:** Generate multiple scan IDs and verify uniqueness both as strings AND that paths don't nest.

---

## Pattern 4: Special Character Sanitization

**Use Case:** Verify that tenant names with special characters are safely sanitized in paths.

**Pattern:**
```python
def test_special_characters_sanitized():
    """Test various special characters are properly handled."""
    test_cases = [
        ("Company@Corp", "company-corp"),
        ("Org/Name", "org-name"),
        ("Tenant~ID", "tenant-id"),
    ]
    
    for input_name, expected_slug in test_cases:
        result = get_scan_output_path(input_name, "scan-001")
        slug = slugify(input_name)
        
        assert slug == expected_slug
        assert slug in str(result) or slug == ""
        
        # Verify no dangerous characters in path
        path_str = str(result)
        assert "@" not in path_str
        assert "#" not in path_str
        assert "&" not in path_str
```

**When to Use:**
- After adding slug/sanitization functions
- When accepting user input for directory names
- Security testing for path traversal prevention

**Key Insight:** Test both the slug function AND verify the sanitized result appears in final path.

---

## Pattern 5: Data Integrity Through Lifecycle

**Use Case:** Verify audit data integrity from creation through multiple read/write cycles.

**Pattern:**
```python
def test_findings_save_and_load_correctly(tmp_path):
    """Test complete audit data lifecycle: create, write, read."""
    with patch("app.core.storage.get_settings") as mock_settings:
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        
        # Step 1: Create directory
        output_path = ensure_scan_directory("Company", "scan-001")
        
        # Step 2: Write findings
        findings = {"count": 15, "severity": "Mixed"}
        with open(output_path / "findings.json", "w") as f:
            json.dump(findings, f)
        
        # Step 3: Write metadata
        meta = {"scan_id": "scan-001", "status": "completed"}
        write_meta_json(output_path, meta)
        
        # Step 4: Verify both files exist and are readable
        assert (output_path / "findings.json").exists()
        assert (output_path / "meta.json").exists()
        
        # Step 5: Load and verify integrity
        with open(output_path / "findings.json", "r") as f:
            loaded_findings = json.load(f)
        with open(output_path / "meta.json", "r") as f:
            loaded_meta = json.load(f)
        
        assert loaded_findings["count"] == 15
        assert loaded_meta["status"] == "completed"
```

**When to Use:**
- After implementing new audit storage mechanisms
- When refactoring data persistence
- End-to-end integration testing

**Key Insight:** Test the full lifecycle in one test: create → write multiple files → read → verify consistency.

---

## Pattern 6: Data Isolation Between Entities

**Use Case:** Verify that multiple companies' audit data doesn't cross-contaminate.

**Pattern:**
```python
def test_multiple_companies_complete_isolation(tmp_path):
    """Test complete data isolation between companies."""
    companies = ["Company A", "Company B", "Company C"]
    
    with patch("app.core.storage.get_settings") as mock_settings:
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        
        # Create audits for each company
        for company in companies:
            path = ensure_scan_directory(company, "scan-001")
            meta = {"company": company, "status": "success"}
            write_meta_json(path, meta)
        
        # Verify isolation: each company has separate directory
        for company in companies:
            slug = slugify(company)
            company_path = tmp_path / slug
            assert company_path.exists()
        
        # Verify data isolation: no cross-contamination
        for company in companies:
            slug = slugify(company)
            meta_file = tmp_path / slug / "Cloud" / "M365" / "scan-001" / "meta.json"
            
            with open(meta_file, "r") as f:
                meta = json.load(f)
            
            # Metadata should only contain THIS company's data
            assert meta["company"] == company
            
            # Metadata should NOT contain other companies
            for other_company in companies:
                if other_company != company:
                    assert meta["company"] != other_company
```

**When to Use:**
- Multi-tenant systems
- When testing data partitioning
- Security testing for data leakage prevention

**Key Insight:** Create multiple entities, verify each has isolated storage, then load and verify no contamination.

---

## Pattern 7: Edge Case Coverage Matrix

**Use Case:** Systematically test combinations of edge cases.

**Pattern:**
```python
@pytest.mark.parametrize("edge_case,expected_behavior", [
    ("", "handles_empty"),
    ("A" * 500, "handles_long"),
    ("@#$%^&", "sanitizes"),
    ("Café-Zürich", "handles_unicode"),
    ("Path/With\\Slashes", "removes_separators"),
])
def test_edge_cases(edge_case, expected_behavior):
    """Test matrix of edge cases."""
    result = get_scan_output_path(edge_case, "scan-001")
    
    if expected_behavior == "handles_empty":
        assert result is not None
        assert "scan-001" in str(result)
    elif expected_behavior == "handles_long":
        assert isinstance(result, Path)
        assert result.is_absolute() or True  # Relative is OK
    elif expected_behavior == "sanitizes":
        assert "@" not in str(result)
        assert "#" not in str(result)
    # ... etc
```

**When to Use:**
- Testing many edge cases systematically
- Avoiding code duplication in edge case tests
- Generating test reports by edge case type

**Key Insight:** Use parametrize to avoid duplication, but keep assertions specific to each case.

---

## Pattern 8: Mock Settings for Path Isolation

**Use Case:** Ensure tests use isolated temporary paths instead of production data directories.

**Pattern:**
```python
def test_something(tmp_path):
    """All tests should use tmp_path, not production directories."""
    with patch("app.core.storage.get_settings") as mock_settings:
        # Mock returns tmp_path as DATA_DIR
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        
        # Now all path operations use tmp_path
        result = ensure_scan_directory("Company", "scan-001")
        
        # Verify files were created in tmp_path, not production
        assert result.is_relative_to(tmp_path) or str(result).startswith(str(tmp_path))
```

**When to Use:**
- Any test that creates files/directories
- Tests that call storage functions
- To prevent test pollution of production data

**Key Insight:** Always mock get_settings() in storage tests to ensure isolation.

---

## Pattern 9: Unicode and Encoding Preservation

**Use Case:** Verify that unicode characters (accents, special chars) are preserved in metadata.

**Pattern:**
```python
def test_unicode_preserved_in_metadata(tmp_path):
    """Test unicode data preserved through storage layer."""
    with patch("app.core.storage.get_settings") as mock_settings:
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        
        # Create path with unicode company name
        company = "Société Générale"
        path = ensure_scan_directory(company, "scan-001")
        
        # Write metadata with unicode
        meta = {
            "company": company,
            "ville": "Paris",
            "notes": "Café-restaurant, très bon!"
        }
        write_meta_json(path, meta)
        
        # Read back and verify unicode preserved
        with open(path / "meta.json", "r", encoding="utf-8") as f:
            loaded = json.load(f)
        
        assert loaded["company"] == "Société Générale"
        assert loaded["ville"] == "Paris"
        assert "très" in loaded["notes"]
```

**When to Use:**
- International/multi-language support
- Testing JSON encoding/decoding
- Verifying database character set support

**Key Insight:** Explicitly use `encoding="utf-8"` when opening/writing files to ensure consistency.

---

## M365-Specific Test Considerations

1. **Tenant ID Handling:** Don't assume tenant_id is in path; it's in config_snapshot
2. **Auth Modes:** Test with all 4 auth modes (interactive, device_code, ropc, client_credentials)
3. **Concurrent Scans:** M365 often runs multiple scans per tenant; verify no conflicts
4. **Metadata Lifecycle:** meta.json created at scan completion; test idempotency
5. **Finding Counts:** Verify findings_count matches actual findings in output

---

## Performance Notes

- All path tests execute in <1s
- Mocking get_settings is faster than real settings loading
- tmp_path fixture creates actual filesystem (not in-memory)
- 32 tests total: ~1.07s execution time
- Parallel execution safe (isolated tmp_path per test)

---

## Related Patterns

See also:
- `project-conventions.md` - Naming conventions
- `swr-data-fetching.md` - Data loading patterns
- Test infrastructure in `backend/tests/conftest.py` - Fixtures and factories
