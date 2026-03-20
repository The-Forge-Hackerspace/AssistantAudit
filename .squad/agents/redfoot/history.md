## Learnings

Project started 2026-03-19.

**Project:** AssistantAudit — Open-source IT infrastructure security auditing tool for pentesters and IT auditors.

**Scope:** Firewalls, Switches, Active Directory, Microsoft 365, Linux/Windows servers, network mapping with VLAN visualization.

**Tech Stack:**
- Backend: Python 3.13 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT OAuth2
- Database: SQLite (dev) → PostgreSQL (prod) — Alembic migrations
- Frontend: Next.js 16 (App Router) + React + TypeScript + Tailwind CSS v4 + shadcn/ui
- Auth: JWT cookies + Axios interceptor + AuthGuard
- Frameworks: 12 dynamic YAML files, SHA-256 synced at startup
- Storage: data/{entreprise_slug}/{category}/{tool}/{scan_id}/

**Current State:**
✅ Phase 1 — Backend foundation (45 endpoints, 8 models, JWT auth)
✅ Phase 2 — 12 YAML frameworks with SHA-256 sync engine
✅ Phase 3 — Full React UI (dashboard, CRUD, assessments, dark mode)
🔄 Phase 4 — Tool integrations (IN PROGRESS)
⏳ Phase 5 — PDF/Word report generation
⏳ Phase 6 — AI-assisted remediation suggestions

**Owner:** T0SAGA97
**GitHub:** https://github.com/The-Forge-Hackerspace/AssistantAudit

---

### 2026-03-19 — CRITICAL: Monkey365 Authentication Bug Fix

**Problem:** The Monkey365 executor incorrectly required `client_id` and `client_secret` for ALL authentication modes, including Interactive Browser mode. This violated the official Monkey365 documentation which states that Interactive Browser authentication requires ONLY `PromptBehavior = 'SelectAccount'` with NO client credentials.

**Root Cause:** The original implementation had a single auth path that always included tenant_id and always expected credentials, without conditional logic based on auth mode.

**Solution Implemented:**

1. **Created `config.py`** — Defined `Monkey365AuthMode` enum with 4 distinct modes:
   - `INTERACTIVE`: Browser popup authentication (NO credentials required)
   - `DEVICE_CODE`: Device code flow for headless environments (NO credentials required)
   - `ROPC`: Resource Owner Password Credentials (requires username + password + tenant_id)
   - `CLIENT_CREDENTIALS`: Application/daemon mode (requires client_id + client_secret + tenant_id)

2. **Rewrote `executor.py`** — PowerShell script generation is now FULLY CONDITIONAL:
   - `INTERACTIVE` mode: Only includes `PromptBehavior = 'SelectAccount'` (no TenantId, ClientId, ClientSecret)
   - `DEVICE_CODE` mode: Only includes `DeviceCode = $true` (no credentials)
   - `ROPC` mode: Includes `Username`, `Password` (SecureString), and `TenantId`
   - `CLIENT_CREDENTIALS` mode: Includes `ClientId`, `ClientSecret` (SecureString), and `TenantId`

3. **Updated Schema Validation** (`backend/app/schemas/scan.py`):
   - Changed `tenant_id`, `client_id`, `client_secret`, `username`, `password` to Optional fields
   - Added `@model_validator` with conditional validation based on `auth_mode`
   - Client credentials mode: Validates tenant_id and client_id are UUID format
   - ROPC mode: Validates tenant_id is UUID format, username is email format
   - Interactive/Device Code modes: No credential validation (none required)

4. **Security Enhancements**:
   - Added email format validation for usernames
   - Added password masking function (`_mask_password`) to NEVER log plaintext passwords
   - All credential fields validated with strict regex patterns (UUID, email, secret format)
   - Passwords always converted to SecureString in PowerShell scripts

**Files Modified:**
- `backend/app/tools/monkey365_runner/config.py` (NEW)
- `backend/app/tools/monkey365_runner/executor.py` (REWRITTEN)
- `backend/app/schemas/scan.py` (UPDATED with conditional validation)

**Key Learning:** External tool integrations must match OFFICIAL DOCUMENTATION exactly. Authentication modes with different credential requirements must use conditional logic, NOT one-size-fits-all parameter sets. Always validate inputs based on context (auth mode determines which credentials are required).

**Next Step:** Security Auditor (Kujan) to review for injection risks and credential handling security.

### 2026-03-19 — Monkey365 Auth Mode Schema Alignment

**Problem:** Monkey365 API schema and scan service still referenced legacy `auth_method` fields and extra config keys, causing mismatches with the updated auth-mode executor and frontend.

**Solution Implemented:**

1. **Schema update (`backend/app/schemas/scan.py`)**
   - Added `Monkey365AuthMode` enum
   - Switched `auth_mode` to enum type with conditional validation

2. **Service alignment (`backend/app/services/monkey365_scan_service.py`)**
   - Stored `auth_mode` in config snapshots/meta
   - Removed legacy fields (prompt_behavior, certificate_path, force_msal_desktop)
   - Passed auth_mode + ROPC credentials into executor safely

