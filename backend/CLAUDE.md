# Backend — Conventions & Architecture

**Path:** `E:\AssistantAudit\backend\`
**Stack:** Python 3.13, FastAPI 0.115+, SQLAlchemy 2, Pydantic v2, Alembic, pytest

## STRUCTURE

```
backend/
├── app/
│   ├── api/v1/           REST endpoints — one file per resource group
│   │   ├── router.py     Aggregates all sub-routers
│   │   ├── auth.py       Login, register, refresh, me
│   │   ├── assessments.py  Campaigns, assessments, control results, M365 scan trigger
│   │   └── tools/        Tool-specific routes (monkey365.py, pingcastle.py, collect.py, ...)
│   ├── core/             Infrastructure — do NOT add business logic here
│   │   ├── config.py     Pydantic Settings — single source of truth for all config
│   │   ├── database.py   SQLAlchemy engine, SessionLocal, Base, get_db()
│   │   ├── deps.py       FastAPI Depends: get_current_user, get_current_auditeur, PaginationParams
│   │   ├── security.py   bcrypt hashing, JWT create/decode
│   │   ├── rate_limit.py In-process login rate limiter (5 attempts/min)
│   │   ├── storage.py    Scan output path utilities (slugify, ensure_scan_directory)
│   │   └── exception_handlers.py  Global error handlers
│   ├── models/           SQLAlchemy ORM — 16 entities
│   ├── schemas/          Pydantic v2 request/response shapes
│   ├── services/         Business logic — 12 service classes
│   ├── tools/            External tool runners (monkey365_runner/, ad_auditor/, ...)
│   └── main.py           FastAPI app factory + lifespan
├── tests/                pytest suite (see tests/AGENTS.md)
├── alembic/              Migrations
├── alembic.ini
├── init_db.py            DB init + default admin creation
└── requirements.txt
```

## ARCHITECTURE RULE

```
Router → Service → Model
```

- **Routers** (`api/v1/*.py`): Validate schema, call one service method, return response. No DB queries.
- **Services** (`services/*.py`): Business logic, DB queries, external calls. Raise `ValueError` for domain errors (caught globally as 400).
- **Models** (`models/*.py`): SQLAlchemy mapped classes. No business logic.
- **Schemas** (`schemas/*.py`): Pydantic v2 `BaseModel`. Separate `Create`, `Read`, `Summary`, `Update` variants.

## DEPENDENCY INJECTION

Standard pattern for an authenticated auditeur endpoint:

```python
@router.post("/resource", response_model=ResourceRead, status_code=201)
async def create_resource(
    body: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    return ResourceService.create(db, body, current_user.username)
```

Available deps (all in `core/deps.py`):
- `get_db` → `Session`
- `get_current_user` → `User` (any authenticated user)
- `get_current_auditeur` → `User` (role: admin or auditeur)
- `get_current_admin` → `User` (role: admin only)
- `PaginationParams` → `.page`, `.page_size`, `.offset`

## MODELS

All models inherit from `core.database.Base`. Use `Mapped[T]` + `mapped_column()` (SQLAlchemy 2 style). Always use `DateTime(timezone=True)` for timestamps:

```python
from datetime import datetime, timezone

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
```

After adding/changing a model:
```bash
alembic revision --autogenerate -m "add_field_to_model"
alembic upgrade head
```

## SCHEMAS

- Use Pydantic v2
- Set `model_config = {"from_attributes": True}` on all `Read` schemas
- Validate constrained inputs with `pattern=` or `field_validator`
- Keep `Create`, `Read`, `Summary`, `Update` schemas separate

## CONFIGURATION

All config comes from `core/config.py` (`Settings` class backed by `pydantic-settings`). Never use `os.environ` directly:

```python
from app.core.config import get_settings
settings = get_settings()  # @lru_cache singleton
```

## 16 DATABASE MODELS

`user`, `entreprise`, `site`, `equipement`, `audit`, `framework` (+ `category`, `control`), `assessment` (+ `campaign`, `control_result`), `attachment`, `scan` (+ `scan_host`, `scan_port`), `collect_result`, `config_analysis`, `ad_audit_result`, `network_map` (+ `network_link`, `vlan_definition`, `site_connection`), `pingcastle_result`, `monkey365_scan_result`

## 12 SERVICES

| Service | Responsibility |
|---------|---------------|
| `auth_service` | Login, password hashing, JWT creation |
| `assessment_service` | Campaign/assessment CRUD, compliance scoring |
| `framework_service` | YAML sync via SHA-256 comparison |
| `scan_service` | Nmap scan lifecycle |
| `collect_service` | SSH/WinRM data collection (Linux, OPNsense, Stormshield, Fortinet) |
| `config_analysis_service` | Firewall config parsing |
| `ad_audit_service` | LDAP-based Active Directory auditing |
| `pingcastle_service` | PingCastle runner |
| `monkey365_service` | M365 scan → assessment mapping (legacy flow) |
| `monkey365_scan_service` | M365 scan lifecycle + background thread |
| `query_optimizer` | N+1 query helpers |

## TESTING

```bash
cd backend
pytest -q                                         # all tests
pytest tests/test_monkey365_executor.py -v        # specific file
pytest -k "monkey365"                             # by keyword
```

Fixtures (all in `tests/conftest.py`):
- `db_session` — in-memory SQLite, fresh per test
- `client` — `TestClient` with `get_db` overridden
- `admin_headers`, `auditeur_headers`, `lecteur_headers` — valid JWT headers
- `admin_user`, `auditeur_user`, `lecteur_user` — pre-created User objects

Standard test pattern:
```python
def test_create_something(client, auditeur_headers):
    response = client.post("/api/v1/resource", json={...}, headers=auditeur_headers)
    assert response.status_code == 201
    assert response.json()["field"] == "expected"
```

## MONKEY365 INTEGRATION

Entry point: `Monkey365ScanService.launch_scan()`

1. Creates `Monkey365ScanResult` in DB with `status=RUNNING`
2. Spawns daemon thread → `execute_scan_background()`
3. Thread instantiates `Monkey365Executor` with `settings.MONKEY365_PATH`
4. Executor calls `ensure_monkey365_ready()` (checks psm1, auto-clones if missing)
5. Writes a PS1 script to a temp file; calls `pwsh -NoProfile -ExecutionPolicy Bypass -File <path>`
6. I/O strategy: interactive/device_code modes inherit parent stdio (browser/prompt visible); ropc/client_credentials use `capture_output=True`
7. After subprocess returns, archives `monkey-reports/{GUID}/` to `MONKEY365_ARCHIVE_PATH/{scan_id}/`
8. Updates DB record to `SUCCESS` or `FAILED`

**Requirements:** `pwsh` (PowerShell 7+) in PATH. Interactive auth requires a desktop Windows session.

## ERROR HANDLING CONVENTION

- Services raise `ValueError` for business rule violations → caught globally as HTTP 400
- Routers re-raise as `HTTPException` when a specific status code is needed (404, 409)
- Global handlers in `core/exception_handlers.py`: `IntegrityError` → 409, `SQLAlchemyError` → 500, unhandled → 500
- Never expose raw exception messages to clients in production (`ENV=production`)
