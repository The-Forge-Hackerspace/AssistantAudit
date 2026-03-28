# AssistantAudit — Project Knowledge Base

**Last updated:** 2026-03-28


## OVERVIEW

IT security auditing platform. FastAPI backend (Python 3.13), Next.js 16 frontend (React 19 + TypeScript), 12 YAML compliance frameworks auto-synced to SQLite, 6 integrated audit tools (Nmap, SSL checker, SSH/WinRM collectors, AD auditor, ORADAD, Monkey365, config parsers).

- **Backend:** `http://localhost:8000` — Swagger UI at `/docs`, ReDoc at `/redoc` (disabled in production)
- **Frontend:** `http://localhost:3000`
- **Database:** SQLite at `backend/instance/assistantaudit.db` (dev) — PostgreSQL in production
- **Architecture spec:** `ARCHITECTURE.md` at root — the source of truth for the v2 migration

### Active migration: Server / Client / Agent (branch `feat/server-client-agent-architecture`)

The project is migrating from a local-only tool to a distributed architecture:
- **Server (Ubuntu):** FastAPI backend, PostgreSQL, LLM/AI, Monkey365, centralized storage
- **Client (browser):** Existing frontend, WebSocket real-time events
- **Agent (Windows):** Separate repo (`AssistantAudit-Agent`), lightweight daemon running nmap/ORADAD/AD collectors

See `ARCHITECTURE.md` §1.5 for binding implementation decisions.

## STRUCTURE

```
AssistantAudit/
├── backend/              FastAPI Python app (see backend/CLAUDE.md)
├── frontend/             Next.js App Router (see frontend/CLAUDE.md)
├── frameworks/           12 YAML audit referentials — auto-synced to DB at startup
├── tools/monkey365/      Vendored PowerShell tool — do NOT edit; update via git pull only
├── certs/                mTLS certificates (ca.pem, ca.key) — NOT committed, generate via scripts/init_ca.py
├── data/                 Monkey365 scan output + encrypted blobs — NOT committed
├── ARCHITECTURE.md       v2 migration spec — READ BEFORE any structural change
├── CLAUDE.md             This file — project knowledge base for Claude Code
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

## IMPLEMENTATION DECISIONS (v2 migration — BINDING)

These decisions are final. Do NOT deviate without explicit approval.

1. **Sync first, async later** — Backend stays synchronous (psycopg2-binary). Do NOT use `async def` on routes or services, do NOT use `AsyncSession` or `create_async_engine`. Exception: WebSocket handlers in `core/websocket_manager.py` and `api/v1/websocket.py` are async by nature.

2. **Existing column names preserved** — NEVER rename existing columns. `nom_projet` stays `nom_projet`, `password_hash` stays `password_hash`, `username` stays `username`. New tables (agents, agent_tasks, anssi_checkpoints) use English names.

3. **Three roles: admin, auditeur, lecteur** — Not two. `auditeur` = the one who owns agents and dispatches tasks. `lecteur` = read-only. Do NOT simplify to "technician".

4. **ORADAD is the AD tool** — The AD audit tool is ORADAD (ANSSI). ORADAD is a data collector (LDAP dump → .tar of TSV files), not an analyzer. Analysis is done server-side by the AI. PingCastle code was fully removed.

5. **Envelope encryption for files** — Files on disk are encrypted with per-file DEK (AES-256-GCM), DEK encrypted with KEK. Never store files in plaintext in production. See `core/file_encryption.py`.

6. **Agent = separate repo** — The Windows agent daemon will live in `AssistantAudit-Agent`, not in this repo. This repo contains only the server and frontend.

7. **RBAC par ressource prévu** — Système de permissions owner/write/read par audit et entreprise (table `ResourcePermission` : user_id, resource_type, resource_id, permission level). Non implémenté encore — chantier dédié après la création de l'agent. Actuellement 30+ endpoints n'ont pas d'isolation par owner_id. Pattern de référence dans `agents.py` et `oradad.py`.

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
| Encryption logic | `backend/app/core/encryption.py` | AES-256-GCM column encryption |
| File encryption | `backend/app/core/file_encryption.py` | Envelope encryption (DEK/KEK) |
| Certificate management | `backend/app/core/cert_manager.py` | mTLS CA + agent cert signing |
| WebSocket management | `backend/app/core/websocket_manager.py` | Connection manager + reconnect buffer |
| Agent API routes | `backend/app/api/v1/agents.py` | Enrollment, heartbeat, task dispatch |
| ANSSI referential | `backend/app/models/anssi_checklist.py` | AD security checkpoints (seed script) |
| Architecture spec | `ARCHITECTURE.md` (root) | Full v2 spec — read before any structural change |

## LANGUAGE CONVENTIONS

- **UI text, user-facing strings, comments, docstrings:** French
- **Code identifiers, variables, function names:** English
- Applies to both backend Python and frontend TypeScript/React

## FRONTEND STACK (BINDING)

- **Next.js 16** with App Router (no Pages Router)
- **React 19** — uses the new `use()` hook, `useActionState`, `useOptimistic`. Do NOT use deprecated patterns like `forwardRef` (refs are now regular props in React 19), `useContext` (use `use(Context)` instead)
- **Tailwind CSS v4** — uses CSS-first configuration (`@theme` in CSS), NOT `tailwind.config.js`. Do NOT use `tailwind.config.js` or `tailwind.config.ts` patterns from v3
- **shadcn/ui v4** — shadcn/skills is installed, USE it as reference. Use `pnpm dlx shadcn@latest` CLI for adding/updating components. Do NOT manually copy component code from docs
- **TypeScript strict** — no `as any`, no `@ts-ignore`

## AUTH

- **User JWT:** 15-minute access tokens + 7-day refresh tokens, type="user"
- **Agent JWT:** 30-day tokens with embedded `owner_id`, type="agent" — see `core/security.py`
- **Enrollment codes:** 8-char alphanumeric, SHA-256 hashed in DB, TTL 10 minutes, single-use
- Roles: `admin` > `auditeur` > `lecteur` (hierarchy enforced in `core/deps.py`)
- `require_auditeur()` allows admin + auditeur (agent operations, task dispatch)
- Frontend stores tokens in js-cookie (`sameSite=strict`, non-httpOnly)
- Rate limiter on `POST /auth/login`: 5 attempts/minute, 5-minute block
- Agent ↔ Server: mTLS with private CA (certs managed by `core/cert_manager.py`)

## KEY ENVIRONMENT VARIABLES

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | auto-generated | JWT signing key — MUST be set explicitly in production |
| `DATABASE_URL` | `sqlite:///instance/assistantaudit.db` | DB connection string (PostgreSQL in prod) |
| `ENV` | `development` | `development` / `testing` / `production` |
| `ENCRYPTION_KEY` | `""` (passthrough) | AES-256-GCM key for DB columns — 64 hex chars in production |
| `FILE_ENCRYPTION_KEY` | `""` (passthrough) | KEK for file envelope encryption — 64 hex chars in production |
| `CA_CERT_PATH` | `certs/ca.pem` | mTLS CA certificate path |
| `CA_KEY_PATH` | `certs/ca.key` | mTLS CA private key path |
| `MONKEY365_PATH` | `""` | Absolute path to `Invoke-Monkey365.ps1` |
| `LOG_LEVEL` | `INFO` | `DEBUG` in dev |
| `CORS_ORIGINS` | `localhost:3000,5173` | Comma-separated allowed origins |