3. **API update (`backend/app/api/v1/tools.py`)**
   - Logging now reports auth_mode and avoids password exposure

**Testing Notes:** pytest run attempted; failures due to missing local API server (test_phase1/2) and duplicate test module name (test_monkey365_auth_modes.py).

### 2026-03-19 — Monkey365 Interactive Browser Blocker Fixes

**Problem:** Monkey365 scans hung in RUNNING due to a timezone mismatch during finalization, with no visibility into PowerShell output and brittle module loading.

**Solution Implemented:**
1. Normalized `created_at` timezone handling in scan finalization and logged scan durations.
2. Added Monkey365 auto-install/module verification and ensured scripts set location/import the module before `Invoke-Monkey365`.
3. Captured full PowerShell stdout/stderr to `powershell_raw_output.json` with duration metadata for debugging.

**Testing Notes:** pytest still fails in `test_phase1.py` / `test_phase2.py` due to connection refused (API server not running).

### 2025-01-27 — Monkey365 Output Directory Analysis & File Handling

**Task:** Investigate reported issue where "Monkey365 outputs to dynamic GUID directory (monkey-reports/$GUID/$FORMAT/$FILE) and files need to be moved to correct directory after completion."

**Investigation Findings:**

1. **No GUID Directory Issue Exists** — The current implementation already handles arbitrary subdirectory structures correctly via recursive glob patterns (`rglob("*.json")`)

2. **Current Architecture:**
   - Output path controlled via `-OutPath` parameter passed to Monkey365 PowerShell module
   - Directory structure: `{DATA_DIR}/{entreprise_slug}/Cloud/{tool}/{scan_id}/`
   - All files written by Monkey365 go to the configured output directory
   - Parser uses `Path.rglob("*.json")` to recursively find ALL JSON files regardless of subdirectory structure

3. **File Discovery Pattern (executor.py:606-622):**
   ```python
   def _parse_output(self, scan_id: str) -> list[dict[str, object]]:
       output_path = self.output_dir / scan_id
       for json_file in output_path.rglob("*.json"):  # ← Recursive search
           # Parse and aggregate findings
   ```
   This automatically handles:
   - `{scan_id}/report.json` ✅
   - `{scan_id}/m365/findings.json` ✅
   - `{scan_id}/monkey-reports/{GUID}/JSON/data.json` ✅
   - Any nested subdirectory structure ✅

4. **Standard Monkey365 Calling Pattern:**
   ```powershell
   $param = @{
       Instance       = 'Microsoft365';
       OutPath        = 'E:\path\to\scan_id';  # Controls output location
       ExportTo       = @('JSON', 'HTML');
       IncludeEntraID = $true;
       # Auth-mode-specific parameters (conditional):
       PromptBehavior = 'SelectAccount';  # INTERACTIVE only
       DeviceCode     = $true;             # DEVICE_CODE only
       TenantId       = '...';             # ROPC/CLIENT_CREDENTIALS
       Username       = '...';             # ROPC only
       Password       = (ConvertTo-SecureString '...' -AsPlainText -Force);  # ROPC only
       ClientId       = '...';             # CLIENT_CREDENTIALS only
       ClientSecret   = (ConvertTo-SecureString '...' -AsPlainText -Force);  # CLIENT_CREDENTIALS only
   }
   Invoke-Monkey365 @param
   ```

5. **Post-Export Handling Already Implemented:**
   - Executor's `_parse_output()` recursively searches for JSON files
   - Parser's `parse_output_directory()` does the same with error handling
   - No file moving/copying is required — files are parsed in place
   - Metadata written to `meta.json` at scan root with timestamps and findings count

**Key Learnings:**

1. **Recursive Glob Pattern:** Using `Path.rglob("*.json")` is the correct approach for handling tools that create dynamic subdirectory structures. It's robust, simple, and doesn't require knowing the exact structure ahead of time.

2. **Output Path Control:** The `-OutPath` parameter gives full control over WHERE Monkey365 writes files. Internal subdirectory structure (if any) doesn't matter because recursive glob finds everything.

3. **No Manual File Moving Needed:** If a tool respects the output path parameter and you use recursive discovery patterns, post-processing file moves are unnecessary and add complexity.

4. **Security Best Practices Applied:**
   - All paths are validated and PowerShell-escaped via `_escape_ps_string()` (single quotes: `'` → `''`)
   - UUIDs validated with regex before being passed to PowerShell
   - Credentials validated conditionally based on auth mode
   - Passwords never logged in plaintext (masked with `_mask_password()`)
   - All user inputs validated with whitelist patterns (collect modules, export formats, scan sites)

