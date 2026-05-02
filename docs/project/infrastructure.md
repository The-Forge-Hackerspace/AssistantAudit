
# Infrastructure - AssistantAudit

<!-- SCOPE: Inventaire declaratif de l'infrastructure AssistantAudit (serveurs, services Docker, reseau, domaines, agent Windows, variables d'environnement, CI/CD, volumes, securite, pieges). Decrit CE QUI est deploye et OU. Les procedures (deploy, restart, troubleshoot) appartiennent a docs/project/runbook.md. -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu prepares un deploiement ou cherches la cartographie infra. -->
<!-- SKIP_WHEN: Tu cherches une procedure (runbook). -->
<!-- PRIMARY_SOURCES: docker-compose.yml, Dockerfile, .env.example, .github/workflows/ -->
## Quick Navigation

- [Vue d'ensemble](#vue-densemble)
- [Serveurs](#serveurs)
- [Services Docker](#services-docker)
- [Reseau](#reseau)
- [Domaines & DNS](#domaines--dns)
- [Agent Windows](#agent-windows)
- [Variables d'environnement critiques](#variables-denvironnement-critiques)
- [Variables secondaires](#variables-secondaires)
- [CI/CD GitHub Actions](#cicd-github-actions)
- [Volumes & persistance](#volumes--persistance)
- [Securite](#securite)
- [Pieges connus](#pieges-connus)
- [Maintenance](#maintenance)

## Agent Entry

Document de reference (inventaire) pour AssistantAudit. Lire avant toute intervention DevOps. Pour les procedures executables (deploy, restart, troubleshoot, rotation cle), voir `docs/project/runbook.md`. Source de verite : `docker-compose.yml`, `Dockerfile`, `Dockerfile.frontend`, `.env.example`, `.github/workflows/`.

## Vue d'ensemble

AssistantAudit est deploye comme une stack Docker Compose unique de 3 services (`db`, `backend`, `frontend`) sur un hote Linux dev/pre-prod, complete par un agent Windows externe pour la collecte M365/Active Directory. L'acces public passe par un reverse proxy externe (NPMPlus en production, Caddy en staging) qui termine TLS et route le trafic vers le frontend Next.js et l'API FastAPI. Le pipeline CI/CD repose entierement sur GitHub Actions (lint, tests SQLite + PostgreSQL, build Docker, scan vulnerabilites, E2E Playwright). Echelle : single-node, pas de replicas, pas de GPU.

## Serveurs

2 hôtes physiques/virtuels. **Les valeurs concrètes (IP internes, hostnames, usernames admin) ne sont pas versionnées** : un nouveau contributeur reçoit le bundle SSH (alias + IP + clé publique à déployer) du mainteneur (`@T0SAGA97`, cf. `.github/CODEOWNERS`) et configure son `~/.ssh/config` en local.

| Alias SSH | OS | Rôle |
|---|---|---|
| `ubuntu-srv` | Linux (Ubuntu) | Hôte dev/pre-prod ; cible `docker compose up -d` (db + backend + frontend) |
| `win-agent` | Windows | Agent de collecte M365 / Active Directory (Monkey365, oradad, AD audit) |

Une fois `~/.ssh/config` configuré, les commandes deviennent `ssh ubuntu-srv` et `ssh win-agent` — aucun secret ni IP RFC1918 dans le repo.

## Services Docker

3 services definis dans `docker-compose.yml`. Aucun replica, redemarrage `unless-stopped` pour tous.

| Service | Image / Build | Port hote | Healthcheck | Limits CPU/RAM | Volumes |
|---|---|---|---|---|---|
| `db` | `postgres:16-alpine` | (non publie ; reseau interne) | `pg_isready -U assistantaudit` (5s/5s/5) | 0.5 CPU / 256M (res. 0.25 / 128M) | `pgdata` (named) |
| `backend` | build `./Dockerfile` target=`production` | `8000:8000` | `curl -f http://localhost:8000/api/v1/health` (10s/5s/3, start 15s) | 1.0 CPU / 512M (res. 0.5 / 256M) | `./data`, `app-certs` (named), `./tools/monkey365`, `./frameworks` |
| `frontend` | build `./Dockerfile.frontend` | `3000:3000` | `curl -f http://localhost:3000` (10s/5s/3, start 15s) | 0.5 CPU / 256M (res. 0.25 / 128M) | (aucun) |

Total reservations : ~2.0 vCPU et ~1.0 GB RAM (cf. `HOST_REQUIREMENTS`).

## Reseau

`docker compose` cree un reseau bridge interne par defaut. Les services se decouvrent par leur nom (`db`, `backend`, `frontend`). La base PostgreSQL n'expose aucun port sur l'hote ; elle n'est joignable que via le reseau Docker. Les dependances de demarrage sont strictes :

| Service | Depend de | Condition |
|---|---|---|
| `backend` | `db` | `service_healthy` |
| `frontend` | `backend` | `service_healthy` |

Le reverse proxy externe (NPMPlus en prod, Caddy en staging) ne fait pas partie du compose : il termine TLS, route `/` vers `frontend:3000`, et `/api/*` vers `backend:8000` via l'URL interne `BACKEND_INTERNAL_URL=http://backend:8000`. Cote Next.js, la rewrite `next.config.ts` est evaluee **au build** : `BACKEND_INTERNAL_URL` doit etre injecte comme build arg.

## Domaines & DNS

| Env | Hote externe | Reverse proxy | TLS |
|---|---|---|---|
| Production | [a confirmer] | NPMPlus | Oui (terminaison proxy) |
| Staging | [a confirmer] | Caddy | Oui (terminaison proxy) |
| Dev local | `localhost:3000` (frontend), `localhost:8000` (backend) | (aucun) | Non |

Le port backend `8000` n'est pas publie via le proxy en production : `FORWARDED_ALLOW_IPS=*` par defaut convient car le port reste accessible uniquement sur le reseau Docker et le runner local. Si le port devient public, restreindre `FORWARDED_ALLOW_IPS` a l'IP du proxy. Uvicorn est lance avec `--proxy-headers` ; les en-tetes `X-Forwarded-Proto` et `X-Forwarded-For` sont lus pour HSTS et le rate-limit par IP.

## Agent Windows

| Aspect | Valeur |
|---|---|
| Role | Collecte distante M365 (Monkey365), Active Directory (AD audit), oradad |
| Hote | Alias SSH `win-agent` (Windows ; valeurs réseau dans le bundle SSH du mainteneur) |
| Authentification | mTLS (certificats X.509 emis par le backend, CA interne) |
| Transport | WebSocket persistant `/ws/agent` (FastAPI + websockets 16.0) |
| Modules cote backend | PowerShell 7 + Az.Accounts, Az.Resources, ExchangeOnlineManagement, MicrosoftTeams, Microsoft.Graph.Authentication, Microsoft.Graph.Users, PnP.PowerShell |
| Variables liees | `CA_CERT_PATH=/app/certs/ca.pem`, `CA_KEY_PATH=/app/certs/ca.key`, `CRL_PATH=certs/crl.pem` |

L'agent recoit les ordres de collecte via WebSocket et remonte les artefacts vers le backend. Les certificats CA et la CRL sont stockes dans le volume `app-certs` (cote backend) afin que la rotation soit centralisee.

## Variables d'environnement critiques

Obligatoires en production / staging / preprod (echec fatal si absentes). Sources : `.env.example`, `backend/app/core/config.py`.

| Var | Role | Format | Generation |
|---|---|---|---|
| `SECRET_KEY` | Signature JWT | >= 32 caracteres | `python -c 'import secrets; print(secrets.token_urlsafe(64))'` |
| `ADMIN_PASSWORD` | Bootstrap admin via `docker_entrypoint.py` | >= 12 chars (recommande) | Mot de passe fort, gestionnaire de secrets |
| `ENCRYPTION_KEY` | AES-256-GCM colonnes (DB) | 64 hex (= 32 bytes) | `python -c 'import os; print(os.urandom(32).hex())'` |
| `FILE_ENCRYPTION_KEY` | KEK enveloppe fichiers (DEK chiffrees par KEK) | 64 hex (= 32 bytes) | `python -c 'import os; print(os.urandom(32).hex())'` |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | Mot de passe fort | Gestionnaire de secrets |
| `DATABASE_URL` | DSN base de donnees | URI SQLAlchemy | `postgresql://assistantaudit:<pwd>@db:5432/assistantaudit` (Docker) ou `sqlite:///instance/assistantaudit.db` (dev) |

Rotation de la KEK : `backend/scripts/rotate_kek.py`.

## Variables secondaires

| Var | Role | Defaut |
|---|---|---|
| `ENV` | Environnement d'execution | `development` (`testing` / `staging` / `preprod` / `production`) |
| `DEMO` | Si `true`, execute `seed_demo.py` apres migrations | `false` (interdit en prod) |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | Pagination API | `20` / `100` |
| `LOG_LEVEL` | Niveau de log Python | `INFO` |
| `NMAP_TIMEOUT` | Timeout scanner Nmap (s) | `600` |
| `MONKEY365_TIMEOUT` | Timeout collecte Monkey365 (s) | `600` |
| `MONKEY365_PATH` | Chemin du script PS1 | `/app/tools/monkey365/Invoke-Monkey365.ps1` (Docker) |
| `DATA_DIR` | Repertoire racine des donnees applicatives | `./data` (host) -> `/app/data` (container) |
| `CA_CERT_PATH` / `CA_KEY_PATH` / `CRL_PATH` | Materiel mTLS agents | `certs/ca.pem`, `certs/ca.key`, `certs/crl.pem` |
| `CORS_ORIGINS` | Origines autorisees (JSON list) | `["http://localhost:3000","http://frontend:3000"]` |
| `FORWARDED_ALLOW_IPS` | IPs autorisees a poser `X-Forwarded-*` | `*` (port 8000 non public) |
| `RATE_LIMIT_AUTH_MAX` / `RATE_LIMIT_API_MAX` / `RATE_LIMIT_PUBLIC_MAX` | Quotas par IP / minute | `5` / `30` / `100` |
| `SENTRY_DSN` / `SENTRY_TRACING_ENABLED` / `SENTRY_TRACES_SAMPLE_RATE` | Monitoring erreurs (optionnel) | (vides) |
| `NEXT_PUBLIC_API_URL` | Base URL exposee au bundle frontend | `/api/v1` |
| `BACKEND_INTERNAL_URL` | Cible de la rewrite Next.js (build-time) | `http://backend:8000` |

## CI/CD GitHub Actions

6 workflows dans `.github/workflows/`. Image Docker poussee vers `ghcr.io/<repo>` (tag `sha`, et `latest` uniquement sur `main`).

| Workflow | Trigger | Description |
|---|---|---|
| `ci.yml` | push (`main`, `feature/**`) + PR vers `main` | Pipeline principal : detect-changes (paths-filter), lint (ruff + eslint, toujours), test matrix (`sqlite` + `postgres:16-alpine`), build Docker (Buildx + cache GHA), scan Trivy |
| `playwright.yml` | push + PR `main`/`master` | E2E : `docker compose up --build`, seed admin, attente health, `npx playwright test` (3 navigateurs), upload `playwright-report/` |
| `secret-scan.yml` | push + PR | Scan secrets (gitleaks ou equivalent) sur l'historique recent |
| `dependabot-auto-merge.yml` | PR Dependabot | Auto-merge des updates patch/minor une fois la CI verte |
| `claude-code-review.yml` | PR | Revue automatisee assistee par Claude (commentaires sur le diff) |
| `claude.yml` | manuel / event | Tache utilitaire Claude Code (issue/PR triggered) |

Secrets CI : `CI_ENCRYPTION_KEY` (test). Credentials E2E : `PLAYWRIGHT_ADMIN_EMAIL=admin@assistantaudit.fr`, `PLAYWRIGHT_ADMIN_PASSWORD=Admin1234!`. Le `concurrency.group=ci-$ github.ref ` annule les runs obsoletes.

## Volumes & persistance

| Volume | Type | Service | Donnee |
|---|---|---|---|
| `pgdata` | named volume Docker | `db` | Donnees PostgreSQL (`/var/lib/postgresql/data`) |
| `app-certs` | named volume Docker | `backend` | CA mTLS, cle privee, CRL (`/app/certs`) |
| `./data` | bind mount | `backend` | Artefacts collecte, uploads, fichiers chiffres (`/app/data`) |
| `./tools/monkey365` | bind mount | `backend` | Module Monkey365 (PS1) - lecture |
| `./frameworks` | bind mount | `backend` | Referentiels YAML (CIS, ANSSI, ISO 27001, NIS2) auto-syncs en DB au demarrage |

Sauvegarde : `pgdata` (dump PostgreSQL) + `app-certs` (cle CA) + `./data` sont les jeux a backup obligatoirement. Voir runbook.md pour la procedure.

## Securite

| Domaine | Mesure |
|---|---|
| Transport agents | mTLS X.509, CA emise par le backend, CRL servie depuis `CRL_PATH` |
| Chiffrement DB | AES-256-GCM via `cryptography 46.0.7`, TypeDecorator `EncryptedJSON` (enveloppe KEK + DEK) |
| Chiffrement fichiers | KEK = `FILE_ENCRYPTION_KEY` ; DEK par fichier ; rotation via `backend/scripts/rotate_kek.py` |
| Auth utilisateurs | bcrypt 5.0.0 pour hash + JWT signe par `SECRET_KEY` (PyJWT >= 2.10) |
| Rate-limit | In-memory par IP (auth/api/public) - voir piege ci-dessous |
| Reverse proxy | NPMPlus / Caddy ; `FORWARDED_ALLOW_IPS` restrict ; `--proxy-headers` uvicorn |
| Secrets repo | `gitleaks` via `secret-scan.yml` ; `.env` dans `.gitignore` |
| CODEOWNERS | `@T0SAGA97` proprietaire global + zones sensibles (`security.py`, `encryption.py`, `file_encryption.py`, `cert_manager.py`, `deps.py`, `rate_limit.py`, `auth.py`, `Dockerfile*`, `docker-compose.yml`, `.github/`, `backend/alembic/`) |
| Scan image | Trivy bloquant sur CRITICAL (job `scan` dans `ci.yml`) |
| Multi-tenant | Isolation par `owner_id` (entreprise) + RBAC |

## Pieges connus

| Sujet | Detail | Reference |
|---|---|---|
| Redirect 307 leak hostname Docker | Starlette renvoie un `Location` avec `netloc=backend:8000` (rewrite Next.js). Playwright sur le runner hors Docker ne resout pas ce hostname. Workaround : `echo "127.0.0.1 backend" >> /etc/hosts` sur le runner. | `.github/workflows/playwright.yml` (step *Mappe le hostname Docker*) |
| Rate-limiter in-memory non partage | Compteurs par processus uvicorn ; multi-worker = quotas multiplies. En E2E, on releve a `10000` (`RATE_LIMIT_*_MAX`). | `backend/app/core/rate_limit.py`, `playwright.yml` env |
| `EmailStr` refuse les TLD reserves | Pydantic + `email-validator` rejettent `.test`, `.example`, `.invalid`, `.localhost`. Utiliser un domaine reel pour les fixtures (`admin@assistantaudit.fr`). | `playwright.yml` (`PLAYWRIGHT_ADMIN_EMAIL`) |
| `BACKEND_INTERNAL_URL` build-time | La rewrite Next.js est figee a la construction de l'image `frontend`. Changer l'URL impose un rebuild. | `docker-compose.yml` (build args), `next.config.ts` |
| `POSTGRES_PASSWORD` sans defaut | Variable obligatoire ; absence = erreur explicite Docker. Tous les `docker compose exec` qui interpolent doivent avoir l'env charge. | `docker-compose.yml` (`${POSTGRES_PASSWORD:?...}`) |
| `FORWARDED_ALLOW_IPS=*` | Acceptable tant que le port 8000 n'est pas public. A restreindre des qu'on expose le backend hors du proxy. | `docker-compose.yml` (`FORWARDED_ALLOW_IPS`) |

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.

**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.

**Last Updated** : 2026-05-02

- **Proprietaire :** `ln-115-devops-docs-creator`
- **Source de verite :** `docker-compose.yml`, `Dockerfile`, `Dockerfile.frontend`, `.env.example`, `.github/workflows/`
- **A mettre a jour quand :**
  - Ajout/suppression d'un service Docker
  - Changement de port, de healthcheck, de limits CPU/RAM ou de volume
  - Nouvelle variable d'environnement (refleter aussi dans `.env.example` et `runbook.md`)
  - Nouveau workflow GitHub Actions ou nouvelle cible de deploiement
  - Changement de serveur, de reverse proxy ou de domaine
  - Decouverte d'un nouveau piege CI/E2E (ajouter dans le tableau dedie)
- **Hors-scope (ne pas documenter ici) :** procedures executables (deploy, restart, troubleshoot, rotation cle, sauvegarde) -> `docs/project/runbook.md` ; design API -> `docs/project/api_spec.md` ; schema DB -> `docs/project/database_schema.md`.
