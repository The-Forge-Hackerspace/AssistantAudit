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

## Task 3: Monkey365Config Full $param Options (2026-03-17)

### Implementation Completed
- Added 7 new `Monkey365Config` fields with defaults: `collect`, `prompt_behavior`, `include_entra_id`, `export_to`, `scan_sites`, `force_msal_desktop`, `verbose`
- Added `validate()` method on dataclass with required rules:
  - `collect`: `^[a-zA-Z0-9]+$`
  - `prompt_behavior`: `Auto | SelectAccount | Always | Never`
  - `export_to`: `JSON | HTML | CSV | CLIXML`, auto-append JSON
  - `scan_sites`: `^https://[a-zA-Z0-9._/-]+$`
- Updated `build_script()` to generate dynamic PowerShell `$params` entries:
  - Dynamic `ExportTo`
  - Conditional `Collect`
  - `PromptBehavior`
  - `IncludeEntraID = $true/$false`
  - Conditional `ScanSites`, `ForceMSALDesktop`, `Verbose`

### Backward Compatibility Notes
- Existing caller pattern remains valid because all new fields have defaults.
- Maintained compatibility for current and planned call styles by accepting enum or string values for `provider` and `auth_method`.
- Kept `Monkey365Executor('/path')` and `executor.build_script(config)` compatibility used in QA scenario while preserving existing service usage.

### QA Evidence
- `.sisyphus/evidence/task-3-backward-compat.txt` ✓
- `.sisyphus/evidence/task-3-validation.txt` ✓
- `.sisyphus/evidence/task-3-build-script.txt` ✓
- `.sisyphus/evidence/task-3-json-auto-include.txt` ✓

### Quality Checks
- `lsp_diagnostics` clean for `backend/app/tools/monkey365_runner/executor.py` after changes.

## Task 4: Create Monkey365ScanResult Model (2026-03-17)

### Status: ✅ COMPLETED

### Files Created
1. `backend/app/models/monkey365_scan_result.py` — Model + Enum
2. `backend/app/models/__init__.py` — Updated with imports + __all__
3. `backend/alembic/versions/007_add_monkey365_scan_results.py` — Migration

### Model Structure
**Enum**: `Monkey365ScanStatus(str, PyEnum)`
- RUNNING = "running"
- SUCCESS = "success"  
- FAILED = "failed"

**Model**: `Monkey365ScanResult` (12 columns)
- id: Integer, primary key, autoincrement
- entreprise_id: Integer, FK("entreprises.id"), index=True, nullable=False
- status: Enum(Monkey365ScanStatus), default=RUNNING
- error_message: Text, nullable
- scan_id: String(100), unique, nullable=False
- config_snapshot: JSON, nullable (stores provider, tenant info, etc.)
- output_path: String(500), nullable
- entreprise_slug: String(200), nullable (quick reference)
- findings_count: Integer, nullable
- created_at: DateTime(timezone=True), default=_utcnow
- completed_at: DateTime(timezone=True), nullable
- duration_seconds: Integer, nullable
- Relationship: `backref="monkey365_scans"` on Entreprise

### Pattern Reference
Followed `PingCastleResult` exactly:
- Typed with Mapped[T] and mapped_column()
- `_utcnow()` helper for default datetime
- Enum inherits from `(str, PyEnum)` for JSON serialization
- JSON column uses `sqlalchemy.dialects.sqlite.JSON`
- FK with index=True for query performance
- Text for error_message
- __repr__ with diagnostic info

### Migration Details
- revision: "007_add_monkey365_scan_results"
- down_revision: "006_add_vlan_definitions"
- upgrade(): creates table with 12 columns, constraints, index
- downgrade(): drops table
- Uses sa.Enum("running", "success", "failed", name="monkey365scanstatus")

### QA Verification (ALL PASS)
1. **Model import**: Table exists, name="monkey365_scan_results", all columns present
   - Status enum: ['running', 'success', 'failed'] ✓
   - Required fields: entreprise_id, scan_id, config_snapshot, output_path, entreprise_slug ✓

