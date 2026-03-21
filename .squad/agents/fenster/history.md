# Fenster — Session History

## Project Knowledge

- AssistantAudit audits infrastructure: Firewalls, Switches, AD, M365, servers
- 12 frameworks drive audit criteria (YAML config files)
- Framework sync: fetch YAML, parse, validate SHA-256, store in database
- Backend exposes REST API for frontend consumption
- Auth: JWT-based, stateless, no server sessions

## Patterns

(To be filled as work progresses)

## Key Files

- App entry: `backend/main.py` or `backend/app/main.py`
- Models: `backend/app/models/`
- API routes: `backend/app/api/`
- Framework sync: `backend/app/services/framework_sync.py` (or similar)
- Database config: `backend/app/database.py`

## Learnings

(To be filled as work progresses)
