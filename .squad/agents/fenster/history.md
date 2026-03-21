## Plugin Enhancements

- 📦 Charter enriched from `software-engineering-team` plugin (2026-03-21T21:10:00Z): OWASP Top 10 security standards for FastAPI, JWT best practices, CI/CD mindset (dep locking, env parity, rollback plan)

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

### Monkey365 Path Construction & Nesting Issue
- **Problem**: M365 audit output had redundant tenant ID nesting: `data/test/Cloud/M365/{scan_id}/{scan_id}/{output}/`
- **Root cause**: `Monkey365Executor.build_script()` and `_parse_output_files()` added `/ scan_id` to `output_dir`, but service layer already included scan_id in the path
- **Solution**: Fixed executor.py lines 151 & 311 to use `self.output_dir` directly without further nesting
- **Impact**: New scans use correct flat structure, existing double-nested scans remain (no migration needed)
- **Key insight**: Always verify path composition between service layer (controller) and executor layer (tool runner)

### M365 API Structure & Modularization
- **Organization**: M365 routes live in `backend/app/api/v1/tools/monkey365.py`, NOT in `tools.py` (root v1)
- **Module Hierarchy**: `tools/` directory has sub-routers (config_analysis.py, ssl_checker.py, collect.py, ad_audit.py, pingcastle.py, monkey365.py)
- **Router Aggregation**: Main `tools/__init__.py` includes all sub-routers with `include_router()`
- **Lesson**: When routes are split across multiple files, verify imports chain correctly through `__init__.py`

### M365 Scan Metadata Capture
- **Auth Settings**: Now captured in database: `auth_mode` (interactive/device_code/ropc/client_credentials), `force_msal_desktop` (bool)
- **PowerShell Config**: All parameters passed to Monkey365 stored in `powershell_config` JSON field for audit trail
- **Archive Path**: Tracked separately in `archive_path` field (independent of `output_path`)
- **Config Snapshot**: Remains as separate field for full point-in-time config record

### File Cleanup on Delete
- **Strategy**: DELETE endpoint calls `Monkey365ScanService.delete_scan()` which:
  1. Deletes working output directory if exists
  2. Deletes archive directory if exists  
  3. Deletes database record
  4. Logs all operations
- **Error Handling**: Warnings logged if files can't be deleted, but record still deleted from DB
- **Archive Base**: Configurable via `MONKEY365_ARCHIVE_PATH` setting (default: `/data/enterprise/Cloud/M365`)

### API Response Schema Design
- **Enhanced GET**: Now returns all auth settings + archive path + full powershell config
- **Request Schema**: `Monkey365ConfigSchema` extended to accept `auth_mode`, `force_msal_desktop`, `powershell_config`
- **Response Schema**: `Monkey365ScanResultRead` now has 16 properties (was 12)
- **Backward Compat**: All new fields are Optional, so existing clients still work

### Database Schema (SQLAlchemy 2.0)
- **15 ORM models** in `backend/app/models/`: User, Entreprise, Site, Equipement (polymorphic base + 9 subtypes), Audit, Framework (with Category + Control), Assessment (Campaign + Assessment + ControlResult), Scan (Reseau + Host + Port), Attachment, NetworkMap, ConfigAnalysis, Monkey365ScanResult, ADAnalysisResult, PingCastleResult
- **Foreign key cascade**: `all, delete-orphan` on parent-child relationships (e.g., Framework → Categories → Controls)
- **Eager loading**: `lazy="selectin"` on most relationships to avoid N+1 queries
- **SQLite dev mode** with auto-creation of tables via `create_all_tables()` in lifespan
- **Alembic migrations**: 7 migration scripts tracked in `backend/alembic/versions/`
- **Connection pooling**: `pool_pre_ping=True` for PostgreSQL, `PRAGMA foreign_keys=ON` for SQLite

### API Endpoint Patterns (FastAPI)
- **45 REST endpoints** across 14 route modules in `backend/app/api/v1/`
- **Dependency injection** via `Depends()`: `get_db()` for sessions, `get_current_user()` for auth, `get_current_admin()` / `get_current_auditeur()` for role checks
- **Pagination**: Reusable `PaginationParams` class with `page`, `page_size`, `offset` calculation
- **Response models**: `PaginatedResponse[T]`, `MessageResponse`, `ScoreResponse` for consistency
- **HTTP status codes**: Proper 201 for POST, 204 for DELETE, 404 for not found, 401/403 for auth failures
- **CORS middleware**: localhost-only in dev, must be env-based in production