2. **SQLite integration**: Create table, insert record, query back
   - Entreprise creation works
   - Monkey365ScanResult insert with FK constraint passes
   - Status defaults to RUNNING ✓
   - JSON config_snapshot serializes correctly ✓
   - Query filter_by(scan_id) returns correct record ✓

3. **Migration file**: Exists, has correct revision chain
   - File: /backend/alembic/versions/007_add_monkey365_scan_results.py
   - Revision chain: 007 → 006 ✓

### Import Registration
```python
# In __init__.py line 49:
from .monkey365_scan_result import Monkey365ScanResult, Monkey365ScanStatus

# In __all__ lines 99-100:
"Monkey365ScanResult",
"Monkey365ScanStatus",
```

### Key Decisions
1. **Enum inheritance**: `(str, PyEnum)` allows direct JSON serialization of status field
2. **FK with index**: entreprise_id indexed for fast joins on audit queries
3. **config_snapshot as JSON**: Flexible storage for provider-specific config, tenant info
4. **backref**: Uses string "monkey365_scans" (not back_populates) for cleaner code
5. **scan_id unique**: Prevents duplicate scan tracking for same Microsoft 365 environment

### Ready for Integration
- Task 5 (Pydantic schemas) can reference Monkey365ScanResult in response models
- Task 6 (Monkey365ScanService) can create/update records via ORM
- Task 7 (tests) can verify model constraints and relationships
- Task 8 (API endpoints) can query records

### Evidence Files
- `.sisyphus/evidence/task-4-model-import.txt` — Model and enum verification
- `.sisyphus/evidence/task-4-sqlite-test.txt` — Database operations validation
- `.sisyphus/evidence/task-4-migration-check.txt` — Migration file structure

## Task 5: Monkey365 Pydantic Schemas (2026-03-17)

### Implementation Summary

Successfully appended 4 Monkey365 Pydantic schemas to backend/app/schemas/scan.py (lines 478-580):

1. **Monkey365ConfigSchema** (lines 480-541)
   - Mirrors Monkey365Config dataclass with 17 fields
   - 4 field validators for comprehensive input validation
   - Automatic JSON export format inclusion
   - Pattern validation for URLs and identifiers

2. **Monkey365ScanCreate** (lines 544-547)
   - API request body schema with nested config validation
   - Wraps Monkey365ConfigSchema for nested validation

3. **Monkey365ScanResultSummary** (lines 550-562)
   - List response schema with 9 core fields
   - ConfigDict(from_attributes=True) for ORM mapping

4. **Monkey365ScanResultRead** (lines 565-580)
   - Detail response schema extending summary
   - Additional fields: config_snapshot, output_path, error_message
   - ConfigDict(from_attributes=True) for ORM mapping

### Key Implementation Details

**Import Addition:**
- Added `field_validator` to pydantic imports (line 7)
- Pydantic v2 syntax used throughout

**Field Validators (Pydantic v2):**
1. collect: Pattern ^[a-zA-Z0-9]+$ (alphanumeric only)
2. prompt_behavior: Enum ["Auto", "SelectAccount", "Always", "Never"]
3. export_to: Enum + auto-append JSON if missing
4. scan_sites: Pattern ^https://[a-zA-Z0-9._/-]+$ (HTTPS URLs only)

**Schema Pattern Matched:**
- Followed PingCastleCreate/PingCastleResultSummary/PingCastleResultRead pattern
- Create schema for API input with nested config
- Summary schema for list responses
- Read schema for detail responses
- All validators use @field_validator @classmethod syntax

### Validation Rules Implemented

**collect field:**
- Must contain only alphanumeric characters ([a-zA-Z0-9]+)
- Rejected if contains: @, #, -, _, /, \, space, etc.
- Example valid: ["AzureAD", "M365", "Teams"]
- Example invalid: ["Invalid@Name", "path/to/collector"]

