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

## Documentation Updates

**2026-03-19 16:29 — Monkey365 Authentication Modes Documentation**
- Added "Authentication Modes" section to CONCEPT.md Phase 4b (Monkey365)
- Documents 4 auth methods: Interactive Browser, Device Code, ROPC, Client Credentials
- Clarifies which modes require credentials vs. browser popup
- Notes implementation details: Pydantic validation, conditional PowerShell generation, password masking
- No existing Known Issues found for Monkey365 auth (bug fix verified)
- Decision: baer-monkey365-docs.md

**2026-03-19 17:00 — Monkey365 Verified Workflow Documentation**
- Added "Verified Workflow" subsection to CONCEPT.md § 🐒 Détail technique (after Installation)
- Documents end-to-end scan flow: auto-install (--depth=1) → module verification → PowerShell generation → browser interactive mode
- Real-time frontend logs (2s polling) + raw output capture (powershell_raw_output.json) + status updates (SUCCESS/FAILED)
- Documents 3 critical bug fixes: timezone offset-aware, silent failures, module loading auto-recovery
- Store location: D:\AssistantAudit\tools\monkey365 (verified)
- Decision: baer-blocker-docs.md (verified workflow)