## WORKFLOW RULES — ALWAYS DO THESE

- **ALWAYS commit after completing a step or major change** — format: `feat`/`fix`/`test`/`refactor`/`security`/`chore`/`docs`. Never leave work uncommitted between steps.
- **ALWAYS run tests after each modification** — if a test breaks, fix it before continuing
- **ALWAYS show the diff summary before moving to the next step** — wait for validation
- **ALWAYS read ARCHITECTURE.md before any structural change**
- **ALWAYS run the POST-BUILD EVALUATION after each frontend chantier** — start app, test visually, fix before commit

## ANTI-PATTERNS — NEVER DO THESE

### General
- **NEVER commit `.env`** — use `.env.example` for documentation only
- **NEVER use `shell=True`** in subprocess calls — use argument lists
- **NEVER use `stdout=None, stderr=None`** when you need to capture output — use `capture_output=True` for non-interactive modes; omit entirely for interactive/device-code modes so prompts remain visible
- **NEVER hardcode absolute Windows paths** in Python source — derive from `Path(__file__)` or `settings`
- **NEVER modify `tools/monkey365/`** — vendored; update via `git pull` only
- **NEVER suppress TypeScript errors** with `as any` or `@ts-ignore`

### Migration-specific (v2)
- **NEVER use `async def` on routes or services** — the backend is sync (see decision §1 above)
- **NEVER rename existing DB columns** — add new columns, don't rename old ones
- **NEVER use `AsyncSession` or `create_async_engine`** — use `Session` and `create_engine`
- **NEVER store files in plaintext on disk in production** — use `EnvelopeEncryption` from `core/file_encryption.py`
- **NEVER expose file paths to the client** — use `file_uuid` and serve through API only
- **NEVER return 403 for ownership checks** — return 404 to avoid revealing existence of resources
- **NEVER skip the double verification on task dispatch** — check audit ownership AND agent ownership AND allowed_tools
- **NEVER put agent code in this repo** — agent daemon lives in `AssistantAudit-Agent`
- **NEVER add PingCastle code** — it was fully removed; the AD tool is ORADAD (ANSSI)
- **NEVER deploy with empty `ENCRYPTION_KEY` or `FILE_ENCRYPTION_KEY`** — passthrough mode is dev-only