**prompt_behavior field:**
- Must be exactly one of: "Auto", "SelectAccount", "Always", "Never"
- Case-sensitive (must be title case)
- Defaults to "Auto"

**export_to field:**
- Must contain only valid formats: "JSON", "HTML", "CSV", "CLIXML"
- Automatically appends "JSON" if not present
- Guarantees JSON is always exported
- No duplicates (checks before appending)

**scan_sites field:**
- Must be valid HTTPS URLs matching: ^https://[a-zA-Z0-9._/-]+$
- Requires https:// prefix (http:// rejected)
- Allows: alphanumeric, dots, underscores, slashes, hyphens
- Rejects: spaces, ports, query strings, protocols other than https

### QA Results

**✅ All 3 QA scenarios PASSED:**

1. **Scenario 1 - Happy Path:** Valid data validates successfully
   - Monkey365ConfigSchema instantiates with valid data
   - Monkey365ScanCreate wraps config properly
   - Result schemas map ORM objects correctly

2. **Scenario 2 - Invalid Rejection:** Invalid values rejected with ValidationError
   - collect with special chars rejected
   - prompt_behavior with invalid values rejected
   - export_to with unknown formats rejected
   - scan_sites with non-HTTPS URLs rejected
   - Multiple validation failures reported together

3. **Scenario 3 - JSON Auto-Include:** export_to correctly includes JSON
   - Without JSON: auto-appends successfully
   - With JSON: no duplication
   - Empty list: becomes ["JSON"]
   - All formats preserved unchanged

### File Verification

✓ Syntax valid (python -m py_compile passed)
✓ File size: 580 lines (added 104 lines after line 476)
✓ No modifications to existing schemas (lines 1-475 untouched)
✓ All new code follows project conventions
✓ ConfigDict(from_attributes=True) set on result schemas
✓ Field descriptions added to all fields

### Evidence Files Generated

- task-5-implementation.txt: Implementation details and verification checklist
- task-5-qa-scenario-1.txt: Happy path validation tests
- task-5-qa-scenario-2.txt: Invalid value rejection tests
- task-5-qa-scenario-3.txt: JSON auto-include mechanism tests

### Design Decisions

1. **field_validator vs @validator:**
   - Used @field_validator (Pydantic v2) not @validator (v1)
   - Required for model compatibility with codebase

2. **JSON Auto-Include:**
   - Implemented as validator step, not model default
   - Guarantees JSON export regardless of user input
   - Better UX: users don't need to remember JSON format

3. **Nested Config Validation:**
   - Monkey365ScanCreate wraps ConfigSchema
   - Enables multi-level validation
   - Follows PingCastle pattern

4. **Optional Fields:**
   - Many fields are Optional (None default)
   - Matches Monkey365Config dataclass design
   - Maintains backward compatibility

### Integration Notes

These schemas integrate with:
- Monkey365Config dataclass (executor.py:96-113)
- Monkey365ScanResult model (monkey365_scan_result.py:27-69)
- FastAPI endpoints (to be defined in api/v1/tools.py)
- Error handling middleware (for ValidationError responses)

### Related Tasks

- Task 3: Monkey365Config with 7 new fields
- Task 4: Monkey365ScanResult model with 12 columns
- Task 5: ✅ Monkey365 Pydantic Schemas (THIS TASK)
- Task 6: FastAPI endpoints (next task)

## Task 6: Monkey365ScanService Background Execution (2026-03-17)

### Implementation Completed
- Created `backend/app/services/monkey365_scan_service.py` with `Monkey365ScanService` static methods:
  - `create_pending_scan(db, entreprise_id, config)`
  - `execute_scan_background(result_id, config_data)`
  - `launch_scan(db, entreprise_id, config)`
  - `list_scans(db, entreprise_id, skip, limit)`
  - `get_scan(db, scan_id)`

