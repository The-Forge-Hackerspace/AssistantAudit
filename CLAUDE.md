# AssistantAudit

## Overview
IT security auditing platform. FastAPI backend, Next.js 16 frontend.

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

### Full stack (Windows)
```powershell
.\start.ps1 --dev    # Development mode
.\start.ps1 --build  # Production build
```

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