## KNOWN TECHNICAL DEBT

### CRITIQUE (avant mise en production)

- **`.env` dans l'historique git** — nécessite `git filter-repo` + rotation de TOUTES les clés (SECRET_KEY, ENCRYPTION_KEY, FILE_ENCRYPTION_KEY)
- **`agent_tasks.parameters` stocke les credentials AD en clair** (JSON non chiffré) — besoin d'un type `EncryptedJSON`
- **30+ endpoints sans isolation par owner_id** (audits, entreprises, sites, équipements, scans) — RBAC par ressource planifié (table `ResourcePermission` : user_id, resource_type, resource_id, permission). Pattern de référence dans `agents.py` et `oradad.py`
- **Endpoint `/auth/refresh` manquant** — les tokens de 15 min ne sont pas renouvelables

### ELEVE (rapidement après la prod)

- **38 routes (42%) accèdent directement à la DB** sans passer par un service — créer AuditService, EntrepriseService, SiteService, EquipementService, AgentService, NetworkMapService
- **121 occurrences du pattern `if not X: raise 404`** — migrer vers `get_or_404()` (helper créé dans `core/helpers.py`, appliqué sur `audits.py` comme démo)
- **`rotate_kek.py` est un stub** — implémenter la rotation KEK complète (Attachment n'a pas encore les colonnes encrypted_dek/dek_nonce/kek_version)
- **Ownership check FK chain dupliqué 3 fois** (attachments.py, file_service.py x2) — centraliser quand le RBAC sera implémenté
- **15 opérations fichier sans try/except** — créer un helper `atomic_write()`
- **`chmod 600` sur `ca.key`** en déploiement Linux — pas de vérification de permissions au démarrage
- **~20 schemas avec champs status/role en `str` au lieu de `Literal`/`Enum`** — pattern démontré dans `ScanCreate`, `CollectCreate`, `ADAuditCreate`
- **`test_api.py` fragile** — dépend de l'ordre d'exécution (rate limiter partagé entre tests)
- **Services manquants de tests** : scan_service, collect_service, ad_audit_service, config_analysis_service, task_service
- **`network-map/page.tsx`** toujours ~2900 lignes — needs component extraction

### MOYEN (amélioration continue)

- `uploaded_by` sur Attachment est `String(200)` — devrait être FK vers `users.id`
- `owner_id` sur audits/scans/ad_audit_results est nullable — backfill nécessaire
- JSON columns sensibles non chiffrés (`dc_list`, `domain_admins` sur `ad_audit_result`) — `EncryptedJSON` planifié
- CRUD copié-collé dans entreprises/sites/equipements/audits (25+ endpoints quasi-identiques)
- Services retournent un mix de types (SQLAlchemy models, dicts, primitifs) — standardiser
- Messages d'erreur mix FR/EN dans tools/*
- Rate limiting WebSocket absent
- Buffers WS non nettoyés pour users inactifs
- Pas de complexité mot de passe au-delà de 8 caractères
- Pas de tests frontend (jest/vitest/playwright)
- `max_length` manquant sur ~100 champs `str` dans les schemas output
- Rate limiter in-process — breaks avec multiple uvicorn workers
- SSH private keys transmises en plaintext dans les request bodies
- CORS origins hardcodées comme défaut dans `config.py`

## COMPLETED

- [x] 12 backend migration steps (500+ tests passing)
- [x] 4 frontend chantiers (users, agents, ORADAD, Monkey365 device code)
- [x] Frontend audit shadcn/ui v4 + React 19 conformity
- [x] Sub-component extraction from monolithic pages (except network-map)
- [x] Complete PingCastle removal (code + models + routes + frontend + migration)
- [x] Security audit 8/8 — 8 critiques fixed, 13 eleves fixed
- [x] Dev practices audit 4/4 — 50 tests added, 928 dead lines removed
- [x] Dependencies pinned and CVEs patched (cryptography, ecdsa, requests, npm)
- [x] Security headers middleware (CSP, HSTS, X-Frame-Options, Referrer-Policy)
- [x] Swagger/ReDoc disabled in production

## NOTES

- Default admin credentials are printed by `init_db.py` / `start.ps1` — change on first login
- Monkey365 requires PowerShell 7+ (`pwsh`) in PATH on Windows
- No Docker — no Dockerfile exists
- No CI build/test pipeline — `.github/workflows/` contains squad triage only
- `ARCHITECTURE.md` is the spec for the v2 migration — read before any structural work
- Each migration step should be a separate commit for easy rollback