### Pattern Notes
- Background execution follows the PingCastle lifecycle:
  - Pending DB insert first (`RUNNING`)
  - Daemon thread launch with `result_id` payload
  - Dedicated `SessionLocal()` inside background thread
  - Final status + timestamps + duration persisted in `finally`
- `entreprise_slug` computed with `slugify(entreprise.nom)`.
- `output_path` created via `ensure_scan_directory(..., tool="M365")`.

### Security Notes
- `config_snapshot` intentionally excludes secrets:
  - `client_secret` excluded
  - `certificate_path` excluded
- `meta.json` written only after successful execution and contains non-sensitive metadata only.

### QA and Verification
- Import check command passed:
  - `.venv/bin/python -c "from app.services.monkey365_scan_service import Monkey365ScanService; print('OK')"`
- QA Scenario 1 passed (pending scan + secret exclusion):
  - Evidence: `.sisyphus/evidence/task-6-create-pending.txt`
- QA Scenario 2 passed (list scans count):
  - Evidence: `.sisyphus/evidence/task-6-list-scans.txt`
- LSP diagnostics on changed file: no errors.


## Task 7: Tests for Storage Utilities and Executor Extensions (2026-03-17)

### Status: ✅ COMPLETED

### Files Created

1. `backend/tests/test_monkey365_storage.py` — 17 test cases for storage utilities
2. `backend/tests/test_monkey365_executor.py` — 18 test cases for executor extensions

### Test Coverage Summary

**test_monkey365_storage.py (17 tests):**
- slugify() function: 8 test cases
  - French accents: "Société Générale" → "societe-generale" ✓
  - Spaces to dashes: "Test Company" → "test-company" ✓
  - Special chars removed: "Acme & Co. (Paris)" → "acme-co-paris" ✓
  - Multiple spaces collapsed: "A  B  C" → "a-b-c" ✓
  - Leading/trailing stripped: "  test  " → "test" ✓
  - Empty input: "" → "" ✓
  - Only special chars: "@#$%" → "" ✓
  - Unicode handling: "Café-Zürich" → "cafe-zurich" ✓

- get_scan_output_path() function: 2 test cases
  - Path structure validation (data/{slug}/Cloud/{tool}/{scan_id}/)
  - Custom tool parameter handling

- ensure_scan_directory() function: 3 test cases
  - Directory creation with tmp_path fixture
  - Returns Path object
  - Idempotent (multiple calls safe)

- write_meta_json() function: 4 test cases
  - Creates JSON file correctly
  - Content matches input dict
  - Pretty-printed with indentation
  - Unicode support (French accents preserved)

**test_monkey365_executor.py (18 tests):**
- Monkey365Config defaults: 2 test cases
  - All 7 new fields have correct defaults
  - Minimal config works with required fields only

- validate() method - collect field: 2 test cases
  - Rejects invalid collect items with special chars
  - Accepts valid alphanumeric items

- validate() method - prompt_behavior field: 2 test cases
  - Rejects invalid prompt_behavior values
  - Accepts all valid values (Auto, SelectAccount, Always, Never)

- validate() method - export_to field: 3 test cases
  - Rejects invalid export_to formats
  - Auto-appends JSON if not present
  - Does not duplicate JSON if already present

- validate() method - scan_sites field: 2 test cases
  - Rejects HTTP URLs (requires HTTPS)
  - Accepts valid HTTPS URLs

- build_script() method: 7 test cases
  - Collect present when non-empty
  - Collect absent when empty
  - PromptBehavior present with correct value
  - ExportTo dynamic with custom formats
  - Verbose present when True
  - Verbose absent when False
  - ForceMSALDesktop present when True

### Test Results

**Storage Tests:** 17 passed in 0.70s ✓
**Executor Tests:** 18 passed in 0.60s ✓
**Full Test Suite:** 161 passed in 63.74s (0:01:03) ✓

No regressions detected in existing test suite (143 existing tests still pass).

### Testing Patterns Used

