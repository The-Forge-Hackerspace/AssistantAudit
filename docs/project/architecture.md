# Architecture — AssistantAudit

<!-- SCOPE: Vue d'architecture (arc42 + C4 ASCII) de la plateforme AssistantAudit. Decrit les conteneurs, composants, patterns et decisions structurantes. Hors scope : versions exactes (voir `tech_stack.md`), exigences fonctionnelles (voir `requirements.md`). -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu touches a plusieurs couches ou tu integres un nouvel outil/composant. -->
<!-- SKIP_WHEN: Tu cherches versions exactes (tech_stack.md) ou exigences (requirements.md). -->
<!-- PRIMARY_SOURCES: backend/app/main.py, backend/app/api/v1/router.py, backend/app/services/, frontend/src/app/ -->
DOC_KIND: project-architecture
DOC_ROLE: vue-systeme
READ_WHEN: prise de decision structurante, onboarding technique, redaction d'ADR, redaction de story Epic-level.
SKIP_WHEN: simple lookup d'une version (voir `tech_stack.md`), recherche d'une regle de codage (voir `../principles.md`), recherche d'un endpoint (voir Swagger `/docs`).
PRIMARY_SOURCES: `backend/app/`, `frontend/src/`, `docker-compose.yml`, `Dockerfile`, `Dockerfile.frontend`, `docs/reference/adrs/`.

## Quick Navigation

