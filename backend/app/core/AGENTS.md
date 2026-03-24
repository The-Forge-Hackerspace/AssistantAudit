# CORE INFRASTRUCTURE

**Location:** `backend/app/core/`
**Overview:** Cross-cutting infrastructure providing configuration, database connectivity, security, and monitoring for the FastAPI application.

## MODULE MAP

| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `config.py` | Settings & env loading | `settings`, `get_auth_data` |
| `database.py` | SQLAlchemy setup | `engine`, `SessionLocal`, `Base` |
| `deps.py` | FastAPI DI hub | `get_db`, `get_current_user`, `require_role` |
| `security.py` | JWT & Password hashing | `create_access_token`, `verify_password` |
| `audit_logger.py` | Request auditing | `AuditLoggingMiddleware` |
| `logging_config.py` | JSON logging | `setup_logging` |
| `metrics.py` | Prometheus init | `REQUEST_COUNT`, `REQUEST_LATENCY` |
| `metrics_middleware.py` | Metric tracking | `PrometheusMiddleware` |
| `health_check.py` | System health | `HealthCheckService` |
| `rate_limit.py` | Auth rate limiting | `RateLimiter` |
| `exception_handlers.py` | Error mapping | `add_exception_handlers` |
| `sentry_integration.py` | Error tracking | `init_sentry` |
| `storage.py` | File utilities | `get_upload_path`, `save_upload_file` |

## DEPENDENCY INJECTION

The `deps.py` module acts as the central hub for FastAPI's `Depends()` system. All API routes must use these to ensure consistency:

*   **get_db**: Yields a scoped SQLAlchemy session and handles cleanup.
*   **get_current_user**: Decodes JWT, verifies the user exists in DB, and returns the User model.
*   **require_role(role)**: A dependency factory that enforces RBAC (admin, auditeur, lecteur).

## CONVENTIONS

*   **Config Source**: Settings load from the ROOT `.env` file, not `backend/.env`.
*   **Secrets**: `SECRET_KEY` is auto-generated in dev if missing from environment.
*   **Security Debt**: CORS origins are currently hardcoded in `config.py`.
*   **Middleware**: Metrics and audit logging are applied globally in `main.py` but configured here.
*   **Storage**: All file operations use paths defined in `storage.py` to ensure portability.