### Auth Implementation (JWT + bcrypt)
- **JWT tokens**: `python-jose` with HS256 algorithm, 15-min access tokens + 7-day refresh tokens
- **Password hashing**: `bcrypt.hashpw()` with salt, `bcrypt.checkpw()` for verification
- **OAuth2PasswordBearer**: `/api/v1/auth/login` as token URL, supports both form and JSON body
- **Rate limiting**: In-memory rate limiter (5 attempts/60s, 5-min block) on login endpoints
- **Role-based access**: `admin` > `auditeur` > `lecteur` roles enforced via dependencies
- **Token payload**: `sub` (user ID), `exp` (expiration), `iat` (issued at), `type` (access/refresh), `role`, `username`

### Framework Sync Mechanics (YAML → Database)
- **Sync on startup**: `FrameworkService.sync_from_directory()` in `lifespan()` reads 14 YAML files from `frameworks/`
- **SHA-256 integrity**: `_file_hash()` computes hash, stored in `Framework.source_hash` to detect changes
- **Import logic**: Create if new, update if hash differs, skip if unchanged
- **YAML structure**: `framework.ref_id`, `name`, `version`, `categories[]`, `controls[]` with `ref_id`, `title`, `severity`, `check_type`, `remediation`
- **Cascade delete**: Old categories/controls are deleted when framework is updated (orphan removal)
- **200+ controls** across 14 frameworks (Active Directory, DNS/DHCP, Firewall, M365, OPNsense, Linux/Windows servers, Switch, VPN, Wi-Fi, Backup, Messaging, Peripherals)

### Service Layer Architecture
- **5 core services**: `AuthService`, `FrameworkService`, `AssessmentService`, `Monkey365Service`, `ScanService`
- **Static methods pattern**: All services use `@staticmethod` for stateless operations
- **Business logic separation**: Controllers (API routes) delegate to services, which interact with DB
- **Compliance scoring**: `Assessment.compliance_score` property aggregates ControlResult statuses (compliant=1, partial=0.5, non-compliant=0)
- **Query optimization**: `selectinload()` to avoid N+1 queries on list operations

### Middleware & Error Handling
- **5 middleware layers**: SecurityHeadersMiddleware, PrometheusMiddleware, AuditLoggingMiddleware, CORS
- **Security headers**: CSP, X-Frame-Options, X-Content-Type-Options, HSTS (HTTPS only)
- **Global exception handlers**: `ValueError` → 400, `IntegrityError` → 409, `SQLAlchemyError` → 500, generic `Exception` → 500 with traceback in debug mode
- **Structured JSON logging**: `ContextualJsonFormatter` adds `environment`, `app_version`, `request_id`, `user_id` to all logs
- **Prometheus metrics**: HTTP request counters, duration histograms, active request gauges exposed at `/metrics`

### Code Quality & Testing
- **Type hints**: 100% coverage on all functions (enforced by FastAPI/Pydantic)
- **Pydantic v2 schemas**: 12 schema modules in `backend/app/schemas/` with `ConfigDict(from_attributes=True)`
- **Test coverage**: 15 test files in `backend/tests/`, comprehensive for Monkey365, partial for other tools
- **Factory pattern**: `factories.py` provides test data generators
- **Test fixtures**: `conftest.py` provides in-memory SQLite DB, test client, auth tokens
- **102 Python files, 688 KB** in `backend/app/`

### Tools Integration (7 tools)
- **monkey365_runner**: PowerShell script generation, JSON parsing, ComplianceStatus mapping (600 lines, full test coverage)
- **ad_auditor**: LDAP 3.0 queries, GPO, Kerberos delegation analysis (674 lines, partial tests)
- **pingcastle_runner**: XML parsing with defusedxml, risk scoring (461 lines, partial tests)
- **nmap_scanner**: Whitelist (40 flags) + blacklist (10 dangerous flags), no shell=True (267 lines, NO tests)
- **ssl_checker**: TLS handshake, cert parsing, security findings (295 lines, NO tests)
- **collectors**: SSH (Paramiko) + WinRM (pywinrm) with 50+ audit commands (1,617 lines, partial tests)
- **config_parsers**: Fortinet + OPNsense firewall rule parsing (589 lines, NO tests)

