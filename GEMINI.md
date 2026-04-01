# GEMINI.md

## Overview
IT security auditing platform. FastAPI backend, Next.js 16 frontend.
Gemini CLI operates in this project following the conventions below.

## Structure

```
AssistantAudit/
├── backend/              FastAPI Python app
├── frontend/             Next.js App Router
├── frameworks/           YAML audit referentials — auto-synced to DB at startup
├── .env.example          Environment template
└── start.ps1             Windows dev orchestrator
```

## How to run

### Manual (backend)
```bash
cd backend
python init_db.py          # First time only
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Manual (frontend)
```bash
cd frontend
npm install
npm run dev
```

### Tests
```bash
cd backend
pytest -q
```

### Database migrations
```bash
cd backend
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

## Architecture pattern

```
Router (api/v1/)
  └── calls Service (services/)
        └── queries Model (models/) via SQLAlchemy Session
              └── Schema (schemas/) for request/response serialization
```

Endpoints never access the database directly. All DB work goes through services.

## Conventions

- **UI text, user-facing strings, comments, docstrings:** French
- **Code identifiers, variables, function names:** English
- Backend: Synchronous only (no async def on routes/services, except WebSocket handlers)
- Existing DB columns: Never rename — add new columns instead
- Frontend: Next.js 16, React 19, Tailwind CSS v4, shadcn/ui v4
- No `as any` or `@ts-ignore` in TypeScript

## Where to look

| Task | Location |
|------|----------|
| Add API endpoint | `backend/app/api/v1/` |
| Add DB model | `backend/app/models/` |
| Add Pydantic schema | `backend/app/schemas/` |
| Add business logic | `backend/app/services/` |
| Add audit tool | `backend/app/tools/` |
| Add frontend page | `frontend/src/app/{route}/page.tsx` |
| Add UI component | `frontend/src/components/` |
| Add compliance framework | `frameworks/` |

## Critical Rules

| Rule | Context | Detail |
|------|---------|--------|
| **Sync only** | Backend routes/services | No `async def` except WebSocket handlers |
| **No column renames** | Database migrations | Add new columns instead |
| **French UI** | All user-facing text | Comments, docstrings, UI strings in French |
| **English code** | Identifiers | Variables, functions, classes in English |
| **No TS escape hatches** | Frontend | No `as any` or `@ts-ignore` |

## Workflow rules

- Commit after completing a step — format: `feat`/`fix`/`test`/`refactor`/`security`/`chore`/`docs`
- Run tests after each modification
- Show the diff summary before moving to the next step

## Anti-patterns

- Never commit `.env`
- Never use `shell=True` in subprocess calls
- Never suppress TypeScript errors with `as any` or `@ts-ignore`
- Never use `async def` on routes or services (backend is sync)
- Never rename existing DB columns

## MCP Tool Preferences

**PREFER** hex-line MCP for code files when available.

| Instead of | Use | Why |
|-----------|-----|-----|
| `read_file` | `mcp__hex-line__read_file` | Hash-annotated, revision-aware |
| `edit_file` | `mcp__hex-line__edit_file` | Hash-verified anchors |
| `write_file` | `mcp__hex-line__write_file` | No prior read needed |
| `search_files` | `mcp__hex-line__grep_search` | Edit-ready matches |

## Compact Instructions

Preserve during context compression: [Critical Rules], [Where to look table],
[language/communication rules], [hard boundaries (NEVER/ALWAYS)].
Drop examples and explanations first.
