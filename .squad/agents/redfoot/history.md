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
