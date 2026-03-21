# Keaton — Session History

## Plugin Installations

- 📦 Plugin `software-engineering-team` installed from `github/awesome-copilot` (2026-03-21) — agent templates: `se-security-reviewer`, `se-system-architecture-reviewer`, `se-gitops-ci-specialist`, `se-product-manager-advisor`, `se-responsible-ai-code`, `se-technical-writer`, `se-ux-ui-designer`
- 📦 Plugin `security-best-practices` installed from `github/awesome-copilot` (2026-03-21) — skill: `ai-prompt-engineering-safety-review`
- 📦 Plugin `typescript-mcp-development` installed from `github/awesome-copilot` (2026-03-21) — skill: `typescript-mcp-server-generator`

## Project Knowledge

- AssistantAudit targets infrastructure security: Firewalls, Switches, AD, M365, Windows/Linux
- Framework-driven: 12 YAML frameworks define audit criteria, synchronized via SHA-256
- Backend stateless auth (JWT/OAuth2) — no server sessions
- Frontend: Next.js SSR with Tailwind + shadcn/ui components
- Database: Pydantic v2 validation, SQLAlchemy 2.0 ORM, PostgreSQL for production

## Patterns

(To be filled as work progresses)

## Key Files

- Framework definitions: `data/` directory
- Backend models: `backend/app/models/`
- API routes: `backend/app/api/`
- Frontend pages: `frontend/app/`

## Learnings

### 2026-03-20: Comprehensive Architectural Audit

**Project Structure:**
- 15 SQLAlchemy models → 24 total entities (with polymorphic Equipment hierarchy)
- 45 REST API endpoints across 14 route modules
- 7 integrated security tools (3,903 LOC total)
- 14 YAML frameworks (12 production + 2 test variants)
- 17 frontend pages (Next.js App Router)
- 7 Alembic migrations applied

**Core Architecture Patterns:**
1. **Framework Sync Engine** — SHA-256 hash-based YAML synchronization at startup
   - Files are source of truth, database is synchronized cache
   - Idempotent sync (detect new/updated/unchanged via hash comparison)
   - Auto-import on startup + manual trigger via POST /frameworks/sync

2. **Assessment Flow** — Audit → Campaign → Assessment → ControlResult
   - Campaign aggregates assessments for an audit
   - Assessment links equipement + framework
   - ControlResult stores compliance status per control
   - Compliance scoring: compliant=1.0, partial=0.5, non_compliant=0.0

3. **Tool Integration Pattern** — Executor → Parser → Mapper
   - Executor: Subprocess runner with timeout + security validation
   - Parser: JSON/XML parsing with multiple schema variants
   - Mapper: Finding → ControlResult mapping via engine_rule_id

4. **Auth Architecture** — Stateless JWT with rate limiting
   - 15-min access tokens, 7-day refresh tokens (HS256)
   - bcrypt password hashing (12 rounds, no passlib)
   - In-memory rate limiter (5 attempts/60s → 300s block)
   - Role-based access: admin | auditeur | lecteur

**Key Files & Purposes:**
- `backend/app/main.py` — Application factory with lifespan hooks (startup: framework sync, metrics, Sentry)
- `backend/app/core/database.py` — SQLAlchemy 2.0 engine + session factory (SQLite dev, PostgreSQL prod)
- `backend/app/services/framework_service.py` — SHA-256 sync engine (import/update/export YAML)
- `backend/app/services/assessment_service.py` — Compliance scoring + campaign lifecycle
- `backend/app/tools/monkey365_runner/` — PowerShell executor + JSON parser + finding mapper
- `frontend/src/lib/api-client.ts` — Axios instance with JWT interceptor + 401 handling
- `frontend/src/contexts/auth-context.tsx` — Global auth state (React Context API)
- `frontend/src/services/api.ts` — Typed API wrapper for all 45 endpoints

**Tech Decisions & Rationale:**
1. **SQLite dev / PostgreSQL prod** — Fast local dev, scalable production
2. **SHA-256 framework hashing** — Deterministic sync, tamper detection, GitOps-ready
3. **Pydantic v2 + SQLAlchemy 2.0** — Modern type safety, validation at boundaries
4. **Next.js 16 App Router** — File-system routing, server components, Turbopack
5. **shadcn/ui (copy-paste)** — Full control, no version lock-in, Tailwind v4 compatible
6. **Axios over fetch** — Interceptors for JWT injection, better error handling
7. **SWR for data fetching** — Automatic revalidation, cache management, loading states

**Architecture Strengths:**
- ✅ SHA-256 framework sync (elegant "code vs. data" solution)
- ✅ SQLAlchemy 2.0 type safety (Mapped types prevent errors at dev time)
- ✅ Comprehensive middleware stack (security headers, metrics, audit logging, CORS)
- ✅ Stateless JWT auth (horizontal scaling ready)
- ✅ Tool integration consistency (Executor → Parser → Mapper pattern)
- ✅ Frontend type safety (150+ TypeScript types, strict mode)
- ✅ Separation of concerns (Routes → Services → Models layering)

**Critical Risks Identified:**
1. **N+1 query patterns** (5 locations) — Performance degradation under load
2. **In-memory rate limiting** — Single-instance only, breaks on multi-worker
3. **WinRM SSL validation disabled** — MITM vulnerability (dev mode)
4. **7 high-severity npm vulnerabilities** — Frontend supply chain risk
5. **No unit tests for Nmap whitelist** — Command injection risk if regex bypass
6. **CORS origins hardcoded** — Must edit code for production domains
7. **No refresh token rotation** — 7-day replay attack window

**Recommended Pre-Production Fixes:**
1. P0: Resolve N+1 queries with selectinload() — 10 hours
2. P0: Migrate rate limiting to Redis (slowapi) — 4 hours
3. P0: Fix WinRM SSL validation (CA bundle) — 3 hours
4. P1: Add Nmap whitelist unit tests — 4 hours
5. P1: CORS environment configuration — 1 hour

**Design Boundaries:**
- ✅ Framework-driven audit orchestration (YES)
- ✅ Tool integration hub (YES)
- ❌ Real-time monitoring system (NO)
- ❌ Automated remediation tool (NO)
- ❌ SIEM replacement (NO)

**12 Framework Constraint:**
- Current: 14 YAML files (12 active + 2 test variants)
- No hard limit in code (design goal, not technical constraint)
- System handles 200+ controls without performance issues
- UI may assume ~12 for visual display (needs testing beyond 15)

**Observable Patterns:**
- Consistent dependency injection via Depends()
- Pydantic schemas use ConfigDict(from_attributes=True)
- Services always return domain objects (no raw DB models in routes)
- Frontend uses async/await + try/catch + toast pattern consistently
- Error responses always include {"detail": "...", "error_type": "..."}

**System Maturity Assessment:**
- ✅ Production-ready for: Development, internal audits (5-10 users), pilot deployment
- ⚠️ Requires fixes for: Multi-tenant SaaS, high-concurrency production (>50 concurrent)
- Overall: 🟢 **Strong architecture, 90% production-ready, clear path forward**
