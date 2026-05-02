# Stack technique — AssistantAudit

<!-- SCOPE: Inventaire des technologies (versions exactes) utilisees par AssistantAudit, avec leur role et la documentation officielle. Source de verite : `backend/requirements.txt`, `frontend/package.json`, `package.json` racine, `docker-compose.yml`, `Dockerfile`, `Dockerfile.frontend`. Hors scope : decisions architecturales (voir `architecture.md`), exigences fonctionnelles (voir `requirements.md`). -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu choisis une lib, valides une version ou rediges un Dockerfile. -->
<!-- SKIP_WHEN: Tu cherches le quoi (architecture) ou le comment (runbook). -->
<!-- PRIMARY_SOURCES: backend/requirements.txt, frontend/package.json, Dockerfile, docker-compose.yml -->
DOC_KIND: project-tech-stack
DOC_ROLE: inventaire-technologies
READ_WHEN: choix d'une dependance, montee de version, audit de surface, redaction de runbook ou de Dockerfile.
SKIP_WHEN: redaction d'une story metier (voir `requirements.md`), ecriture d'un ADR (voir `../reference/adrs/`).
PRIMARY_SOURCES: `backend/requirements.txt`, `frontend/package.json`, `package.json`, `docker-compose.yml`, `Dockerfile`, `Dockerfile.frontend`, `start.ps1`, `.github/workflows/`.

## Quick Navigation

