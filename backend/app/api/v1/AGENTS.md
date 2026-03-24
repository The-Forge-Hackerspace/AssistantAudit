# API v1 ROUTE DEFINITIONS

## OVERVIEW
This directory contains the FastAPI `APIRouter` definitions for version 1 of the REST API.

## ROUTE FILES

| File | Prefix | Purpose |
|------|--------|---------|
| `router.py` | `/api/v1` | Root router including all sub-routers |
| `auth.py` | `/auth` | Authentication, tokens, profile |
| `entreprises.py` | `/entreprises` | Company management |
| `sites.py` | `/sites` | Site management (under entreprise) |
| `equipements.py` | `/equipements` | Equipment management (under site) |
| `audits.py` | `/audits` | Audit management |
| `assessments.py` | `/assessments` | Control results per audit |
| `frameworks.py` | `/frameworks` | Compliance framework listing |
| `scans.py` | `/scans` | Network scan management |
| `attachments.py` | `/attachments` | Evidence file management |
| `health.py` | `/health` | API health check |
| `network_map.py` | `/network-map` | Topology data |
| `tools.py` | `/tools` | General tool endpoints |
| `pingcastle_terminal.py` | `/pingcastle` | WebSocket for PingCastle |
| `tools/` | `/tools/*` | Tool-specific route subdirectory |

## PATTERN: ADDING AN ENDPOINT

1. Create a new file (e.g., `new_feature.py`) and define an `APIRouter`:
   ```python
   router = APIRouter(prefix="/new-feature", tags=["New Feature"])
   ```
2. Import the router in `router.py`.
3. Add `api_router.include_router(new_feature.router)` to the `api_router` instance.

## AUTHENTICATION DEPENDENCIES

Protect routes using dependencies from `core/deps.py`:
- `Depends(get_current_user)`: Validates JWT token.
- `Depends(require_role("admin"))`: Enforces role-based access control.

Example:
```python
@router.post("/", dependencies=[Depends(require_role("admin"))])
async def create_item(): ...
```