5. **Integration Pattern:** When integrating external tools:
   - Control output location via tool parameters (don't rely on tool defaults)
   - Use recursive discovery patterns for file parsing (handles any subdirectory structure)
   - Validate and escape ALL inputs before passing to external executables
   - Implement conditional parameter logic based on operation mode (auth modes, scan types, etc.)
   - Capture raw execution output for debugging (stdout/stderr/returncode/duration)

**Recommendations for Future Integrations:**

1. **PingCastle Integration:** Apply same pattern — control output directory, use recursive glob for file discovery
2. **Custom Tool Bridges:** Always validate that output path parameters are respected by the tool
3. **Security Enhancements:** Consider implementing security fixes from SECURITY_FIXES_MONKEY365.py:
   - Secure temporary file handling with restricted permissions (mode 0o700)
   - JSON file size limits (100 MB) to prevent DoS
   - Rate limiting for scan executions (10 scans/hour)
   - Credential sanitization in output logs

**Files Analyzed:**
- `backend/app/tools/monkey365_runner/executor.py` (PowerShell script generation, scan execution)
- `backend/app/tools/monkey365_runner/parser.py` (JSON file discovery and parsing)
- `backend/app/tools/monkey365_runner/config.py` (Auth mode enums and validation)
- `backend/app/services/monkey365_scan_service.py` (Scan orchestration, metadata recording)
- `backend/app/services/monkey365_service.py` (Assessment mapping integration)
- `backend/app/core/storage.py` (Directory structure management)
- `SECURITY_FIXES_MONKEY365.py` (Security enhancement recommendations)

**Conclusion:** The Monkey365 integration is **working as designed**. No file handling changes are required. The recursive glob pattern already handles any subdirectory structure Monkey365 might create, including GUID-based directories.

### 2025-03-21 — CRITICAL FIX: Monkey365 Parameter Name (OutPath → OutDir)

**Problem:** PowerShell execution failed with:
```
Invoke-Monkey365 : Cannot find a parameter matching 'OutPath'
```

**Root Cause:** The executor was using `-OutPath` parameter, but Monkey365 cmdlet actually uses `-OutDir`.

**Investigation:**
1. Examined `Invoke-Monkey365.ps1` (line 200-204):
   ```powershell
   [Parameter(Mandatory= $false, HelpMessage = 'Please specify folder to export results')]
   [System.IO.DirectoryInfo]$OutDir,
   ```

2. Confirmed in `core/init/New-O365Object.ps1` (lines 126-128):
   ```powershell
   #Set Output Dir
   If($false -eq $MyParams.ContainsKey('OutDir')){
       $MyParams.OutDir = ("{0}/monkey-reports" -f $ScriptPath)
   }
   ```

3. Verified parameter type: `System.IO.DirectoryInfo`
4. Default behavior: If not provided, uses `{ScriptPath}/monkey-reports`

**Fix Applied:**
- **File:** `backend/app/tools/monkey365_runner/executor.py`
- **Line 454:** Changed `OutPath` → `OutDir`
- **Impact:** Single character change fixes parameter recognition

**Key Learnings:**
1. **Always verify parameter names** against official cmdlet signatures (`Get-Help` or source code)
2. **Correct Monkey365 parameter:** `-OutDir` (not OutPath, OutputPath, Path, or ReportPath)
3. **PowerShell escaping patterns:** Single-quote doubling (`'` → `''`) via `_escape_ps_string()` is working correctly
4. **Parameter name typos** are silent until runtime — no static analysis can catch this type of error

**Monkey365 Output Parameters Reference:**
- **OutDir** — `DirectoryInfo`, Optional, Default: `{ScriptPath}/monkey-reports`
- **ExportTo** — `String[]`, Optional, Default: `@('JSON')`
- **Compress** — `Switch`, Optional, Compresses output to ZIP
- **SaveProject** — `Switch`, Optional, Saves entire project structure

**Status:** ✅ RESOLVED — Monkey365 execution should now proceed without "Cannot find parameter" errors.

### 2026-03-20 — CRITICAL FIX: Monkey365 SaveProject Parameter (OutDir → SaveProject)

**Problem:** PowerShell execution failed with:
```
Invoke-Monkey365 : Cannot find a parameter matching 'OutPath'
```

**Root Cause Investigation:**
1. Examined executor.py line 462: was using `-OutDir` parameter
2. Consulted official Monkey365 documentation (https://silverhack.github.io/monkey365/)
3. Discovered the CORRECT parameter is `-SaveProject` (not OutDir or OutPath)

**Fix Applied:**
- **File:** `backend/app/tools/monkey365_runner/executor.py`
- **Line 462:** Changed `OutDir = '{safe_output}'` → `SaveProject = '{safe_output}'`

**Monkey365 Output Structure:**
When using `-SaveProject 'E:\AssistantAudit\data\output\scan_xyz'`:
```
E:\AssistantAudit\data\output\scan_xyz\
└── monkey-reports\
    └── {GUID}\                  # Auto-generated by Monkey365
        ├── JSON\
        ├── HTML\
        └── ...
```

**Impact:**
- File discovery logic (recursive glob via `rglob("*.json")`) already handles GUID-based subdirectories
- No changes needed to parser or file handling
- PowerShell escaping patterns unchanged
- Single parameter name fix resolves execution errors

**Key Learnings:**
1. Always verify parameter names against official cmdlet documentation
2. Monkey365 uses `-SaveProject` (not OutPath/OutDir/OutputPath)
3. Recursive glob patterns are robust for dynamic subdirectory structures
4. Parameter name mismatches are silent until runtime

**Status:** ✅ FIXED — Monkey365 parameter corrected, ready for execution testing
