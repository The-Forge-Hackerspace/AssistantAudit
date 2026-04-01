"""
Tests for Monkey365 storage utilities.

Covers slugify, path generation, directory creation, and JSON metadata writing.
"""

import json
from pathlib import Path
from unittest.mock import patch

from app.core.storage import (
    ensure_scan_directory,
    get_scan_output_path,
    slugify,
    write_meta_json,
)

# ────────────────────────────────────────────────────────────────────────
# slugify() Tests
# ────────────────────────────────────────────────────────────────────────


def test_slugify_french_accents():
    """Test slugify handles French accents correctly."""
    result = slugify("Société Générale")
    assert result == "societe-generale", f"Expected 'societe-generale', got '{result}'"


def test_slugify_spaces_to_dashes():
    """Test slugify converts spaces to dashes."""
    result = slugify("Test Company")
    assert result == "test-company", f"Expected 'test-company', got '{result}'"


def test_slugify_special_chars_removed():
    """Test slugify removes special characters."""
    result = slugify("Acme & Co. (Paris)")
    assert result == "acme-co-paris", f"Expected 'acme-co-paris', got '{result}'"


def test_slugify_multiple_spaces_collapsed():
    """Test slugify collapses multiple spaces to single dash."""
    result = slugify("A  B  C")
    assert result == "a-b-c", f"Expected 'a-b-c', got '{result}'"


def test_slugify_leading_trailing_stripped():
    """Test slugify strips leading/trailing whitespace and dashes."""
    result = slugify("  test  ")
    assert result == "test", f"Expected 'test', got '{result}'"


def test_slugify_empty_input():
    """Test slugify handles empty string."""
    result = slugify("")
    assert result == "", f"Expected empty string, got '{result}'"


def test_slugify_only_special_chars():
    """Test slugify returns empty string for special chars only."""
    result = slugify("@#$%")
    assert result == "", f"Expected empty string, got '{result}'"


def test_slugify_unicode_handling():
    """Test slugify handles various unicode characters."""
    result = slugify("Café-Zürich")
    assert result == "cafe-zurich", f"Expected 'cafe-zurich', got '{result}'"


# ────────────────────────────────────────────────────────────────────────
# get_scan_output_path() Tests
# ────────────────────────────────────────────────────────────────────────


def test_get_scan_output_path_structure():
    """Test get_scan_output_path generates correct path structure."""
    result = get_scan_output_path("Test Company", "scan-001")
    
    # Verify it's a Path object
    assert isinstance(result, Path), f"Expected Path object, got {type(result)}"
    
    # Verify path components (from end backwards)
    parts = result.parts
    assert parts[-1] == "scan-001", f"Expected scan_id 'scan-001', got '{parts[-1]}'"
    assert parts[-2] == "M365", f"Expected tool 'M365', got '{parts[-2]}'"
    assert parts[-3] == "Cloud", f"Expected 'Cloud', got '{parts[-3]}'"
    assert parts[-4] == "test-company", f"Expected slug 'test-company', got '{parts[-4]}'"


def test_get_scan_output_path_custom_tool():
    """Test get_scan_output_path with custom tool parameter."""
    result = get_scan_output_path("Test Company", "scan-001", tool="Azure")
    
    parts = result.parts
    assert parts[-2] == "Azure", f"Expected tool 'Azure', got '{parts[-2]}'"


# ────────────────────────────────────────────────────────────────────────
# ensure_scan_directory() Tests
# ────────────────────────────────────────────────────────────────────────


def test_ensure_scan_directory_creates_path(tmp_path, monkeypatch):
    """Test ensure_scan_directory creates directory."""
    # Mock settings to use tmp_path
    with patch("app.core.storage.get_settings") as mock_settings:
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        
        result = ensure_scan_directory("Test Company", "scan-001")
        
        assert result.exists(), f"Directory {result} was not created"
        assert result.is_dir(), f"{result} is not a directory"


def test_ensure_scan_directory_returns_path(tmp_path):
    """Test ensure_scan_directory returns Path object."""
    with patch("app.core.storage.get_settings") as mock_settings:
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        
        result = ensure_scan_directory("Test Company", "scan-001")
        
        assert isinstance(result, Path), f"Expected Path object, got {type(result)}"


def test_ensure_scan_directory_idempotent(tmp_path):
    """Test ensure_scan_directory can be called multiple times safely."""
    with patch("app.core.storage.get_settings") as mock_settings:
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        
        # Call twice
        result1 = ensure_scan_directory("Test Company", "scan-001")
        result2 = ensure_scan_directory("Test Company", "scan-001")
        
        assert result1 == result2, "Multiple calls should return same path"
        assert result1.exists(), "Directory should still exist"


# ────────────────────────────────────────────────────────────────────────
# write_meta_json() Tests
# ────────────────────────────────────────────────────────────────────────


def test_write_meta_json_creates_file(tmp_path):
    """Test write_meta_json creates JSON file."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    
    metadata = {"tool": "M365", "status": "running", "scan_id": "abc-123"}
    result = write_meta_json(output_dir, metadata)
    
    assert result.exists(), f"File {result} was not created"
    assert result.name == "meta.json", f"Expected 'meta.json', got '{result.name}'"


def test_write_meta_json_content_matches(tmp_path):
    """Test write_meta_json writes correct JSON content."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    
    metadata = {"tool": "M365", "status": "completed", "findings": 42}
    meta_file = write_meta_json(output_dir, metadata)
    
    # Read back and verify
    with open(meta_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    
    assert loaded == metadata, f"Expected {metadata}, got {loaded}"


def test_write_meta_json_pretty_printed(tmp_path):
    """Test write_meta_json uses pretty-print formatting."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    
    metadata = {"key1": "value1", "key2": "value2"}
    meta_file = write_meta_json(output_dir, metadata)
    
    # Read raw content
    content = meta_file.read_text(encoding="utf-8")
    
    # Should have newlines (pretty-printed)
    assert "\n" in content, "Expected pretty-printed JSON with newlines"
    # Should have indentation
    assert "  " in content, "Expected indentation in JSON"


def test_write_meta_json_unicode_support(tmp_path):
    """Test write_meta_json handles unicode correctly."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    
    metadata = {"entreprise": "Société Générale", "ville": "Paris"}
    meta_file = write_meta_json(output_dir, metadata)
    
    # Read back and verify unicode preserved
    with open(meta_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    
    assert loaded["entreprise"] == "Société Générale", "Unicode should be preserved"
    assert loaded["ville"] == "Paris", "Unicode should be preserved"