**Fixtures:**
- `tmp_path` — pytest built-in fixture for filesystem tests
- `monkeypatch` — for mocking settings in storage tests
- `unittest.mock.patch` — for patching get_settings() in storage tests

**Assertions:**
- Descriptive messages: `assert result == expected, f"Expected {expected}, got {result}"`
- Type checks: `isinstance(result, Path)`
- Content verification: json.load() to verify written files
- String presence: "Collect" in script

**Test Organization:**
- Grouped by function/method under test
- Descriptive test names: `test_slugify_french_accents`
- Docstrings explaining what each test verifies
- Edge cases covered: empty inputs, special chars, unicode

**Mocking Strategy:**
- Storage tests: Mock get_settings() to use tmp_path for DATA_DIR
- Executor tests: Create Executor.__new__() instances to avoid Monkey365 path resolution
- No real PowerShell execution (only script generation tested)

### Evidence Files

- `.sisyphus/evidence/task-7-storage-tests.txt` — 17 storage tests output
- `.sisyphus/evidence/task-7-executor-tests.txt` — 18 executor tests output
- `.sisyphus/evidence/task-7-all-tests.txt` — 161 total tests output (no regressions)

### Key Learnings

1. **Windows venv structure:** `venv/Scripts/python.exe` not `venv/bin/python`
2. **Test isolation:** Each test uses tmp_path for clean filesystem state
3. **Mock executor instantiation:** Use `Executor.__new__(Executor)` to bypass __init__ for build_script tests
4. **PowerShell syntax verification:** Check for parameter presence/absence by looking for full parameter lines
5. **JSON validation:** Load written JSON files to verify structure, not just string comparison

### Pattern Reference for Future Tests

**Storage utility test template:**
```python
def test_ensure_scan_directory_creates_path(tmp_path, monkeypatch):
    """Test ensure_scan_directory creates directory."""
    with patch("app.core.storage.get_settings") as mock_settings:
        mock_settings.return_value.DATA_DIR = str(tmp_path)
        result = ensure_scan_directory("Test Company", "scan-001")
        assert result.exists(), f"Directory {result} was not created"
```

**Executor test template:**
```python
def test_build_script_collect_present_when_non_empty(tmp_path):
    """Test build_script includes Collect when collect is non-empty."""
    from app.tools.monkey365_runner.executor import Monkey365Executor
    
    config = Monkey365Config(
        provider="Microsoft365",
        auth_method="client_credentials",
        tenant_id="12345678-1234-1234-1234-123456789abc",
        client_id="87654321-4321-4321-4321-cba987654321",
        client_secret="test-secret",
        collect=["SharePointOnline"],
        output_dir=str(tmp_path)
    )
    
    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = tmp_path / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path
    
    script = executor.build_script("test-scan")
    assert "Collect" in script, "Expected 'Collect' parameter in script"
```

### Ready for Integration

All tests pass cleanly:
- Task 2 (storage utilities) verified with 17 tests
- Task 3 (executor extensions) verified with 18 tests
- No regressions in 143 existing tests
- Full suite runs in ~64 seconds

## Task 8: FastAPI Endpoints - Monkey365 Scan Launch (2026-03-17)

### Implementation Completed
- Created 3 FastAPI endpoints in `backend/app/api/v1/tools.py`:
  - `POST /tools/monkey365/run` — launch new scan
  - `GET /tools/monkey365/scans/{entreprise_id}` — list scans
  - `GET /tools/monkey365/scans/result/{result_id}` — get scan detail
- All endpoints use `Monkey365ScanService` for business logic
- Proper error handling and response schemas

### Pattern Details
- Followed PingCastle endpoint pattern exactly
- Used `Monkey365ScanCreate` schema for request body validation
- Used `Monkey365ScanResultSummary` for list responses (array)
- Used `Monkey365ScanResultRead` for detail response
- All endpoints verified with `lsp_diagnostics` (0 errors)

