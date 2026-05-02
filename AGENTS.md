# AssistantAudit — Agent Entry Point

<!-- SCOPE: Point d'entree canonique du depot AssistantAudit pour developpeurs et agents IA. Conventions, navigation, regles transverses et procedure d'onboarding. -->
<!-- DOC_KIND: index -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Demarrage d'une session de developpement ou onboarding agent IA — point d'entree canonique du depot. -->
<!-- SKIP_WHEN: Tu cherches une procedure specifique (runbook), un schema DB ou une decision architecturale. -->
<!-- PRIMARY_SOURCES: docs/README.md, docs/principles.md, docs/project/architecture.md, docs/project/runbook.md -->

## Quick Navigation

- [Overview](#overview)
- [Structure](#structure)
- [Quick Start](#quick-start)
- [Onboarding nouveau contributeur](#onboarding-nouveau-contributeur)
- [Architecture](#architecture)
- [Where to Look](#where-to-look)
- [Conventions](#conventions)
- [Documentation](#documentation)
- [Anti-patterns](#anti-patterns)

## Agent Entry

Quand lire ce document : Demarrage d'une session de developpement ou onboarding agent IA — point d'entree canonique du depot.

Quand l'ignorer : Tu cherches une procedure specifique (runbook), un schema DB ou une decision architecturale.

Sources primaires : `docs/README.md`, `docs/principles.md`, `docs/project/architecture.md`, `docs/project/runbook.md`.

## Overview

Plateforme d'audit de sécurité informatique pour Red Team, auditeurs de conformité et consultants cybersécurité. Backend FastAPI (Python sync), frontend Next.js 16. Les auditeurs gèrent des missions, des checklists, et génèrent des rapports PDF conformes aux référentiels de sécurité standards (CIS, ANSSI, ISO 27001, NIS2).

## Structure

```
AssistantAudit/
├── backend/              Application FastAPI (Python 3.13, sync)
│   ├── app/
│   │   ├── api/v1/       Routeurs HTTP (22 modules)
│   │   ├── core/         Sécurité, encryption, errors, rate-limit, WebSocket manager
│   │   ├── models/       Modèles SQLAlchemy 2.0
│   │   ├── schemas/      Schémas Pydantic 2.x
│   │   ├── services/     Logique métier (Style B : module-level functions)
│   │   ├── tools/        Outils d'audit (ad_auditor, monkey365_runner, ssl_checker, …)
│   │   └── templates/    Templates Jinja2 pour rapports PDF (WeasyPrint)
│   ├── alembic/          Migrations DB
│   ├── scripts/          Seeds, rotate_kek, init_ca, reset_admin_password
│   └── tests/            Tests pytest (688+)
├── frontend/             Application Next.js 16 (App Router, React 19, Tailwind v4, shadcn/ui v4)
│   └── src/
│       ├── app/          Pages (route segments)
│       └── components/   Composants React
├── frameworks/           Référentiels YAML (auto-syncs en DB au démarrage)
├── tests/e2e/            Suite Playwright
├── tests/manual/         Scripts bash (test-all.sh)
├── docs/                 Documentation projet (voir docs/README.md)
├── .env.example          Template variables d'environnement
└── docker-compose.yml    Orchestration conteneurs (db + backend + frontend)
```

## Quick Start

### Docker (recommandé)

```bash
cp .env.example .env   # Remplir SECRET_KEY, ADMIN_PASSWORD, ENCRYPTION_KEY, FILE_ENCRYPTION_KEY, POSTGRES_PASSWORD
docker compose up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

Identifiants admin affichés dans le terminal au premier démarrage.

### Manuel (Linux/macOS)

```bash
cd backend && python init_db.py && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
cd frontend && npm install && npm run dev
```

Détails complets : voir [`docs/project/runbook.md`](docs/project/runbook.md).

### Tests

```bash
cd backend && pytest -q                # tests backend
npx playwright test                    # E2E (depuis la racine)
bash tests/manual/test-all.sh          # tests manuels (Docker requis)
```

### Migrations DB

```bash
cd backend
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

## Onboarding nouveau contributeur

Si tu rejoins le projet pour la première fois :

1. **Clone & bootstrap** : suis [`docs/project/runbook.md`](docs/project/runbook.md) (Docker recommandé, alternative manuelle disponible).
2. **SSH config** (si tu as accès dev/pre-prod) : ajoute les alias `ubuntu-srv` et `win-agent` à ton `~/.ssh/config` — demande le bundle (IPs internes, alias, clé publique à déployer) au mainteneur (`@T0SAGA97` cf. `.github/CODEOWNERS`).
3. **Linear MCP** : pour les agents IA, connecte l'intégration Linear dans Claude Code (ou autre). Le `Team UUID` est résolu dynamiquement depuis le `Team Key` `TOS` (visible dans chaque ID de ticket `TOS-XX`). Workspace : TOSAGA. Board canonique : [`docs/tasks/kanban_board.md`](docs/tasks/kanban_board.md).
4. **Tests** : `cd backend && pytest -q` doit être vert sur ta machine avant le premier PR.
5. **Standards** : lis [`docs/principles.md`](docs/principles.md) et [`docs/documentation_standards.md`](docs/documentation_standards.md) avant de toucher au code.
6. **Workflow** : commits conventionnels (`feat`/`fix`/`test`/`refactor`/`security`/`chore`/`docs`). Branch protection sur `main` — toujours passer par PR.

## Architecture

```
Router (api/v1/)
  └── appelle Service (services/)
        └── interroge Model (models/) via SQLAlchemy Session
              └── sérialise avec Schema (schemas/)
```

Les endpoints n'accèdent **jamais** directement à la base de données. Toute logique métier passe par les services. Les exceptions de domaine (`AppError`, `NotFoundError`, `ForbiddenError`, `ConflictError`, `ValidationError`, `BusinessRuleError`, `ServerError`) vivent dans `core/errors.py` ; les routeurs les traduisent en `HTTPException`.

Détail complet : [`docs/project/architecture.md`](docs/project/architecture.md).

## Where to Look

| Tâche | Emplacement |
|-------|-------------|
| Ajouter un endpoint API | `backend/app/api/v1/` |
| Ajouter un modèle DB | `backend/app/models/` |
| Ajouter un schéma Pydantic | `backend/app/schemas/` |
| Ajouter de la logique métier | `backend/app/services/` |
| Ajouter un outil d'audit | `backend/app/tools/` |
| Ajouter un template de rapport | `backend/app/templates/reports/sections/` |
| Ajouter une page frontend | `frontend/src/app/{route}/page.tsx` |
| Ajouter un composant UI | `frontend/src/components/` |
| Ajouter un référentiel d'audit | `frameworks/<nom>.yaml` |
| Ajouter une migration | `cd backend && alembic revision --autogenerate -m "msg"` |
| Ajouter un test backend | `backend/tests/test_<module>.py` |
| Ajouter un test E2E | `tests/e2e/<feature>.spec.ts` |
| Ajouter un script de seed/ops | `backend/scripts/` |

## Conventions

- **Texte UI, chaînes utilisateur, commentaires, docstrings :** français
- **Identifiants, variables, noms de fonctions :** anglais
- Backend : synchrone uniquement — pas de `async def` sur les routes ou services (sauf handlers WebSocket)
- Colonnes DB existantes : ne jamais renommer — ajouter de nouvelles colonnes à la place
- Stack frontend : Next.js 16, React 19, Tailwind CSS v4, shadcn/ui v4
- TypeScript : pas de `as any` ni `@ts-ignore`
- Format de commit : `feat` / `fix` / `test` / `refactor` / `security` / `chore` / `docs`
- Tests après chaque modification ; diff summary avant de passer à l'étape suivante

## Documentation

Le hub de documentation est disponible dans [`docs/README.md`](docs/README.md). Pour la liste exhaustive des standards (SCOPE, Maintenance, NO_CODE, etc.) : [`docs/documentation_standards.md`](docs/documentation_standards.md).

## Anti-patterns

- Ne jamais commiter `.env`
- Ne jamais utiliser `shell=True` dans les appels subprocess
- Ne jamais supprimer les erreurs TypeScript avec `as any` ou `@ts-ignore`
- Ne jamais utiliser `async def` sur les routes ou services backend
- Ne jamais renommer une colonne DB existante
- Ne jamais appeler `db.query()` / `db.execute()` / `select()` / `session.get()` dans `api/v1/` — toujours via un service
- Ne jamais appeler `db.commit()` / `db.rollback()` dans `api/v1/` — la transaction appartient au service
- Ne jamais lever `HTTPException` dans un service — utiliser une exception de domaine `core/errors.py`
- Ne jamais appeler `asyncio.run()` depuis du code sync — utiliser `asyncio.run_coroutine_threadsafe(coro, app_loop)`
- Ne jamais utiliser un `dict` de classe pour de l'état request-scoped — utiliser `contextvars.ContextVar`
- Ne jamais définir un service comme classe statique — utiliser des fonctions module-level (Style B)

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.

**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.

**Last Updated** : 2026-05-02
