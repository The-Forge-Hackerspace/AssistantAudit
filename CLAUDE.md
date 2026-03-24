# AssistantAudit — Project Knowledge Base

**Last updated:** 2026-03-24

## OVERVIEW

IT security auditing platform. FastAPI backend (Python 3.13), Next.js 16 frontend (React 19 + TypeScript), 12 YAML compliance frameworks auto-synced to SQLite, 7 integrated audit tools (Nmap, SSL checker, SSH/WinRM collectors, AD auditor, PingCastle, Monkey365, config parsers).

- **Backend:** `http://localhost:8000` — Swagger UI at `/docs`, ReDoc at `/redoc`
- **Frontend:** `http://localhost:3000`
- **Database:** SQLite at `backend/instance/assistantaudit.db` (dev) — PostgreSQL planned for production

## STRUCTURE

```
AssistantAudit/
├── backend/              FastAPI Python app (see backend/CLAUDE.md)
├── frontend/             Next.js App Router (see frontend/CLAUDE.md)
├── frameworks/           12 YAML audit referentials — auto-synced to DB at startup
├── tools/monkey365/      Vendored PowerShell tool — do NOT edit; update via git pull only
├── data/                 Monkey365 scan output — NOT committed (add to .gitignore if missing)
├── .env                  Local config — NOT committed in production (copy from .env.example)
├── .env.example          Environment template
├── start.ps1             Windows dev orchestrator (venv + deps + alembic + uvicorn + next dev)
└── install_m365_modules.ps1  One-time PowerShell module installer for Monkey365 dependencies
```

## HOW TO RUN

### Full stack (Windows, recommended)
```powershell
.\start.ps1 --dev    # Development mode with hot-reload
.\start.ps1 --build  # Production build
```

### Manual (backend)
```bash
cd backend
python init_db.py          # First time only: creates tables + default admin user
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Manual (frontend)
```bash
cd frontend
npm install
npm run dev     # http://localhost:3000
npm run build
npm run lint
```

### Tests
```bash
cd backend
pytest -q
pytest tests/test_monkey365_executor.py -v   # specific file
```

### Database migrations
```bash
cd backend
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

## ARCHITECTURE

```
Router (api/v1/)
  └── calls Service (services/)
        └── queries Model (models/) via SQLAlchemy Session
              └── Schema (schemas/) for request/response serialization
```

Endpoints **never** access the database directly. All DB work goes through services.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/app/api/v1/` | Create route file, register in `router.py` |
| Add DB model | `backend/app/models/` | SQLAlchemy mapped class, then `alembic revision --autogenerate` |
| Add Pydantic schema | `backend/app/schemas/` | Pydantic v2 model |
| Add business logic | `backend/app/services/` | Service class, call from router |
| Add audit tool | `backend/app/tools/` | New subpackage + service + API route |
| Add frontend page | `frontend/src/app/{route}/page.tsx` | Next.js App Router |
| Add UI component | `frontend/src/components/` | Custom in root, shadcn primitives in `ui/` |
| Add compliance framework | `frameworks/` | YAML file, auto-synced to DB at next startup |
| Configure environment | `.env` (root) | Copy from `.env.example` |

## LANGUAGE CONVENTIONS

- **UI text, user-facing strings, comments, docstrings:** French
- **Code identifiers, variables, function names:** English
- Applies to both backend Python and frontend TypeScript/React

## AUTH

- JWT: 15-minute access tokens + 7-day refresh tokens
- Roles: `admin` > `auditeur` > `lecteur` (hierarchy enforced in `core/deps.py`)
- Frontend stores tokens in js-cookie (`sameSite=strict`, non-httpOnly)
- Rate limiter on `POST /auth/login`: 5 attempts/minute, 5-minute block

## KEY ENVIRONMENT VARIABLES

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | auto-generated | JWT signing key — MUST be set explicitly in production |
| `DATABASE_URL` | `sqlite:///instance/assistantaudit.db` | DB connection string |
| `ENV` | `development` | `development` / `testing` / `production` |
| `MONKEY365_PATH` | `""` | Absolute path to `Invoke-Monkey365.ps1` |
| `MONKEY365_ARCHIVE_PATH` | `/data/enterprise/Cloud/M365` | Archive base for scan results |
| `PINGCASTLE_PATH` | `""` | Absolute path to `PingCastle.exe` |
| `LOG_LEVEL` | `INFO` | `DEBUG` in dev |
| `CORS_ORIGINS` | `localhost:3000,5173` | Comma-separated allowed origins |

## ANTI-PATTERNS — NEVER DO THESE

- **NEVER commit `.env`** — use `.env.example` for documentation only
- **NEVER use `shell=True`** in subprocess calls — use argument lists
- **NEVER use `stdout=None, stderr=None`** when you need to capture output — use `capture_output=True` for non-interactive modes; omit entirely for interactive/device-code modes so prompts remain visible
- **NEVER hardcode absolute Windows paths** in Python source — derive from `Path(__file__)` or `settings`
- **NEVER modify `tools/monkey365/`** — vendored; update via `git pull` only
- **NEVER suppress TypeScript errors** with `as any` or `@ts-ignore`

## KNOWN TECHNICAL DEBT

- `executor.py:11` hardcodes `D:\AssistantAudit` fallback path — must be derived from settings
- `executor.py:210-218` uses `stdout=None, stderr=None` — PowerShell errors are invisible to the app
- SSH private keys transmitted as plaintext in API request bodies (`schemas/scan.py`)
- `.env` was committed to git; verify it is excluded and remove from history if needed
- `data/` directory may contain real company names in git history
- `network-map/page.tsx` is ~2,900 lines — needs component extraction
- CORS origins hardcoded as defaults in `config.py` — should be required from environment in production
- Rate limiter is in-process only — breaks with multiple uvicorn workers
- No frontend tests (no jest/vitest/playwright configured)
- Monkey365 requires interactive desktop MSAL auth — not compatible with headless servers

## NOTES

- Default admin credentials are printed by `init_db.py` / `start.ps1` — change on first login
- Monkey365 requires PowerShell 7+ (`pwsh`) in PATH on Windows
- No Docker — despite README references, no Dockerfile exists
- No CI build/test pipeline — `.github/workflows/` contains squad triage only