| Section | Sujet |
|---------|-------|
| [Introduction et objectifs](#introduction-et-objectifs) | Pourquoi cette architecture |
| [Contraintes architecturales](#contraintes-architecturales) | Regles non negociables |
| [Contexte (C4 niveau 1)](#contexte-c4-niveau-1) | Le systeme et ses voisins |
| [Conteneurs (C4 niveau 2)](#conteneurs-c4-niveau-2) | Processus deployes |
| [Composants backend (C4 niveau 3)](#composants-backend-c4-niveau-3) | Decoupage interne FastAPI |
| [Composants frontend](#composants-frontend) | Decoupage interne Next.js |
| [Patterns architecturaux](#patterns-architecturaux) | Conventions partagees |
| [Decisions cles](#decisions-cles) | Tableau decisionnel + ADR |
| [Vue runtime](#vue-runtime) | Sequences principales |
| [Vue deploiement](#vue-deploiement) | Topologie d'execution |
| [Maintenance](#maintenance) | Regles de mise a jour |

## Agent Entry

| Si la demande concerne... | Alors consulter |
|---------------------------|-----------------|
| Une nouvelle frontiere de service | [Patterns architecturaux](#patterns-architecturaux) + [Composants backend](#composants-backend-c4-niveau-3) |
| Un nouveau processus / conteneur | [Conteneurs](#conteneurs-c4-niveau-2) + [Vue deploiement](#vue-deploiement) |
| Une regle transverse (langue, sync, RBAC) | [Contraintes architecturales](#contraintes-architecturales) |
| Une decision a justifier | [Decisions cles](#decisions-cles) + `docs/reference/adrs/` |

## Introduction et objectifs

AssistantAudit est une plateforme web (frontend Next.js + backend FastAPI + base PostgreSQL) qui industrialise le cycle d'audit de securite IT. L'architecture vise trois objectifs structurants :

| Objectif | Implication architecturale |
|----------|----------------------------|
| Tracabilite et confidentialite des preuves | Chiffrement au repos AES-256-GCM, isolation multi-tenant `owner_id`, mTLS agents. |
| Industrialisation des audits | Frameworks YAML auto-sync, pipelines de collecte, generation PDF/DOCX deterministe. |
| Maintenabilite par une petite equipe | Backend strictement synchrone, layered Router -> Service -> Model, services en module-level functions (Style B). |

## Contraintes architecturales

| Contrainte | Detail |
|------------|--------|
| Backend synchrone | `async def` interdit hors WebSocket handlers; pas d'`asyncio.run()` (utiliser `asyncio.run_coroutine_threadsafe`). |
| Frontiere routers/services | `api/v1/` ne fait pas d'acces DB direct, ne commit/rollback pas, ne reload pas la session. |
| Domain exceptions | Services levent `AppError` / `NotFoundError` (`core/errors.py`); routers traduisent en `HTTPException`. |
| Langue | UI / docstrings / commentaires en francais; identifiants en anglais. |
| Frameworks YAML | Source de verite : `frameworks/*.yaml`; auto-sync vers la table `framework` au demarrage. |
| Frontend stack | Next.js 16 (App Router), React 19, Tailwind v4, shadcn/ui v4 fixes. |
| Etat request-scoped | `contextvars.ContextVar` (jamais de dict de classe). |
| mTLS agents | Les agents Windows s'authentifient via certificat client; CA gere par `core/cert_manager.py`. |
| Migrations DB | Alembic uniquement; jamais renommer une colonne existante. |

## Contexte (C4 niveau 1)

Vue C1 : le systeme AssistantAudit et ses interlocuteurs.

```
+-------------------+        HTTPS         +-----------------------+
|  Auditeur /       | -------------------> |    AssistantAudit     |
|  Red Team /       |   (Next.js UI)       |    (frontend + API    |
|  Consultant       | <------------------- |     + base PG)        |
+-------------------+                      +-----------+-----------+
                                                       |
                              +------------------------+---------------------+
                              |                        |                     |
                              v                        v                     v
                       +-------------+         +---------------+      +--------------+
                       | Agent       |  WSS    | Cibles        |  ?   | Reverse proxy|
                       | Windows     | mTLS    | (M365, AD,    |      | NPMPlus/     |
                       | (collecte)  |         |  serveurs SSH,|      | Caddy)       |
                       |             |         |  pare-feu)    |      +------+-------+
                       +------+------+         +---------------+             |
                              |                                              |
                              +---- WSS /ws/agent ---------------------------+
```

| Acteur | Type | Interaction principale |
|--------|------|------------------------|
| Auditeur / Red Team / Consultant | Humain | Utilise l'UI Next.js (HTTPS via reverse proxy). |
| Agent Windows | Systeme | Se connecte en WebSocket mTLS sur `/ws/agent`. |
| Cibles (M365, AD, hosts SSH, pare-feu) | Systemes externes | Sont scrutees par les outils integres et les agents. |
| Reverse proxy (NPMPlus en prod, Caddy en staging) | Infrastructure | Expose le frontend, propage les en-tetes via `FORWARDED_ALLOW_IPS`. |
| Sentry | Service externe optionnel | Recoit les erreurs si `SENTRY_DSN` est defini. |

## Conteneurs (C4 niveau 2)

```
+----------------------------- Reverse proxy (externe) ---------------------------+
|                                                                                 |
|       /              /api/*  (rewrite Next.js -> backend)                        |
|       v                                                                         |
+-------+-------------------------------------------------------------------------+
        |
        |
+-------v---------+    rewrites      +---------------------+    SQL    +-----------+
| frontend        |  ============>   | backend             | =======>  | db        |
| Next.js 16      |  /api/v1/*       | FastAPI 0.135       |           | postgres  |
| port 3000       |                  | uvicorn (sync)      |           | 16-alpine |
| (image          |                  | port 8000           |           |           |
|  Dockerfile.    |                  | (image Dockerfile)  |           |           |
|  frontend)      |                  |                     |           |           |
+-----------------+                  +----------+----------+           +-----------+
                                                |
                                                | WSS /ws/agent (mTLS)
                                                v
                                         +-------------+
                                         | Agent       |
                                         | Windows     |
                                         | (host       |
                                         |  externe)   |
                                         +-------------+
```

| Conteneur | Image / runtime | Port | Role |
|-----------|-----------------|------|------|
| frontend | Image issue de `Dockerfile.frontend` (base `node:22-alpine`) | 3000 | Sert l'UI Next.js, proxy `/api/*` vers `BACKEND_INTERNAL_URL`. |
| backend | Image issue de `Dockerfile` cible `production` (base `python:3.13-slim-bookworm` + PowerShell 7) | 8000 | Expose `/api/v1/*`, `/ws/agent`, applique le rate-limit, orchestre services / outils. |
| db | `postgres:16-alpine` | 5432 (interne) | Persistance SQL, healthcheck `pg_isready`. |
| Reverse proxy externe | NPMPlus (prod) ou Caddy (staging) | 80/443 | Termine TLS et expose le frontend; le backend n'est pas publie via le proxy. |
| Agent Windows | Service hors compose (cf. `win-agent`) | sortant -> 8000 / WS | Execute la collecte M365 / AD / PowerShell pour le backend. |

## Composants backend (C4 niveau 3)

```
+------------------------------ backend/app/ -----------------------------------+
|                                                                                |
|  api/v1/   (HTTP routers, sans DB direct)                                      |
|  ├── agents, assessments, attachments, audits, auth, checklists,              |
|  ├── entreprises, equipements, files, findings, frameworks, health,           |
|  ├── network_map, oradad, pipelines, reports, sites, tags, users,             |
|  ├── websocket, router (registration)                                         |
|  └── tools/  (ad_audit, collect, config_analysis, monkey365, ssl_checker)     |
|                                                                                |
|  services/   (logique metier + transactions)                                   |
|  ├── audit_service, assessment_service, checklist_service                     |
|  ├── auth_service, entreprise_service, site_service, equipement_service       |
|  ├── framework_service, finding_service, recommendations_service              |
|  ├── remediation_plan_service, executive_summary_service, glossary_service    |
|  ├── ad_audit_service, monkey365_service, monkey365_streaming_executor        |
|  ├── monkey365_scan_service, oradad_analysis_service, oradad_config_service   |
|  ├── network_map_service, scan_progress, pipeline_service, task_service       |
|  ├── annexes_service, report_service, file_service, tag_service               |
|  ├── config_analysis_service, agent_service, collect_service                  |
|  └── collect/ (dispatcher, findings, evaluators/{linux,opnsense,windows})     |
|                                                                                |
|  models/    (SQLAlchemy 2.x)                                                   |
|  ├── user, entreprise, site, equipement, audit, assessment                    |
|  ├── checklist, anssi_checklist, finding, framework, tag                      |
|  ├── agent, agent_task, task_artifact, attachment, report                     |
|  ├── collect_pipeline, collect_result, config_analysis                        |
|  ├── ad_audit_result, monkey365_scan_result, oradad_config, network_map       |
|  └── enums                                                                     |
|                                                                                |
|  schemas/   (Pydantic 2.x)  + validators                                       |
|                                                                                |
|  core/      (transverse)                                                       |
|  ├── config, database, deps (DI), errors (AppError/NotFoundError)             |
|  ├── security (JWT/bcrypt), encryption (AES-256-GCM), file_encryption (KEK)   |
|  ├── cert_manager (CA mTLS), rate_limit, websocket_manager, event_loop        |
|  ├── task_runner, sweeper_runtime, collect_sweeper, heartbeat_sweeper         |
|  ├── exception_handlers, audit_logger, logging_config, helpers, storage       |
|  └── metrics, metrics_middleware, sentry_integration, health_check            |
|                                                                                |
|  tools/     (modules d'audit reutilisables, hors HTTP)                         |
|  ├── ad_auditor/     (auditor.py)                                             |
|  ├── collectors/     (ssh_collector, winrm_collector)                         |
|  ├── config_parsers/ (base, fortinet, opnsense)                               |
|  ├── monkey365_runner/ (config, executor, mapper, parser)                     |
|  └── ssl_checker/    (checker.py)                                             |
|                                                                                |
|  templates/reports/  (Jinja2 + WeasyPrint)                                     |
|  ├── sections/ (cover, executive_summary, scope, objectives,                   |
|  │              recommendations, remediation_plan, glossary,                   |
|  │              annexes, toc, introduction, _placeholder)                     |
|  ├── macros.html, report_base.html, styles.css                                 |
|                                                                                |
|  data/glossary.yaml  (glossaire metier rendu dans les rapports)                |
|  main.py             (bootstrap FastAPI + middleware + routers)                |
+--------------------------------------------------------------------------------+
```

| Couche | Role | Regles |
|--------|------|--------|
| `api/v1/` | Validation HTTP, DI, traduction des `AppError` en `HTTPException` | Pas d'acces DB direct, pas de commit/rollback. |
| `services/` | Logique metier + transactions + appels outils | Sync; module-level functions (Style B); leve `AppError`/`NotFoundError`. |
| `models/` | Mapping SQLAlchemy + colonnes chiffrees (`EncryptedJSON`) | Jamais renommer; ajouter une colonne via Alembic. |
| `schemas/` | DTO Pydantic 2 (request/response, validators) | Pas de logique metier. |
| `core/` | Transverse : config, DI, securite, encryption, rate-limit, WS, sweepers, observabilite | Centralise les decisions transverses. |
| `tools/` | Outils metier reutilisables (collecte, parsing, runners) | Injectes dans les services; testables hors HTTP. |
| `templates/reports/` | Rendu PDF (WeasyPrint) | Sections placees sous `sections/`. |

## Composants frontend

```
+------------------------------ frontend/src/ ----------------------------------+
|                                                                                |
|  app/  (Next.js App Router)                                                    |
|  ├── (pages)/  agents, audits/[id]/{checklists,synthese}, audits/evaluation,  |
|  │             entreprises, equipements, frameworks, login, profile, sites,  |
|  │             utilisateurs                                                   |
|  ├── outils/   ad-auditor, collecte, config-parser, monkey365, network-map,   |
|  │             oradad, scanner, ssl-checker                                   |
|  ├── layout.tsx, providers.tsx, error.tsx, globals.css                        |
|                                                                                |
|  components/                                                                   |
|  ├── ui/       (shadcn primitives : button, card, dialog, sheet, ...)         |
|  ├── checklists/   (filler, item-row, progress)                               |
|  ├── evaluation/   (attachment-section)                                       |
|  ├── network-map/  (TopologyView, dialogs/editors, Toolbar)                   |
|  ├── tags/        (tag-badge, tag-filter, tag-selector)                       |
|  ├── app-layout, auth-guard, skeletons, theme-toggle                          |
|                                                                                |
|  contexts/  auth-context.tsx                                                   |
|  hooks/     use-api, use-mobile, useNetworkMap                                 |
|  lib/       api-client (axios), constants, utils                               |
|  services/  api.ts                                                             |
|  types/     api, index                                                         |
+--------------------------------------------------------------------------------+
```

| Element | Role |
|---------|------|
| `app/` | Routes Next.js App Router (pages serveur/client). |
| `components/ui/` | Primitives shadcn-ui (radix + Tailwind). |
| `components/network-map/` | Editeur graphique base sur `@xyflow/react` + `@dagrejs/dagre`. |
| `contexts/auth-context.tsx` | Etat d'authentification global. |
| `lib/api-client.ts` | Client axios vers `/api/v1`; gere refresh + interception erreurs. |
| `services/api.ts` | Wrappers typed des appels API. |
| `hooks/use-api.ts` | Cache GET via SWR. |

## Patterns architecturaux

| Pattern | Implementation | Reference |
|---------|----------------|-----------|
| Layered architecture | Router (`api/v1/`) -> Service (`services/`) -> Model (`models/`) | `backend/app/` |
| Service Layer | Module-level functions, jamais classes static-only (Style B) | `backend/app/services/*` |
| DTO / Schema | Pydantic 2 separe la couche transport de la couche modele | `backend/app/schemas/*` |
| Domain exceptions | `AppError`, `NotFoundError` levees par services; routers traduisent | `backend/app/core/errors.py` |
| Dependency Injection | `Depends(...)` FastAPI injecte session DB et utilisateur courant | `backend/app/core/deps.py` |
| Request-scoped state | `contextvars.ContextVar` | `backend/app/core/` (utilises par audit logger / metrics) |
| Encryption-at-rest (col.) | TypeDecorator `EncryptedJSON` AES-256-GCM | `backend/app/core/encryption.py` |
| Encryption-at-rest (fichiers) | Enveloppe KEK + DEK | `backend/app/core/file_encryption.py` |
| mTLS agents | CA propre, certificats clients pour les agents Windows | `backend/app/core/cert_manager.py` |
| Rate limiting | In-memory par IP avec seuils auth/api/public | `backend/app/core/rate_limit.py` |
| Frameworks auto-sync | YAML -> table `framework` au boot | `backend/app/services/framework_service.py` + `frameworks/*.yaml` |
| WebSocket manager | Broker WS pour agents et streaming PowerShell | `backend/app/core/websocket_manager.py` |
| Sweepers | Tasks de menage (heartbeat, collect) executees par `sweeper_runtime` | `backend/app/core/heartbeat_sweeper.py`, `collect_sweeper.py` |

## Decisions cles

| ID | Decision | Rationale | Lien |
|----|----------|-----------|------|
| ADR-001 | Chiffrement au repos AES-256-GCM (TypeDecorators) + enveloppe KEK/DEK pour les fichiers | Garantir la confidentialite des preuves et credentials en cas de fuite DB / FS | [`../reference/adrs/ADR-001-encryption-at-rest.md`](../reference/adrs/ADR-001-encryption-at-rest.md) |
| AD-Sync | Backend strictement synchrone (FastAPI sync mode) | Simplicite operationnelle pour une petite equipe; pieges async evites | `principles.md` |
| AD-Layered | Router/Service/Model strict + domain exceptions | Tester la logique metier hors HTTP; preserver la frontiere transactionnelle | `principles.md`, `core/errors.py` |
| AD-Frameworks | Frameworks YAML auto-sync au demarrage | Versionner les referentiels avec le code; rester ouvert a l'edition manuelle | `frameworks/*.yaml`, `framework_service.py` |
| AD-mTLS | Authentification mTLS des agents Windows | Eviter la diffusion de secrets partages; CA propre revocable | `core/cert_manager.py` |
| AD-Stack | Frontend fige sur Next.js 16 + React 19 + Tailwind 4 + shadcn 4 | Aligner contributions et migrations majeures | `tech_stack.md` |

## Vue runtime

Sequences principales (haut niveau).

| Sequence | Etapes |
|----------|--------|
| Login + appel API | Client soumet credentials -> `auth.login` -> `auth_service` valide bcrypt -> emet JWT -> requetes suivantes passent par middleware rate-limit -> `deps.get_current_user` -> service -> modele -> DB -> reponse Pydantic. |
| Agent collecte | Agent ouvre WS mTLS sur `/ws/agent` -> `websocket_manager` enregistre la session -> backend pousse une tache (`agent_task`) -> agent renvoie artefacts (`task_artifact`) -> heartbeat surveille par `heartbeat_sweeper`. |
| Generation rapport | Client appelle `POST /api/v1/reports/...` -> `report_service` aggregue executive summary, findings, recommandations, plan de remediation, glossaire, annexes -> WeasyPrint rend `report_base.html` avec sections Jinja2 -> stockage chiffre via `file_service`. |
| Auto-sync frameworks | Au boot de FastAPI, `framework_service` lit `frameworks/*.yaml`, fait un upsert en table `framework`. |

## Vue deploiement

Topologie d'execution (`docker-compose.yml`).

| Service compose | Image | Limite CPU | Limite RAM | Volumes |
|-----------------|-------|------------|------------|---------|
| `db` | `postgres:16-alpine` | 0.5 | 256M | `pgdata` (named volume) |
| `backend` | build local (`Dockerfile`, target `production`) | 1.0 | 512M | `./data`, `app-certs`, `./tools/monkey365`, `./frameworks` |
| `frontend` | build local (`Dockerfile.frontend`) | 0.5 | 256M | (aucun) |

Particularites :

| Aspect | Detail |
|--------|--------|
| Reverse proxy | Externe (NPMPlus prod / Caddy staging); le port 8000 du backend n'est pas publie via le proxy. |
| Build args frontend | `NEXT_PUBLIC_API_URL=/api/v1`, `BACKEND_INTERNAL_URL=http://backend:8000` evalues au build. |
| Healthchecks | `pg_isready` (db), `GET /api/v1/health` (backend), `GET /` (frontend). |
| PowerShell | Modules Az / Graph / Exchange / Teams / PnP installes dans l'image backend pour Monkey365. |
| Agent Windows | Hors docker-compose; deploye sur `win-agent` (`172.16.20.21`) via `start.ps1` / installation manuelle. |

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

| Regle | Detail |
|-------|--------|
| Source | Toute decision structurante donne lieu a un ADR sous `docs/reference/adrs/`. |
| C4 ASCII | Pas de mermaid : tous les diagrammes restent ASCII (compatibles avec la regle NO_CODE > 5 lignes appliquee aux blocs de code, pas aux diagrammes). |
| Synchronisation | Verifier que les composants listes correspondent aux dossiers reels (`backend/app/`, `frontend/src/`). |
| ADR | Section [Decisions cles](#decisions-cles) referencee par identifiant; lier les nouveaux ADRs des leur acceptation. |
| Audit | Document revu par `ln-611-docs-structure-auditor`, `ln-612-semantic-content-auditor`, `ln-614-docs-fact-checker`. |
| Liens | Tous les liens internes restent relatifs. |