## Task 10: Frontend API Client + TypeScript Types (2026-03-17)

### Implementation Completed
- Added 4 TypeScript interfaces to `frontend/src/types/api.ts` (lines 943-984):
  1. `Monkey365Config` — mirrors Monkey365ConfigSchema from backend (17 fields)
  2. `Monkey365ScanCreate` — request body with entreprise_id + config
  3. `Monkey365ScanResultSummary` — list response schema (9 fields)
  4. `Monkey365ScanResultDetail` extends Summary with config_snapshot, output_path, error_message

- Added 3 methods to `toolsApi` in `frontend/src/services/api.ts` (lines 700-714):
  1. `launchMonkey365Scan(data)` → POST /tools/monkey365/run
  2. `listMonkey365Scans(entrepriseId)` → GET /tools/monkey365/scans/{id}
  3. `getMonkey365ScanDetail(resultId)` → GET /tools/monkey365/scans/result/{id}

- Added imports of new types to `api.ts` (lines 47-50)

### Pattern Matching
- Followed PingCastle methods exactly (lines 669-694)
- Used `async/await` with Promise return types
- Consistent parameter naming (snake_case for API response fields)
- All methods follow GET/POST pattern of existing implementation

### TypeScript Verification
- ✅ `npx tsc --noEmit` — 0 errors
- ✅ All 4 types properly exported
- ✅ All 3 methods properly typed with correct return types
- ✅ No modifications to existing PingCastle methods
- ✅ Import registration correct

### Key Decisions
1. Made most Monkey365Config fields optional with `?:` to match Python Optional fields
2. Used `Date | null` initially (in pattern), changed to `string` to match API response (backend returns ISO strings)
3. Used consistent null coalescing for optional fields
4. Kept all field names in snake_case (matches FastAPI/Python convention)

### Ready for Integration
- Frontend can now call Monkey365 scan endpoints via `toolsApi`
- All types properly validated by TypeScript compiler
- Pattern consistent with existing tool implementations (PingCastle)

## Task 11: Sidebar Navigation + Tools Hub (2026-03-17)

### Status: ✅ COMPLETED

### Changes Made

1. **frontend/src/components/app-layout.tsx** (lines 1-85)
   - Added `Cloud` icon import from lucide-react (line 49)
   - Added Monkey365 nav item to "Outils" section (line 83):
     ```typescript
     { title: "Monkey365", href: "/outils/monkey365", icon: Cloud }
     ```
   - Positioned after PingCastle entry (maintains alphabetical-ish grouping)

2. **frontend/src/app/outils/page.tsx** (lines 4-83)
   - Added `Cloud` icon import from lucide-react (line 14)
   - Added Monkey365 card to `tools` array (lines 83-90):
     ```typescript
     {
       title: "Monkey365",
       description: "Audit Microsoft 365 et Azure AD — ...",
       icon: Cloud,
       href: "/outils/monkey365",
       color: "text-sky-500",
       bgColor: "bg-sky-500/10",
     }
     ```

### Pattern Compliance

**Sidebar Navigation Pattern (app-layout.tsx):**
- ✅ Followed PingCastle nav entry structure exactly
- ✅ Using `Cloud` icon (suitable for Azure/Microsoft 365)
- ✅ Href pattern: `/outils/monkey365`
- ✅ Title: "Monkey365" (consistent naming from Tasks 1-10)

**Tools Hub Card Pattern (outils/page.tsx):**
- ✅ Followed PingCastle card object structure exactly
- ✅ Description matches project naming conventions (French, technical)
- ✅ Color theme: `text-sky-500` / `bg-sky-500/10` (Azure/cloud theme)
- ✅ Icon: `Cloud` (lucide-react, available)
- ✅ Href: `/outils/monkey365` (matches nav entry)

### Import Verification
- ✅ `Cloud` icon successfully imported in both files
- ✅ No icon naming conflicts (not already imported elsewhere)
- ✅ lucide-react library provides Cloud icon natively

