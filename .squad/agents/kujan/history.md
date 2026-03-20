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

## Security Reviews Conducted

### **2026-03-19 — Monkey365 Authentication System (4 auth modes)**

**Trigger:** Auto-triggered review — Redfoot rewrote Monkey365 auth with subprocess calls and user credentials

**Scope:**
- `backend/app/tools/monkey365_runner/executor.py` (PowerShell script generation)
- `backend/app/schemas/scan.py` (Monkey365ConfigSchema validation)
- `backend/app/api/v1/tools.py` (Monkey365 endpoints)
- `backend/app/services/monkey365_scan_service.py` (service layer)
- `backend/app/models/monkey365_scan_result.py` (data model)

**Findings:** 8 findings total (0 BLOCKING, 3 HIGH, 3 MEDIUM, 2 LOW)

**Critical Security Observations:**
1. ✅ **Command injection fully mitigated** — UUID regex + email validation + PowerShell single-quote escaping
2. ✅ **Credentials never logged in plaintext** — `_mask_password()` used consistently
3. ✅ **Credentials NOT stored in database** — excluded from `config_snapshot` JSON field
4. ⚠️ **HIGH (S2):** PowerShell script files with plaintext credentials written to disk, cleaned up in `finally` — recommend `-Command` instead of `-File` to avoid disk entirely
5. ⚠️ **HIGH (S1):** Credentials passed to background thread via `config.model_dump()` — verify no inadvertent serialization
6. ⚠️ **MEDIUM (S5):** `provider` field is free-text string, should be enum-constrained like `auth_mode`

**Positive Controls Identified:**
- Auth-mode-specific credential validation (Pydantic `@model_validator`)
- JWT + RBAC authorization (`get_current_auditeur`)
- Allowlist validation for collect modules, export formats, scan sites
- 1-hour subprocess timeout
- Conditional PowerShell parameter generation (no credentials for INTERACTIVE/DEVICE_CODE)

**Approval:** ✅ **APPROVED WITH CONDITIONS** — S1, S2, S5 must be fixed before production

**Report Location:** `.squad/decisions/inbox/kujan-monkey365-security.md`

**Lessons Learned:**
- Subprocess scripts containing credentials are HIGH RISK even with cleanup — prefer stdin or environment variables
- Defense-in-depth validation (schema + executor) is good practice but creates DRY risk — document clearly
- PowerShell single-quote escaping (`'` → `''`) is correct for single-quoted strings (verified secure)
- Masking credentials in logs is not enough — also sanitize subprocess error output

---

### **2026-03-20 — Monkey365 Critical Fixes Hotfix Review**

**Trigger:** Requested by T0SAGA97 — Quick security review of 3 critical Redfoot fixes

**Scope:**
- Timezone bug fix (monkey365_scan_service.py:156-163)
- PowerShell output capture to JSON (executor.py:526-536, 553-562)
- Monkey365 auto-install + module loading (executor.py:269-330)

**Findings:** 5 findings total (0 BLOCKING, 0 HIGH, 2 MEDIUM, 3 LOW)

**Critical Security Assessment:**
1. ✅ **Timezone fix is correct** — Conditional conversion only if naive, uses `timezone.utc`, fallback logic sound
2. ✅ **PowerShell output capture is safe** — stdout/stderr don't contain credentials (Monkey365 outputs audit data), no injection, JSON properly encoded
3. ✅ **Git clone is secure** — HTTPS only, `--depth=1` shallow clone, hardcoded URL (no user input), proper error handling, no shell=True
4. ✅ **Script file handling unchanged** — Still deleted in `finally` block (known limitation from S2 in previous review)
5. ✅ **Input validation before script gen** — All auth parameters validated and escaped

**Positive Observations:**
- 21 comprehensive test cases covering all three fixes (9 timezone + 5 output + 7 module)
- Test coverage excellent (all path: success, failure, edge cases)
- Conditional PowerShell parameters still working (no credentials for INTERACTIVE/DEVICE_CODE)
- Subprocess timeout remains 3600s
- Array-based subprocess calls (no shell=True)

**Approval:** ✅ **APPROVED — No blockers**

**Conditions for production:**
1. Document `powershell_raw_output.json` is internal diagnostics (not user-facing)
2. Preventive: Ensure all `Monkey365ScanResult.created_at` uses `datetime.now(timezone.utc)` by default
3. Future optimization: Consider `-Command` for credential-free modes

**Report Location:** `.squad/decisions/inbox/kujan-blocker-review.md`

**Key Insight:**
- Redfoot's fixes are production-ready — all three address real bugs without introducing new security risks
- PowerShell output capture is safe because Monkey365 doesn't output credentials
- Timezone fix prevents silent duration calculation failures
- Auto-install pattern is standard and secure (GitHub HTTPS clone + local verification)
- Previous HIGH findings (S1, S2) remain acknowledged but outside scope of this hotfix review
