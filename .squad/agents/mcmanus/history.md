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

### 2026-03-19 — Monkey365 Authentication Mode Tests

**Completed:** Full test suite for Monkey365 authentication modes (4 modes × comprehensive coverage).

**File Created:** `backend/tests/test_monkey365_auth_modes.py` (23 tests, 100% pass rate)

**Coverage:**
1. **Interactive Mode:** Validates no credentials required, PowerShell script generation without credentials
2. **Device Code Mode:** Validates no credentials required, correct PowerShell parameter generation
3. **Client Credentials Mode:** 
   - Tests all 3 fields required (tenant_id, client_id, client_secret)
   - Tests missing field scenarios (each field individually)
   - Tests UUID validation for tenant_id/client_id
   - Tests PowerShell script generation with all credentials
   - Tests password masking in logs (***) 
4. **ROPC Mode:**
   - Tests all 3 fields required (tenant_id, username, password)
   - Tests missing field scenarios (each field individually)
   - Tests email validation for username
   - Tests empty password rejection
   - Tests PowerShell script generation with username/password
   - Tests password masking in logs (***)

**Edge Cases Covered:**
- Invalid auth_mode rejection
- Invalid UUID format detection
- Invalid email format detection
- Empty password handling
- Password masking for security (logs never show plaintext)

**Key Learning:** The `Monkey365Config` dataclass in `executor.py` uses conditional validation logic in the `validate()` method. Each auth mode has different credential requirements enforced at validation time, not at instantiation. This allows the config object to be created with partial data and validated later.

**Testing Pattern:** Used `Monkey365Executor.__new__()` to create mock executor instances without full initialization, allowing direct access to `build_script()` method for PowerShell generation testing without requiring the actual Monkey365 installation.

### 2026-03-20 — Monkey365 Timezone & Executor Regression Tests

**Completed:** Added regression coverage for timezone-aware duration handling, PowerShell output capture, auto-install directory creation, and module import checks.