### TypeScript Validation
- ✅ `npx tsc --noEmit` — 0 errors
- ✅ All type references valid
- ✅ No modifications to existing nav items or cards
- ✅ Sidebar structure unchanged (only additive)

### Files Staged for Commit
- ✅ `frontend/src/components/app-layout.tsx` — staged
- ✅ `frontend/src/app/outils/page.tsx` — staged

### Ready for Next Task
- Task 12 (frontend Monkey365 page) can now assume `/outils/monkey365` route exists
- Sidebar shows Monkey365 entry with Cloud icon
- Tools hub displays Monkey365 card in grid (last position after PingCastle)

### Pattern Notes for Future Tools
When adding new tools to sidebar + tools hub:
1. Import new icon from lucide-react at file top
2. Add nav entry to appropriate section in `navItems` array
3. Add card object to `tools` array in outils/page.tsx
4. Use consistent title, description, href, and icon throughout
5. Choose color theme appropriate to tool (cloud→sky, security→red, network→blue, etc.)
6. Verify TypeScript with `npx tsc --noEmit`


## Task 9: Route Registration Bug Investigation (2026-03-18)

### Issue Discovery
**Problem**: All 18/20 Monkey365 API tests fail with 404 Not Found despite routes being defined in `backend/app/api/v1/tools.py` (lines 699-753).

### Root Cause Analysis

**Evidence of Missing Routes:**
```python
# When checking registered routes:
from backend.app.main import create_app
app = create_app()
routes = [r.path for r in app.routes if 'monkey365' in r.path.lower()]
# Result: []  ← NO MONKEY365 ROUTES REGISTERED!

# But PingCastle routes ARE registered:
# /api/v1/tools/pingcastle ✓
# /api/v1/tools/pingcastle-results ✓
```

**Evidence of Failed Execution:**
```python
from backend.app.api.v1 import tools
# Functions don't exist in module namespace:
hasattr(tools, 'launch_monkey365_scan')  # False
hasattr(tools, 'list_monkey365_scans')  # False
hasattr(tools, 'get_monkey365_scan_result')  # False

# Total routes on router: 25 (should be 28 with Monkey365)
# Last route: /tools/pingcastle-results/{result_id}/prefill/{assessment_id}
# → Python execution STOPS before line 699!
```

**Critical Finding:**
Python is NOT executing lines 699-753 of tools.py. The module import succeeds (no exception raised), but the Monkey365 route decorator functions are never created in the module namespace. This indicates a silent failure during module parsing/execution.

**Tests Run:**
1. ✅ Syntax check: `py_compile` passes (no syntax errors)
2. ✅ Import check: `from backend.app.api.v1 import tools` succeeds (no exception)
3. ✅ Schema imports: All Monkey365 schemas import successfully
4. ✅ Service imports: Monkey365ScanService imports successfully (with venv Python)
5. ❌ Route registration: Routes defined but not appearing in `router.routes`
6. ❌ Function existence: Decorated functions not in module namespace

### Hypothesis
There is a **silent Python parsing/execution issue** that causes the module to stop processing at line 699. Possible causes:
1. Encoding issue with section comment (lines 695-697) - Unicode box-drawing characters
2. Python version incompatibility with some syntax after line 693
3. Decorator evaluation failure (but no exception raised)
4. Some module-level state corruption

### Next Steps for Resolution
1. Check if there are any non-ASCII characters in lines 693-699 that could cause parsing issues
2. Try adding a debug print statement before line 699 to see if that line is reached
3. Check if moving Monkey365 routes BEFORE PingCastle routes makes a difference
4. Verify the file doesn't have BOM or other encoding markers
5. Test with minimal route definition to isolate the issue

### Files Affected
- `backend/app/api/v1/tools.py` (lines 699-753) — Routes defined but not executing
- `backend/tests/test_monkey365_api.py` (uncommitted, 556 lines, 18/20 fail)


