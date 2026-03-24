# BACKEND APPLICATION INTERNALS

**Generated:** 2026-03-22
**Context:** `/backend/app/` — FastAPI core application

## OVERVIEW

This directory contains the FastAPI application logic. It follows a strictly decoupled architecture: **Router → Service → Model**.

## STRUCTURE

```
backend/app/
├── api/v1/       # REST endpoints (versioned)
├── core/         # Infrastructure (config, DB, auth, metrics, logging) — see core/AGENTS.md
├── models/       # SQLAlchemy ORM (16 entities)
├── schemas/      # Pydantic v2 (Request/Response)
├── services/     # Business logic layer (12 services)
├── tools/        # External tool integrations (7 tools) — see tools/AGENTS.md
└── main.py       # FastAPI application factory (create_app + lifespan)
```

## WHERE TO LOOK

| Task | Location | Pattern |
|------|----------|---------|
| Create endpoint | `api/v1/` | Define route, inject service, return schema |
| Business logic | `services/` | Logic class, DB operations, external calls |
| DB Model | `models/` | SQLAlchemy class, then run Alembic |
| Request/Response | `schemas/` | Pydantic v2 models |
| Security/Auth | `core/` | Security utilities and JWT logic |

## KEY PATTERNS

### Router → Service → Model Flow
Endpoints must never access the database directly. They call services.
- **Router**: `api/v1/users.py` (receives schema, calls service)
- **Service**: `services/user_service.py` (performs logic, queries model)
- **Model**: `models/user.py` (SQLAlchemy definition)

### Dependency Injection
Located in `core/deps.py`. Use `Depends()` in route signatures:
- `get_db`: Provides a SQLAlchemy session
- `get_current_user`: Handles JWT validation and user retrieval
- `require_role("admin")`: Role-based permission checks

## ENTITIES & SERVICES

### 16 Models
`user`, `entreprise`, `site`, `equipement`, `audit`, `assessment`, `framework`, `scan`, `attachment`, `collect_result`, `config_analysis`, `ad_audit_result`, `network_map`, `pingcastle_result`, `monkey365_scan_result`, `audit_log`.

### Services (in `services/`)
1. **auth_service** — JWT generation/refresh, password hashing
2. **assessment_service** — Compliance control evaluation and scoring
3. **framework_service** — YAML referential sync (SHA-256 hash comparison)
4. **scan_service** — Network scan execution lifecycle
5. **collect_service** — SSH/WinRM remote data collection
6. **config_analysis_service** — Firewall config parsing and analysis
7. **ad_audit_service** — Active Directory LDAP auditing
8. **pingcastle_service** — PingCastle AD health check
9. **monkey365_service** — Monkey365 M365/Azure bridge
10. **monkey365_scan_service** — Monkey365 scan result management
11. **query_optimizer** — Database query optimization utilities

## CONVENTIONS

- **Language**: English for code (identifiers, variables), French for comments and docstrings.
- **Exceptions**: Raise `HTTPException` in routers; raise custom `AppError` in services (caught by global handler).
- **Validation**: Use Pydantic `field_validator` for complex data rules.
