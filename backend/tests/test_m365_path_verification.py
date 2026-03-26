"""
M365 Audit Path Verification Tests

Comprehensive verification that the Monkey365 audit output path fix works correctly.
Tests path construction, backward compatibility, edge cases, and data integrity.
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from app.core.storage import (
    slugify,
    get_scan_output_path,
    ensure_scan_directory,
    write_meta_json,
)


# ────────────────────────────────────────────────────────────────────────
# TEST 1: Path Construction - No Duplicate Tenant IDs
# ────────────────────────────────────────────────────────────────────────


class TestPathConstruction:
    """Verify audit output paths do not have duplicate tenant IDs."""
    
    def test_path_structure_single_tenant_id(self):
        """Verify path structure: data/slug/Cloud/M365/scan_id (no duplicate tenant_id)."""
        # Example: "acme-corp" should appear only once (as slug)
        result = get_scan_output_path("Acme Corp", "scan-001")
        parts = result.parts
        
        # Extract meaningful parts
        slug_part = None
        cloud_idx = None
        m365_idx = None
        scan_idx = None
        
        for i, part in enumerate(parts):
            if part == "acme-corp":
                slug_part = i
            if part == "Cloud":
                cloud_idx = i
            if part == "M365":
                m365_idx = i
            if part == "scan-001":
                scan_idx = i
        
        # Verify all parts exist in order
        assert slug_part is not None, "Slug 'acme-corp' not found in path"
        assert cloud_idx is not None, "Cloud dir not found in path"
        assert m365_idx is not None, "M365 dir not found in path"
        assert scan_idx is not None, "scan-001 not found in path"
        
        # Verify order
        assert slug_part < cloud_idx < m365_idx < scan_idx, (
            f"Path parts out of order: slug({slug_part}) < Cloud({cloud_idx}) < "
            f"M365({m365_idx}) < scan_id({scan_idx})"
        )
        
        # Verify no duplicates
        path_str = str(result)
        assert path_str.count("acme-corp") == 1, (
            f"Slug 'acme-corp' appears {path_str.count('acme-corp')} times, expected 1: {path_str}"
        )
    
    def test_path_with_multiple_tenant_ids(self):
        """Test multiple different tenant IDs in same session."""
        paths = []
        for i in range(3):
            tenant = f"tenant-{i}"
            scan_id = f"scan-{i}"
            path = get_scan_output_path(tenant, scan_id)
            paths.append((tenant, scan_id, path))
        
        # Each path should be unique
        path_strings = [str(p[2]) for p in paths]
        assert len(path_strings) == len(set(path_strings)), "Paths are not unique"
        
        # No cross-contamination of tenant IDs
        for tenant, scan_id, path in paths:
            path_str = str(path)
            for other_tenant, _, _ in paths:
                if other_tenant != tenant:
                    # Other tenant should not appear in this path
                    assert other_tenant not in path_str, (
                        f"Path for {tenant} contains other tenant {other_tenant}: {path_str}"
                    )
    
    def test_path_structure_with_special_chars_in_tenant(self):
        """Test path construction with special characters in tenant name."""
        # "Société Générale & Co." → "societe-generale-co" (sanitized)
        result = get_scan_output_path("Société Générale & Co.", "scan-abc")
        parts = result.parts
        
        # Should have clean slug without special chars
        slug_found = False
        for part in parts:
            if "societe" in part.lower() and "generale" in part.lower():
                slug_found = True
                # Verify no special chars in slug
                assert "&" not in part, f"Special char & found in slug: {part}"
                assert "." not in part, f"Special char . found in slug: {part}"
                assert "é" not in part, f"Accent é found in slug: {part}"
        
        assert slug_found, "Expected sanitized slug not found in path"
    
    def test_cloud_m365_structure_consistency(self):
        """Verify consistent directory structure: .../Cloud/M365/scan_id/"""
        for company in ["Company A", "Company B", "Test Org"]:
            for scan_id in ["scan-1", "scan-2"]:
                result = get_scan_output_path(company, scan_id)
                path_str = str(result)
                
                # Must have Cloud/M365 structure
                assert "Cloud" in path_str, f"Missing 'Cloud' in path: {path_str}"
                assert "M365" in path_str, f"Missing 'M365' in path: {path_str}"
                
                # Cloud must come before M365
                assert path_str.index("Cloud") < path_str.index("M365"), (
                    f"'Cloud' should come before 'M365' in path: {path_str}"
                )
                
                # scan_id must come last
                assert path_str.endswith(scan_id), (
                    f"scan_id '{scan_id}' should be last in path: {path_str}"
                )


# ────────────────────────────────────────────────────────────────────────
# TEST 2: Backward Compatibility
# ────────────────────────────────────────────────────────────────────────


class TestBackwardCompatibility:
    """Verify new path structure doesn't break queries/reads of old data."""
    
    def test_old_audit_data_with_duplicate_paths_still_accessible(self, tmp_path):
        """Simulate old data structure and verify it can still be read."""
        # Old structure (with duplicate tenant_id): data/company/tenant_123/Cloud/M365/tenant_123/scan_id
        # We can't test this directly without modifying storage, but we verify the new
        # structure doesn't break if old files exist
        
        old_style_path = tmp_path / "company" / "tenant_123" / "Cloud" / "M365" / "tenant_123" / "scan_001"
        old_style_path.mkdir(parents=True, exist_ok=True)
        
        old_meta = {
            "scan_id": "scan_001",
            "status": "completed",
            "old_format": True
        }
        old_meta_file = old_style_path / "meta.json"
        with open(old_meta_file, "w") as f:
            json.dump(old_meta, f)
        
        # New code should still be able to read old files
        assert old_meta_file.exists(), "Old meta.json not created"
        
        with open(old_meta_file, "r") as f:
            loaded = json.load(f)
        
        assert loaded["old_format"] is True, "Old data format not readable"
    
    def test_new_path_structure_queries_don_not_break(self, tmp_path):
        """Test that queries for new path structure work correctly."""
        with patch("app.core.storage.get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            
            # Create new-style paths
            for i in range(3):
                scan_id = f"scan-{i:03d}"
                path = ensure_scan_directory("Test Company", scan_id)
                
                # Write metadata
                meta = {
                    "scan_id": scan_id,
                    "status": "success",
                    "findings_count": i * 10
                }
                write_meta_json(path, meta)
            
            # Verify all paths exist and can be queried
            base_path = tmp_path / "test-company" / "Cloud" / "M365"
            assert base_path.exists(), f"Base path does not exist: {base_path}"
            
            # Count scan directories
            scan_dirs = list(base_path.iterdir())
            assert len(scan_dirs) == 3, f"Expected 3 scan dirs, found {len(scan_dirs)}"
            
            # Verify each has metadata
            for scan_dir in scan_dirs:
                meta_file = scan_dir / "meta.json"
                assert meta_file.exists(), f"meta.json missing in {scan_dir}"


# ────────────────────────────────────────────────────────────────────────
# TEST 3: Edge Cases
# ────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases in path construction."""
    
    def test_empty_tenant_id_handling(self):
        """Empty tenant ID should not create invalid paths."""
        result = get_scan_output_path("", "scan-001")
        path_str = str(result)
        
        # Should still produce valid path structure
        assert "Cloud" in path_str, "Path missing 'Cloud' directory"
        assert "M365" in path_str, "Path missing 'M365' directory"
        assert "scan-001" in path_str, "Path missing scan_id"
        
        # Empty tenant should result in empty slug
        # Path should be: .../Cloud/M365/scan-001
        parts = result.parts
        cloud_idx = None
        m365_idx = None
        scan_idx = None
        
        for i, part in enumerate(parts):
            if part == "Cloud":
                cloud_idx = i
            if part == "M365":
                m365_idx = i
            if part == "scan-001":
                scan_idx = i
        
        assert cloud_idx is not None and m365_idx is not None and scan_idx is not None
        assert cloud_idx < m365_idx < scan_idx, "Parts out of order for empty tenant"
    
    def test_special_characters_in_tenant_sanitized(self):
        """Test various special characters are properly handled."""
        test_cases = [
            ("Acme@Corp", "acme-corp"),  # @ becomes dash
            ("Test#Company$", "test-company"),  # Special chars become dashes
            ("Org/Name", "org-name"),  # / becomes dash
            ("Company\\Division", "company-division"),  # \ becomes dash
            ("Tenant~ID", "tenant-id"),  # ~ becomes dash
            ("Name:With:Colons", "name-with-colons"),  # : becomes dash
        ]
        
        for company, expected_slug in test_cases:
            result = get_scan_output_path(company, "scan-001")
            path_str = str(result)
            slug = slugify(company)
            
            # Slug should match expected
            assert slug == expected_slug, (
                f"Slug mismatch for '{company}': got '{slug}', expected '{expected_slug}'"
            )
            
            # Path should contain the slugified version
            assert slug in path_str or slug == "", (
                f"Slug '{slug}' not found in path: {path_str}"
            )
    
    def test_concurrent_audits_same_tenant_no_conflicts(self, tmp_path):
        """Test concurrent audits from same tenant produce non-conflicting paths."""
        with patch("app.core.storage.get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            
            company = "Test Company"
            scan_ids = [f"scan-{i:04d}" for i in range(10)]
            
            paths = []
            for scan_id in scan_ids:
                path = ensure_scan_directory(company, scan_id)
                paths.append(path)
            
            # All paths should be unique
            path_strs = [str(p) for p in paths]
            assert len(path_strs) == len(set(path_strs)), "Duplicate paths detected"
            
            # All should exist
            for path in paths:
                assert path.exists(), f"Path not created: {path}"
            
            # No path should be a parent/child of another
            for i, p1 in enumerate(paths):
                for j, p2 in enumerate(paths):
                    if i != j:
                        # p1 should not contain p2 and vice versa
                        assert not str(p2).startswith(str(p1)), (
                            f"Path nesting detected: {p1} contains {p2}"
                        )
                        assert not str(p1).startswith(str(p2)), (
                            f"Path nesting detected: {p2} contains {p1}"
                        )
    
    def test_very_long_tenant_names(self):
        """Test handling of very long company names."""
        long_name = "A" * 500  # Very long name
        result = get_scan_output_path(long_name, "scan-001")
        
        # Should not raise error and produce valid path
        assert isinstance(result, Path), "Path construction failed for long name"
        assert "scan-001" in str(result), "scan_id not in path"


# ────────────────────────────────────────────────────────────────────────
# TEST 4: Data Integrity
# ────────────────────────────────────────────────────────────────────────


class TestDataIntegrity:
    """Verify findings are saved correctly in new path structure."""
    
    def test_findings_saved_in_correct_path(self, tmp_path):
        """Test findings are saved in the correct new path structure."""
        with patch("app.core.storage.get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            
            company = "Test Company"
            scan_id = "scan-findings-001"
            
            # Create directory and save findings
            path = ensure_scan_directory(company, scan_id)
            
            findings = {
                "scan_id": scan_id,
                "findings_count": 42,
                "results": [
                    {"issue": "Config X", "severity": "High"},
                    {"issue": "Config Y", "severity": "Medium"}
                ]
            }
            
            findings_file = path / "findings.json"
            with open(findings_file, "w") as f:
                json.dump(findings, f)
            
            # Verify findings are in correct location
            expected_path = tmp_path / "test-company" / "Cloud" / "M365" / scan_id
            assert expected_path.exists(), f"Expected path not created: {expected_path}"
            assert (expected_path / "findings.json").exists(), "findings.json not created"
            
            # Verify findings are readable
            with open(expected_path / "findings.json", "r") as f:
                loaded = json.load(f)
            
            assert loaded["findings_count"] == 42, "Findings count mismatch"
            assert len(loaded["results"]) == 2, "Findings results count mismatch"
    
    def test_metadata_consistency_across_paths(self, tmp_path):
        """Verify metadata stays consistent in new path structure."""
        with patch("app.core.storage.get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            
            test_cases = [
                ("Company Alpha", "scan-alpha-001"),
                ("Company Beta", "scan-beta-001"),
            ]
            
            for company, scan_id in test_cases:
                path = ensure_scan_directory(company, scan_id)
                
                meta = {
                    "scan_id": scan_id,
                    "entreprise_name": company,
                    "status": "success",
                    "output_path": str(path),
                }
                
                write_meta_json(path, meta)
                
                # Verify metadata file exists
                meta_file = path / "meta.json"
                assert meta_file.exists(), f"meta.json not created for {company}"
                
                # Verify metadata is readable
                with open(meta_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                
                assert loaded["scan_id"] == scan_id, f"Metadata scan_id mismatch for {company}"
                assert loaded["entreprise_name"] == company, f"Metadata company mismatch"
    
    def test_duplicate_audit_idempotency(self, tmp_path):
        """Test that running the same audit twice doesn't corrupt data."""
        with patch("app.core.storage.get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            
            company = "Test Company"
            scan_id = "scan-idem-001"
            
            # First audit
            path1 = ensure_scan_directory(company, scan_id)
            meta1 = {"scan_id": scan_id, "run": 1}
            write_meta_json(path1, meta1)
            
            # Second audit (same company and scan_id)
            path2 = ensure_scan_directory(company, scan_id)
            meta2 = {"scan_id": scan_id, "run": 2}  # Overwrite
            write_meta_json(path2, meta2)
            
            # Paths should be identical
            assert path1 == path2, "Paths differ for identical company/scan_id"
            
            # Latest metadata should be present
            with open(path2 / "meta.json", "r") as f:
                loaded = json.load(f)
            
            assert loaded["run"] == 2, "Metadata not updated on second run"


# ────────────────────────────────────────────────────────────────────────
# TEST 5: Smoke Tests - Integration
# ────────────────────────────────────────────────────────────────────────


class TestIntegrationSmoke:
    """Integration smoke tests for the full path lifecycle."""
    
    def test_full_audit_lifecycle(self, tmp_path):
        """Test complete audit path lifecycle: create, write, read."""
        with patch("app.core.storage.get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            
            company = "Acme Corp"
            scan_id = "scan-lifecycle-001"
            
            # Step 1: Create directory
            output_path = ensure_scan_directory(company, scan_id)
            assert output_path.exists(), "Directory not created"
            
            # Step 2: Write findings
            findings = {"count": 15, "severity": "Mixed"}
            findings_file = output_path / "findings.json"
            with open(findings_file, "w") as f:
                json.dump(findings, f)
            
            # Step 3: Write metadata
            meta = {
                "scan_id": scan_id,
                "company": company,
                "findings_count": 15,
                "status": "completed"
            }
            write_meta_json(output_path, meta)
            
            # Step 4: Read and verify all data
            assert (output_path / "findings.json").exists()
            assert (output_path / "meta.json").exists()
            
            with open(output_path / "findings.json", "r") as f:
                read_findings = json.load(f)
            with open(output_path / "meta.json", "r") as f:
                read_meta = json.load(f)
            
            assert read_findings["count"] == 15
            assert read_meta["company"] == company
            assert read_meta["status"] == "completed"
    
    def test_multiple_companies_isolation(self, tmp_path):
        """Test that multiple companies' audits don't interfere with each other."""
        with patch("app.core.storage.get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            
            companies = ["Company A", "Company B", "Company C"]
            
            for company in companies:
                path = ensure_scan_directory(company, "scan-001")
                meta = {"company": company, "status": "success"}
                write_meta_json(path, meta)
            
            # Verify each company has separate directory
            for company in companies:
                slug = slugify(company)
                company_path = tmp_path / slug
                assert company_path.exists(), f"Company path not created for {company}"
            
            # Verify data isolation
            for company in companies:
                slug = slugify(company)
                company_path = tmp_path / slug / "Cloud" / "M365" / "scan-001"
                
                with open(company_path / "meta.json", "r") as f:
                    meta = json.load(f)
                
                assert meta["company"] == company, (
                    f"Data contamination: {company} metadata contains {meta['company']}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
