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

### 2026-03-20 — EPIC 3 Wiki Structure Completion

**Task:** Merge Baer's EPIC 3 completion report and commit all Wiki pages to GitHub.

**Actions Completed:**
1. ✅ Merged `.squad/decisions/inbox/baer-epic3-wiki-structure.md` into `decisions.md`
2. ✅ Deleted inbox file after merge
3. ✅ Navigated to `D:\AssistantAudit.wiki\`
4. ✅ Staged all 9 Wiki pages (5,602 insertions)
5. ✅ Committed with detailed message referencing EPIC 3 and Sprint 0 audit integration
6. ✅ Returned to main repo `D:\AssistantAudit`

**Wiki Pages Committed:**
- Home.md, Architecture.md, API-Reference.md
- Frameworks.md, Tool-Integrations.md, Network-Mapping.md
- Deployment-Guide.md, Development-Guide.md, Security-Notes.md

**Commit Hash:** ad4b48c

**Status:** EPIC 3 GitHub Wiki structure complete and committed. Ready for push to remote.
