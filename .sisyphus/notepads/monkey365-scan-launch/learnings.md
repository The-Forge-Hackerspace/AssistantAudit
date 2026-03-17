# Learnings - Monkey365 Scan Launch

## Patterns and Conventions
(Subagents: append discoveries here)

## Task 1: Add DATA_DIR and MONKEY365_TIMEOUT to Settings

**Status**: ✅ COMPLETED

### Changes Made
1. Added `MONKEY365_TIMEOUT: int = 600` to Settings class (line 98) — matches existing NMAP_TIMEOUT pattern
2. Added `DATA_DIR: str = "./data"` to Settings class (line 106) — new section for data storage
3. Added `DATA_DIR=./data` to `.env.example` (line 40) — in tools section near MONKEY365_TIMEOUT

### Pattern Reference
- Followed existing style from MONKEY365_PATH, PINGCASTLE_PATH, PINGCASTLE_OUTPUT_DIR
- Used `str` type hint for DATA_DIR (not Path) to match existing pattern
- Default values: DATA_DIR="./data", MONKEY365_TIMEOUT=600
- Located after tool settings (NMAP, MONKEY365, PINGCASTLE) for logical grouping

### Validation Results
✅ Settings load with defaults: DATA_DIR=./data, TIMEOUT=600
✅ Environment variable overrides work correctly
✅ Both fields are accessible via settings.DATA_DIR and settings.MONKEY365_TIMEOUT

### Evidence Files
- `.sisyphus/evidence/task-1-settings-defaults.txt` — default values test
- `.sisyphus/evidence/task-1-settings-override.txt` — env override test

### Unblocks
- Task 2: storage.py can now use settings.DATA_DIR
- Task 6: service can now use settings.MONKEY365_TIMEOUT
- Task 8: API can now access both settings


## Task 2: Storage Path Utilities (2026-03-17)

### Implementation Completed
- `storage.py` module created with all 4 required functions
- French accent handling: `slugify("Société Générale")` → `"societe-generale"` ✓
- Path structure: `data/{slug}/Cloud/{tool}/{scan_id}/` ✓
- Metadata JSON support with indent=2 ✓

### Pattern Notes
- Settings singleton imported via `from .config import get_settings()` (relative import in package)
- DATA_DIR resolved: if relative, resolve relative to project root (BASE_DIR.parent)
- Slugify algorithm: NFKD normalize → ASCII encode (ignore) → lowercase → regex replace → collapse dashes → strip edges

### Implementation Details
- Used `unicodedata.normalize('NFKD', text)` for proper accent decomposition
- Path resolution: `BASE_DIR = Path(__file__).resolve().parent.parent.parent` gets backend/ directory
- Project root = backend parent, so data/ is at project root level
- All 3 QA scenarios PASS: French accents, storage creation, edge cases

### Code Quality
- Type hints: Dict imported from typing (linter wants Dict[str, Any] but code works)
- Relative imports used (`.config` not `app.core.config`)
- All functions docstrings with examples
- No external dependencies beyond stdlib + existing settings

### Ready for Integration
- Task 6 (Monkey365ScanService) can now use `ensure_scan_directory()` and `write_meta_json()`
- Task 7 tests can verify storage functions directly
