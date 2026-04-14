"""
Generic storage path utilities for scan output directories.

Provides slug generation, path management, and metadata handling that can be
reused by any tool that writes scan results (Monkey365, future cloud tools, etc.).

Path convention: {DATA_DIR}/{slug(entreprise)}/Cloud/{tool}/{scan_id}/
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict

from .config import get_settings


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Handles unicode normalization, accent stripping, lowercase conversion,
    and special character replacement.

    Algorithm:
    1. Normalize unicode (NFKD decomposition)
    2. Strip diacritics via ASCII encoding
    3. Lowercase
    4. Replace non-alphanumeric with dashes
    5. Collapse multiple dashes
    6. Strip leading/trailing dashes

    Args:
        text: Input text (may contain accents, spaces, special chars)

    Returns:
        URL-safe slug (lowercase, alphanumeric + dashes only)

    Examples:
        >>> slugify("Société Générale")
        'societe-generale'
        >>> slugify("  Àccénts & Spëcial!! Chars  ")
        'accents-special-chars'
        >>> slugify("Ça Marche Bien!")
        'ca-marche-bien'
    """
    # Step 1: Normalize unicode (NFKD = decompose accented chars)
    text = unicodedata.normalize("NFKD", text)

    # Step 2: Strip accents by encoding to ASCII (ignoring non-ASCII)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Step 3: Lowercase
    text = text.lower()

    # Step 4: Replace non-alphanumeric with dash
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # Step 5: Collapse multiple dashes to single dash
    text = re.sub(r"-+", "-", text)

    # Step 6: Strip leading/trailing dashes
    text = text.strip("-")

    return text


def get_scan_output_path(entreprise_name: str, scan_id: str, tool: str = "M365") -> Path:
    """
    Compute the output path for a scan result.

    Structure: {data_dir}/{slugify(entreprise_name)}/Cloud/{tool}/{scan_id}/

    Resolves DATA_DIR from settings:
    - If absolute: use as-is
    - If relative: resolve relative to project root (parent of backend/)

    Args:
        entreprise_name: Company name (e.g., "Test Co")
        scan_id: Unique scan identifier (e.g., "abc-123")
        tool: Tool name (default: "M365")

    Returns:
        Path object pointing to scan output directory (not created yet)

    Example:
        >>> path = get_scan_output_path("Test Co", "abc-123")
        >>> str(path)
        '/mnt/e/AssistantAudit/data/test-co/Cloud/M365/abc-123'
    """
    settings = get_settings()

    # Resolve DATA_DIR: absolute or relative to project root
    data_dir = Path(settings.DATA_DIR)
    if not data_dir.is_absolute():
        # BASE_DIR is backend/ (3 levels up from this file)
        backend_dir = Path(__file__).resolve().parent.parent.parent
        project_root = backend_dir.parent
        data_dir = project_root / settings.DATA_DIR

    # Build path: data_dir/slug/Cloud/tool/scan_id
    slug = slugify(entreprise_name) or "enterprise"
    output_path = data_dir / slug / "Cloud" / tool / scan_id

    return output_path


def ensure_scan_directory(entreprise_name: str, scan_id: str, tool: str = "M365") -> Path:
    """
    Ensure scan output directory exists, creating it if necessary.

    Creates all parent directories with parents=True, exist_ok=True.

    Args:
        entreprise_name: Company name
        scan_id: Unique scan identifier
        tool: Tool name (default: "M365")

    Returns:
        Path object pointing to the created/existing directory

    Example:
        >>> path = ensure_scan_directory("Test Co", "abc-123")
        >>> path.exists()
        True
    """
    output_path = get_scan_output_path(entreprise_name, scan_id, tool)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def write_meta_json(output_path: Path, meta: Dict) -> Path:  # type: ignore[type-arg]
    """
    Write metadata dictionary to meta.json in the output directory.

    Writes to {output_path}/meta.json with indent=2 for readability.

    Args:
        output_path: Directory path where meta.json will be written
        meta: Metadata dictionary to serialize

    Returns:
        Path object pointing to the written meta.json file

    Example:
        >>> path = ensure_scan_directory("Test Co", "abc-123")
        >>> meta_path = write_meta_json(path, {"tool": "M365", "status": "running"})
        >>> meta_path.exists()
        True
    """
    meta_file = output_path / "meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta_file
