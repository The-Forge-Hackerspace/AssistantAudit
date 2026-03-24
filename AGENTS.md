# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-22
**Commit:** 11598c2
**Branch:** AddM365withMonkey365

## OVERVIEW

IT security auditing platform — FastAPI backend (Python 3.13), Next.js 16 frontend (React 19 + TypeScript), 12 YAML compliance frameworks (200+ controls), 7 integrated audit tools (Nmap, SSL checker, SSH/WinRM collectors, AD auditor, PingCastle, Monkey365, config parsers). SQLite dev, PostgreSQL planned.

## STRUCTURE

```
AssistantAudit/
├── backend/              # FastAPI Python app
│   ├── app/              # Application code (see backend/app/AGENTS.md)
│   │   ├── api/v1/       # REST endpoints (45 routes, versioned)
│   │   ├── core/         # Cross-cutting: config, DB, auth, metrics, logging
│   │   ├── models/       # SQLAlchemy ORM models (16 models)
│   │   ├── schemas/      # Pydantic v2 request/response schemas
│   │   ├── services/     # Business logic layer (12 services)
│   │   └── tools/        # 7 external tool integrations
│   ├── tests/            # pytest suite (see backend/tests/AGENTS.md)
│   ├── alembic/          # Database migrations
│   ├── init_db.py        # DB init + default admin creation
│   └── requirements.txt  # Python dependencies
├── frontend/             # Next.js App Router
│   └── src/              # Source (see frontend/src/AGENTS.md)
│       ├── app/          # Pages: dashboard, audits, entreprises, outils, login...
│       ├── components/   # UI components (shadcn/ui + custom)
│       ├── contexts/     # React contexts (auth)
│       ├── hooks/        # Custom hooks (useApi, useMobile)
│       ├── lib/          # Utilities, API client, constants
│       ├── services/     # API service layer
│       └── types/        # TypeScript type definitions
├── frameworks/           # 12 YAML audit referentials (see frameworks/AGENTS.md)
├── tools/                # Vendored: Monkey365 PowerShell tool (do NOT edit)
├── .squad/               # AI team orchestration (agents, routing, templates)
├── .github/              # CI workflows (squad triage/labels only — NO build/test CI)
├── start.ps1             # Windows PowerShell orchestrator (venv + deps + alembic + uvicorn + next)
└── .env.example          # Environment template
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/app/api/v1/` | Create route file, register in `router.py` |
| Add DB model | `backend/app/models/` | SQLAlchemy model, then `alembic revision --autogenerate` |
| Add schema | `backend/app/schemas/` | Pydantic v2 model, import in endpoint |
| Add business logic | `backend/app/services/` | Service class, inject via `deps.py` |
| Add audit tool | `backend/app/tools/` | Create subpackage, add service + API route |
| Add frontend page | `frontend/src/app/{route}/page.tsx` | Next.js App Router convention |
| Add UI component | `frontend/src/components/` | Custom in root, shadcn in `ui/` |
| Add compliance framework | `frameworks/` | YAML file, auto-synced to DB at startup |
| Configure environment | `.env` (root) | Copy from `.env.example` |
| Database migrations | `backend/alembic/` | `alembic revision --autogenerate -m "desc"` |
| Run tests | `backend/tests/` | `pytest -q` from `backend/` |

## CONVENTIONS

- **Language**: Comments, docstrings, and UI text are in **French** — code identifiers in English
- **Backend pattern**: Router → Service → Model (no direct DB in routes)
- **Auth**: JWT with 15min access + 7-day refresh tokens; roles: `admin`, `auditeur`, `lecteur`
- **Framework sync**: YAML files in `frameworks/` auto-sync to DB on startup via SHA-256 hash comparison
- **Config**: Pydantic `BaseSettings` loading from root `.env` — see `backend/app/core/config.py`
- **Frontend imports**: Path alias `@/` → `./src/` (tsconfig paths)
- **UI library**: shadcn/ui components in `frontend/src/components/ui/` — do NOT modify directly
- **No Docker**: Despite README claims, no Dockerfile/docker-compose exists yet
- **Windows-first**: `start.ps1` is the primary dev orchestrator; no Linux/macOS equivalent

## ANTI-PATTERNS (THIS PROJECT)

- **NEVER commit `.env`, `venv/`, `.venv/`, `__pycache__/`, `frontend/.next/`, `frontend/tmp/`** — some are currently in repo (known debt)
- **NEVER use `shell=True`** in subprocess calls — command injection risk; use argument lists
- **NEVER bypass SSL validation** in production — WinRM SSL disabled in dev (TODO: fix before prod)
- **NEVER modify `tools/monkey365/`** — vendored external tool; update via git pull only
- **NEVER suppress type errors** with `as any` or `@ts-ignore` in frontend
- **NEVER pass SSH private keys as plaintext in API requests** — known security debt, needs redesign
- **NEVER hardcode CORS origins** — should be env-based (currently hardcoded in config.py)

## COMMANDS

```bash
# Backend
cd backend
python -m venv ../venv && source ../venv/bin/activate  # or ..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py                                       # First-time DB + admin setup
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev       # Dev server at :3000
npm run build     # Production build
npm run lint      # ESLint (eslint-config-next defaults)

# Tests
cd backend && pytest -q

# Migrations
cd backend && alembic revision --autogenerate -m "description"
cd backend && alembic upgrade head

# Full stack (Windows only)
.\start.ps1 --dev    # Development mode
.\start.ps1 --build  # Production build mode
```

## NOTES

- **Default admin creds** printed by `init_db.py` / `start.ps1` — change immediately
- **SECRET_KEY** auto-generated in dev; MUST set in `.env` for production
- **SQLite** for dev — PostgreSQL migration planned (change `DATABASE_URL` in `.env`)
- **No CI/CD pipeline** — GitHub workflows are squad/agent triage automation only
- **No frontend tests** — no jest/vitest/playwright configured
- **Monkey365 requires PowerShell 7+** and Windows for full functionality
- **7 npm high-severity vulns** flagged in Sprint 0 audit — unresolved
- **5 N+1 query patterns** in backend — documented in CONCEPT.md known issues
- **API docs**: Swagger UI at `http://localhost:8000/docs`, ReDoc at `/redoc`
