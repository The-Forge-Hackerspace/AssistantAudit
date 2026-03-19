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

## Sprint 0 Validation (2026-03-19)

**Sprint Structure:** Three sequential epics with EPIC 1 (audits) executing in parallel across 7 independent workstreams.

**Validation Outcome:**
- ✅ All 7 audit agents available and unblocked
- ✅ EPIC 1 (45-endpoint backend, tools, DB, frontend, security, DevSecOps, infrastructure audits) approved for parallel execution
- ✅ No hard data dependencies between audit workstreams confirmed
- ✅ Business alignment confirmed (audit → documentation → wiki enables Phase 4 continuation)
- ✅ Sequential EPIC dependencies (EPIC 1 → 2 → 3) are clean with clear gating

**Key Decision:** Established daily async stand-up + weekly PO sync for conflict resolution during parallel audit execution.

**Process Insight:** Parallel audit execution works because each agent has isolated domain scope and audit findings are independent (no agent's output is prerequisite for another's input). Baer can begin documentation drafting concurrently with EPIC 1 findings.

**Outcome Document:** `.squad/decisions/inbox/verbal-sprint0-validation.md`
