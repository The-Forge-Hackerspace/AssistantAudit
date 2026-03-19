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