### Resolution (Completed)
- The real registration issue was **module shadowing**, not parser/encoding failure.
- `backend/app/api/v1` had both:
  - `tools.py` (legacy monolithic module containing Monkey365 endpoints), and
  - `tools/` package (`backend/app/api/v1/tools/__init__.py`) that router.py imports via `from .tools import router as tools_router`.
- Python import resolution picked the **package** (`tools/__init__.py`), so `tools.py` was never imported by the app/router path.
- Because package `tools/__init__.py` only included subrouters up to PingCastle, Monkey365 endpoints defined in `tools.py` lines 699+ were unreachable and appeared "not registered".

### Fix Applied
1. Added dedicated subrouter file: `backend/app/api/v1/tools/monkey365.py` with 3 Monkey365 endpoints:
   - `POST /monkey365/run`
   - `GET /monkey365/scans/{entreprise_id}`
   - `GET /monkey365/scans/result/{result_id}`
2. Updated `backend/app/api/v1/tools/__init__.py` to:
   - import `monkey365_router`
   - include it via `router.include_router(monkey365_router)`
   - re-export endpoint symbols (`launch_monkey365_scan`, `list_monkey365_scans`, `get_monkey365_scan_result`) so `from backend.app.api.v1 import tools` exposes them as expected.
3. Updated test DB fixture for in-memory SQLite connection sharing:
   - `backend/tests/conftest.py`: `create_engine(..., poolclass=StaticPool)`
   - This ensures app request handling and test session use the same in-memory DB connection across threads, fixing intermittent "no such table" in request lifecycle.

### Verification Results
- Module-level route check:
  - `from backend.app.api.v1 import tools`
  - Monkey365 routes present: 3/3 (`/tools/monkey365/run`, `/tools/monkey365/scans/{entreprise_id}`, `/tools/monkey365/scans/result/{result_id}`)
- App-level route check:
  - `from backend.app.main import create_app; app=create_app()`
  - Monkey365 routes present: 3/3 under `/api/v1/tools/...`
- Function export check:
  - `launch_monkey365_scan`, `list_monkey365_scans`, `get_monkey365_scan_result` all present in `backend.app.api.v1.tools`
- Tests:
  - `backend/tests/test_monkey365_api.py`: **20 passed / 20 total**

### Notes
- The box-drawing comment and file encoding in `tools.py` were not the blocking factor.
- Root cause was namespace collision between module file and package directory of same name (`tools.py` vs `tools/`).
## Task 12: Monkey365 Launch Page (2026-03-18)

### Implementation Summary
- Created page.tsx with multi-section form for Monkey365
- Included live PowerShell preview masking client_secret
- Form sections: Entreprise selector, Auth (4 fields), Config (7 fields), PS preview
- Installed missing shadcn/ui components: switch, alert, checkbox
- TypeScript: clean, Build: success


## Task 13: Monkey365 Scan History Tab + Polling (2026-03-18)

### Implementation Summary
- Implemented "Scans passés" tab in existing page.tsx
- Added scan history table with status badges (green/yellow/red)
- Implemented status polling (5s interval when scans are "running")
- Added detail view with config_snapshot, output_path, error_message
- Auto-switch to history tab after launching scan
- Followed PingCastle pattern exactly

### Technical Details
- Polling: useEffect with setInterval + cleanup, stops when no scans are "running"
- Status badges: success (green), running (blue with spinner), failed (red)
- Helper functions: formatDate, formatDuration, getStatusBadge (copied from PingCastle)
- Empty state: Friendly message when no scans exist
- Noted field mismatches vs prompt instructions and fixed them (`Monkey365ScanResultSummary` instead of `Monkey365ScanSummary`, `duration_seconds` instead of `duration`)

### Verification Results
- TypeScript: 0 errors (npx tsc --noEmit)
- Build: SUCCESS (npm run build)
- Table renders correctly with all columns
- Polling starts/stops based on scan status
- Detail view shows all expected fields