| Section | Sujet |
|---------|-------|
| [Backend](#backend) | Python 3.13 + FastAPI |
| [Frontend](#frontend) | Next.js 16 + React 19 |
| [Base de donnees](#base-de-donnees) | PostgreSQL / SQLite |
| [Conteneurs et runtime](#conteneurs-et-runtime) | Docker + PowerShell |
| [CI/CD](#cicd) | GitHub Actions |
| [Tests E2E](#tests-e2e) | Playwright |
| [Outils integres](#outils-integres) | Monkey365, ssl_checker, AD audit, ORADAD, parsers |
| [Versions runtime](#versions-runtime) | Python / Node |
| [Maintenance](#maintenance) | Regles de mise a jour |

## Agent Entry

| Si la demande concerne... | Alors consulter |
|---------------------------|-----------------|
| Une montee de version d'une dep Python | [Backend](#backend) + `backend/requirements.txt` |
| Une montee de version d'une dep JS | [Frontend](#frontend) + `frontend/package.json` |
| Le runtime container | [Conteneurs et runtime](#conteneurs-et-runtime) + `Dockerfile`, `Dockerfile.frontend` |
| L'integration avec Monkey365 / ORADAD | [Outils integres](#outils-integres) + `backend/app/tools/` |

## Backend

| Composant | Version | Role | Doc officielle |
|-----------|---------|------|----------------|
| FastAPI | 0.135.1 | Framework web (mode synchrone) | https://fastapi.tiangolo.com/ |
| uvicorn[standard] | 0.42.0 | Serveur ASGI (`--proxy-headers`, `--forwarded-allow-ips`) | https://www.uvicorn.org/ |
| SQLAlchemy | 2.0.48 | ORM | https://docs.sqlalchemy.org/en/20/ |
| Alembic | 1.18.4 | Migrations DB | https://alembic.sqlalchemy.org/ |
| Pydantic | 2.12.5 | Validation / serialisation | https://docs.pydantic.dev/2.12/ |
| pydantic-settings | 2.13.1 | Chargement config typee | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| email-validator | 2.3.0 | Validation des adresses email | https://github.com/JoshData/python-email-validator |
| PyJWT | >= 2.10 | Signature/verification JWT | https://pyjwt.readthedocs.io/ |
| bcrypt | 5.0.0 | Hash de mot de passe | https://github.com/pyca/bcrypt |
| python-multipart | 0.0.26 | Multipart parser (patch GHSA-mj87-hwqh-73pj) | https://github.com/Kludex/python-multipart |
| cryptography | 46.0.7 | AES-256-GCM, certificats CA mTLS | https://cryptography.io/en/latest/ |
| websockets | 16.0 | Lib WebSocket cote serveur | https://websockets.readthedocs.io/ |
| pytest | 9.0.3 | Framework de tests | https://docs.pytest.org/en/stable/ |
| pytest-asyncio | 1.3.0 | Support tests asynchrones | https://pytest-asyncio.readthedocs.io/ |
| pytest-cov | 7.0.0 | Couverture de tests | https://pytest-cov.readthedocs.io/ |
| pytest-mock | 3.15.1 | Mocks pour pytest | https://pytest-mock.readthedocs.io/ |
| ruff | >= 0.11.0 | Lint Python | https://docs.astral.sh/ruff/ |
| python-json-logger | 4.0.0 | Logs JSON structures | https://github.com/madzak/python-json-logger |
| prometheus-client | 0.24.1 | Exposition metriques Prometheus | https://prometheus.github.io/client_python/ |
| sentry-sdk | 2.55.0 | Capture erreurs / traces | https://docs.sentry.io/platforms/python/ |
| WeasyPrint | 68.0 | Rendu PDF des rapports | https://doc.courtbouillon.org/weasyprint/ |
| python-docx | 1.1.2 | Generation DOCX | https://python-docx.readthedocs.io/ |
| Jinja2 | 3.1.6 | Templating des rapports | https://jinja.palletsprojects.com/ |
| paramiko | 4.0.0 | Collecte SSH | https://www.paramiko.org/ |
| pywinrm | 0.5.0 | Collecte Windows WinRM | https://github.com/diyan/pywinrm |
| ldap3 | 2.9.1 | Audit LDAP / Active Directory | https://ldap3.readthedocs.io/ |
| python-dateutil | 2.9.0.post0 | Manipulation de dates | https://dateutil.readthedocs.io/ |
| PyYAML | 6.0.3 | Lecture des frameworks YAML | https://pyyaml.org/ |
| defusedxml | 0.7.1 | Parsing XML sur (Nmap, configs) | https://github.com/tiran/defusedxml |
| httpx | 0.28.1 | Client HTTP (futures integrations) | https://www.python-httpx.org/ |
| python-dotenv | 1.2.2 | Chargement `.env` | https://pypi.org/project/python-dotenv/ |
| psycopg2-binary | >= 2.9.0 | Driver PostgreSQL (production) | https://www.psycopg.org/docs/ |

## Frontend

| Composant | Version | Role | Doc officielle |
|-----------|---------|------|----------------|
| Next.js | 16.2.3 | Framework React (App Router) | https://nextjs.org/docs |
| React | 19.2.3 | Lib UI | https://react.dev/ |
| react-dom | 19.2.3 | Renderer DOM React | https://react.dev/reference/react-dom |
| TypeScript | ^5 | Typage statique | https://www.typescriptlang.org/docs/ |
| Tailwind CSS | ^4 (via `@tailwindcss/postcss` ^4) | Styling utility-first | https://tailwindcss.com/docs |
| shadcn | ^3.8.4 | CLI primitives UI | https://ui.shadcn.com/ |
| radix-ui | ^1.4.3 | Primitives accessibles | https://www.radix-ui.com/primitives |
| tw-animate-css | ^1.4.0 | Animations Tailwind | https://github.com/Wombosvideo/tw-animate-css |
| react-hook-form | ^7.72.0 | Gestion de formulaires | https://react-hook-form.com/ |
| @hookform/resolvers | ^5.2.2 | Adaptateurs de validation | https://github.com/react-hook-form/resolvers |
| zod | ^4.3.6 | Schema validation | https://zod.dev/ |
| axios | ^1.15.0 | Client HTTP | https://axios-http.com/ |
| swr | ^2.4.0 | Cache GET / revalidation | https://swr.vercel.app/ |
| @xyflow/react | ^12.9.2 | Graphes (network map) | https://reactflow.dev/ |
| @dagrejs/dagre | ^1.1.8 | Layout de graphes | https://github.com/dagrejs/dagre |
| @xterm/xterm | ^6.0.0 | Terminal embarque (Monkey365) | https://xtermjs.org/ |
| @xterm/addon-fit | ^0.11.0 | Auto-resize terminal | https://github.com/xtermjs/xterm.js/tree/master/addons/addon-fit |
| lucide-react | ^0.563.0 | Icones SVG | https://lucide.dev/ |
| next-themes | ^0.4.6 | Theme dark/light | https://github.com/pacocoursey/next-themes |
| recharts | ^2.15.4 | Graphes / charts | https://recharts.org/ |
| sonner | ^2.0.7 | Toaster | https://sonner.emilkowal.ski/ |
| html-to-image | 1.11.11 | Export visuels en image | https://github.com/bubkoo/html-to-image |
| class-variance-authority | ^0.7.1 | Variants de composants | https://cva.style/ |
| clsx | ^2.1.1 | Composition de classNames | https://github.com/lukeed/clsx |
| tailwind-merge | ^3.4.0 | Fusion intelligente Tailwind | https://github.com/dcastil/tailwind-merge |
| eslint | ^9 | Lint JS/TS | https://eslint.org/docs/latest/ |
| eslint-config-next | 16.1.6 | Preset lint Next.js | https://nextjs.org/docs/app/api-reference/config/eslint |

## Base de donnees

| Composant | Version | Role | Doc officielle |
|-----------|---------|------|----------------|
| PostgreSQL | 16 (image `postgres:16-alpine`) | Persistance production (healthcheck `pg_isready`) | https://www.postgresql.org/docs/16/ |
| SQLite | natif Python (defaut `DATABASE_URL=sqlite:///instance/assistantaudit.db`) | Persistance developpement | https://www.sqlite.org/docs.html |
| psycopg2-binary | >= 2.9.0 | Driver PG (production) | https://www.psycopg.org/docs/ |

## Conteneurs et runtime

| Composant | Version | Role | Reference |
|-----------|---------|------|-----------|
| Docker (multi-stage) | base `node:22-alpine` (frontend) + base `python:3.13-slim-bookworm` (backend) | Build et run des images | `Dockerfile`, `Dockerfile.frontend` |
| docker-compose | services `db`, `backend`, `frontend` | Orchestration locale et serveur | `docker-compose.yml` |
| PowerShell | 7 (installe dans l'image backend) | Execution Monkey365 et scripts M365 | https://learn.microsoft.com/powershell/ |
| Az.Accounts / Az.Resources | modules PSGallery (image backend) | Authentification Azure / inventaire | https://learn.microsoft.com/powershell/azure/ |
| ExchangeOnlineManagement | module PSGallery | Audits Exchange Online | https://learn.microsoft.com/powershell/exchange/exchange-online-powershell |
| MicrosoftTeams | module PSGallery | Audits Teams | https://learn.microsoft.com/microsoftteams/teams-powershell-overview |
| Microsoft.Graph.Authentication | module PSGallery | Authentification Graph | https://learn.microsoft.com/powershell/microsoftgraph/ |
| Microsoft.Graph.Users | module PSGallery | Lecture utilisateurs Graph | https://learn.microsoft.com/powershell/microsoftgraph/ |
| PnP.PowerShell | module PSGallery | Audits SharePoint / OneDrive | https://pnp.github.io/powershell/ |

## CI/CD

| Workflow | Description |
|----------|-------------|
| `.github/workflows/ci.yml` | Lint backend (ruff) + lint frontend (eslint) + tests `pytest -q` + build frontend. |
| `.github/workflows/playwright.yml` | E2E Playwright (`tests/e2e/`) avec `FORWARDED_ALLOW_IPS` permissif et `RATE_LIMIT_*_MAX` relache. |
| `.github/workflows/secret-scan.yml` | Scan de secrets via `gitleaks` sur l'historique. |
| `.github/workflows/dependabot-auto-merge.yml` | Auto-merge des PR Dependabot (config dans `.github/dependabot.yml`). |
| `.github/workflows/claude-code-review.yml` | Revue automatique par Claude Code sur PR. |
| `.github/workflows/claude.yml` | Workflow d'invocation Claude (commentaires PR / issues). |

## Tests E2E

| Composant | Version | Role | Reference |
|-----------|---------|------|-----------|
| @playwright/test | ^1.58.2 (`package.json` racine) | Tests end-to-end navigateur | https://playwright.dev/docs/intro |
| @types/node | ^25.5.0 | Types Node pour Playwright | https://www.npmjs.com/package/@types/node |
| Suites | `tests/e2e/` (agents, audits, auth, entreprises, equipements, frameworks, network-map, rbac, responsive, sidebar-breakpoint, sites, smoke-auth, smoke-public, utilisateurs) | Couverture parcours critiques | `playwright.config.ts` |

## Outils integres

| Outil | Role | Reference |
|-------|------|-----------|
| Monkey365 | Audit Microsoft 365 (PowerShell streaming) | `backend/app/tools/monkey365_runner/` ; `tools/monkey365` (volume Docker) |
| Nmap | Scan reseau (sortie XML parsee via `defusedxml`) | Variable `NMAP_TIMEOUT=600`; declenche par les pipelines de collecte |
| ssl_checker (custom) | Verification chaines TLS / certificats | `backend/app/tools/ssl_checker/checker.py` |
| AD auditor | Audit Active Directory (LDAP via `ldap3`) | `backend/app/tools/ad_auditor/auditor.py` |
| ORADAD | Outil ANSSI d'audit AD; resultats importes | `backend/app/services/oradad_analysis_service.py`, modele `oradad_config` |
| Config parser Fortinet | Parse de configurations Fortinet | `backend/app/tools/config_parsers/fortinet.py` |
| Config parser OPNsense | Parse de configurations OPNsense | `backend/app/tools/config_parsers/opnsense.py` |
| SSH collector | Collecte distante SSH (paramiko) | `backend/app/tools/collectors/ssh_collector.py` |
| WinRM collector | Collecte distante Windows | `backend/app/tools/collectors/winrm_collector.py` |
| Network map | Editeur graphe (xyflow + dagre) | `frontend/src/app/outils/network-map/`, `backend/app/services/network_map_service.py` |

## Versions runtime

| Runtime | Version | Source |
|---------|---------|--------|
| Python | 3.13 (image `python:3.13-slim-bookworm`) | `Dockerfile` |
| Node | 22 (image `node:22-alpine`) | `Dockerfile.frontend` |
| PowerShell | 7 (installe dans l'image backend) | `Dockerfile` |
| PostgreSQL serveur | 16 (image `postgres:16-alpine`) | `docker-compose.yml` |

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

| Regle | Detail |
|-------|--------|
| Source de verite | Toute version vient de `backend/requirements.txt`, `frontend/package.json`, `package.json` racine ou des fichiers Docker. |
| Synchronisation | Toute montee de version doit mettre a jour ce document dans le meme commit. |
| Liens officiels | Privilegier la doc officielle de l'editeur; eviter les agregateurs. |
| Audit | Document revu par `ln-614-docs-fact-checker` et `ln-625-dependencies-auditor`. |
| Liens | Tous les liens internes restent relatifs. |
