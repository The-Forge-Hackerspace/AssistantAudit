
# Runbook — AssistantAudit

<!-- SCOPE: Runbook operationnel — comment demarrer, deployer, migrer, surveiller, sauvegarder, restaurer et depanner AssistantAudit (Docker + manuel). -->
<!-- DOC_KIND: how-to -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu deploies, demarres, migres, surveilles ou depannes l'application. -->
<!-- SKIP_WHEN: Tu cherches l'inventaire infra (infrastructure.md) ou l'API. -->
<!-- PRIMARY_SOURCES: docker-compose.yml, .env.example, backend/init_db.py, backend/docker_entrypoint.py, start.ps1 -->
## Quick Navigation

- [Prerequis](#prerequis)
- [Demarrage rapide Docker](#demarrage-rapide-docker)
- [Demarrage Windows (start.ps1)](#demarrage-windows-startps1)
- [Demarrage manuel backend](#demarrage-manuel-backend)
- [Demarrage manuel frontend](#demarrage-manuel-frontend)
- [Migrations Alembic](#migrations-alembic)
- [Tests](#tests)
- [Generation des cles](#generation-des-cles)
- [Operations courantes](#operations-courantes)
- [Surveillance et metriques](#surveillance-et-metriques)
- [Logs](#logs)
- [Sauvegardes](#sauvegardes)
- [Rollback](#rollback)
- [Troubleshooting](#troubleshooting)
- [Securite operationnelle](#securite-operationnelle)
- [Maintenance](#maintenance)

## Agent Entry

Document destine aux operateurs et agents IA realisant le deploiement, la maintenance et le depannage de la plateforme. Les commandes sont en anglais ; le texte explicatif est en francais. Stack : FastAPI 0.135 (Python 3.13) + Next.js 16 + PostgreSQL 16, orchestre via `docker compose` ou `start.ps1` (Windows). Toutes les commandes sont a executer depuis la racine du depot, sauf indication contraire.

## Prerequis

| Element | Version | Note |
|---|---|---|
| Docker Engine | >= 24 | Inclut le driver `compose` v2 — verifier `docker compose version` |
| Docker Compose | v2 (plugin) | Le projet utilise la syntaxe `docker compose` (pas `docker-compose`) |
| Git | >= 2.40 | Pour cloner et suivre le depot |
| Python | 3.13 | Requis seulement pour le mode manuel backend |
| Node.js | 22 LTS | Requis seulement pour le mode manuel frontend (image Docker fait deja le build) |
| PowerShell | 7+ | Requis pour `start.ps1` (Windows) et l'agent collecte M365/AD |
| curl + jq | recents | Tests manuels (`tests/manual/test-all.sh`) |

## Demarrage rapide Docker

1. `git clone https://github.com/The-Forge-Hackerspace/AssistantAudit`
2. `cd AssistantAudit`
3. `cp .env.example .env` puis editer (au minimum : `SECRET_KEY`, `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`, `ENCRYPTION_KEY`, `FILE_ENCRYPTION_KEY`)
4. `docker compose up -d`
5. Acceder aux endpoints : Frontend `http://localhost:3000` ; API `http://localhost:8000` ; Swagger `http://localhost:8000/docs`
6. Identifiants admin : login `admin`, mot de passe = valeur de `ADMIN_PASSWORD` (affiche dans les logs au premier demarrage si absent : `docker compose logs backend | head -50`)

## Demarrage Windows (start.ps1)

| Mode | Commande | Description |
|---|---|---|
| Developpement | `.\start.ps1 --dev` | Logs DEBUG, hot-reload uvicorn et `npm run dev` |
| Production locale | `.\start.ps1 --build` | `next build` + uvicorn multi-workers |
| Verbose (alias dev) | `.\start.ps1 --verbose` | Equivalent fonctionnel a `--dev` |

Le script gere : verification des prerequis, copie automatique de `.env.example` vers `.env`, telechargement/mise a jour des outils (Monkey365), `init_db.py`, demarrage des services, rotation de logs, arret propre via Ctrl+C.

## Demarrage manuel backend

| Etape | Commande |
|---|---|
| 1. Aller dans le backend | `cd backend` |
| 2. (Premiere fois) initialiser la DB | `python init_db.py` |
| 3. Lancer uvicorn (hot-reload) | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |

`init_db.py` applique `alembic upgrade head`, cree l'utilisateur `admin` (variable `ADMIN_PASSWORD` requise) et synchronise les referentiels YAML depuis `frameworks/`.

## Demarrage manuel frontend

| Etape | Commande |
|---|---|
| 1. Aller dans le frontend | `cd frontend` |
| 2. Installer les dependances | `npm install` |
| 3. Lancer Next.js dev | `npm run dev` |

Build production : `npm run build` puis `npm run start` (port 3000 par defaut).

## Migrations Alembic

| Action | Commande |
|---|---|
| Creer une revision auto-generee | `cd backend && alembic revision --autogenerate -m "describe_change"` |
| Appliquer toutes les migrations | `cd backend && alembic upgrade head` |
| Revenir d'un cran (rollback) | `cd backend && alembic downgrade -1` |
| Voir l'historique | `cd backend && alembic history` |

Ne jamais renommer une colonne existante : ajouter une nouvelle colonne. Le `docker_entrypoint.py` applique automatiquement `alembic upgrade head` au demarrage du conteneur.

## Tests

| Type | Commande |
|---|---|
| Backend (pytest, 909+ tests) | `cd backend && pytest -q` |
| E2E Playwright | `npx playwright test` (depuis la racine) |
| Tests manuels (bash + curl + jq) | `bash tests/manual/test-all.sh` |
| Lint backend | `cd backend && ruff check .` |
| Lint frontend | `cd frontend && npm run lint` |

Configuration pytest centralisee dans `backend/pyproject.toml` (`[tool.pytest.ini_options]`) :

- `testpaths = ["tests"]` — collecte limitee a `backend/tests/`.
- `markers = ["slow", "integration"]` — utiliser `@pytest.mark.slow` ou `@pytest.mark.integration` pour cibler les tests longs ou dependants d'un service externe ; filtrage via `pytest -m "not slow"` ou `pytest -m integration`.
- `filterwarnings` : les `DeprecationWarning` issus de `pythonjsonlogger` sont escalades en erreur (signal pour la migration vers `pythonjsonlogger.json`) ; ceux de `sentry_sdk.push_scope` sont ignores (legacy hors de notre controle).

CI connue : redirection 307 fuite hostname Docker, rate-limiter in-memory non partage entre processus, `EmailStr` refuse les TLD reserves — adapter les fixtures en consequence.

## Generation des cles

| Cle | Commande |
|---|---|
| `SECRET_KEY` (>= 32 chars) | `python -c 'import secrets; print(secrets.token_urlsafe(64))'` |
| `ENCRYPTION_KEY` (64 hex) | `python -c 'import os; print(os.urandom(32).hex())'` |
| `FILE_ENCRYPTION_KEY` (64 hex) | `python -c 'import os; print(os.urandom(32).hex())'` |
| `POSTGRES_PASSWORD` | `python -c 'import secrets; print(secrets.token_urlsafe(24))'` |
| `ADMIN_PASSWORD` | au choix, fort, >= 12 caracteres recommande |

Stocker ces valeurs dans un gestionnaire de secrets (Vault, 1Password, etc.) — jamais dans le depot.

## Operations courantes

| Operation | Commande / Note |
|---|---|
| Voir l'etat des services | `docker compose ps` |
| Suivre les logs (tous services) | `docker compose logs -f` |
| Suivre les logs backend | `docker compose logs -f backend` |
| Shell dans le backend | `docker compose exec backend bash` |
| Redemarrer un service | `docker compose restart backend` |
| Reconstruire une image | `docker compose build backend && docker compose up -d backend` |
| Appliquer migrations a chaud | `docker compose exec backend python -m alembic upgrade head` |
| Rotation de la KEK fichiers | `docker compose exec backend python scripts/rotate_kek.py` |
| Injecter donnees de demo | `docker compose exec backend python scripts/seed_demo.py` (ou `DEMO=true` dans `.env`) |
| Seed checkpoints ANSSI | `docker compose exec backend python scripts/seed_anssi_checkpoints.py` |
| Seed checklists | `docker compose exec backend python scripts/seed_checklist_*.py` |
| Seed tags | `docker compose exec backend python scripts/seed_tags.py` |
| (Re)generer le CA mTLS agents | `docker compose exec backend python scripts/init_ca.py` |
| Synchroniser un framework YAML | redemarrer backend ou appel API `POST /api/v1/frameworks/sync` |
| Arret propre | `docker compose down` (ajouter `-v` pour purger les volumes) |

## Surveillance et metriques

| Endpoint | Description |
|---|---|
| `GET /api/v1/health` | Liveness (utilise par le healthcheck Docker) |
| `GET /api/v1/health/ready` | Readiness (DB + dependances pretes) |
| `GET /api/v1/metrics` | Metriques Prometheus (`prometheus-client`) si expose |

Surveiller en plus : `docker compose ps` (etat `healthy`), CPU/RAM via `docker stats`, taille des volumes `pgdata` et `app-certs`.

## Logs

Les logs backend sont structures en JSON via `python-json-logger`, niveau pilote par `LOG_LEVEL` (`DEBUG` recommande en dev, `INFO` en prod). Les erreurs sont remontees a Sentry si `SENTRY_DSN` est defini ; tracing optionnel via `SENTRY_TRACING_ENABLED` et `SENTRY_TRACES_SAMPLE_RATE`.

| Source | Commande |
|---|---|
| Backend | `docker compose logs --tail=200 backend` |
| Frontend | `docker compose logs --tail=200 frontend` |
| PostgreSQL | `docker compose logs --tail=200 db` |
| Logs persistants (option) | definir `LOG_FILE=/chemin/vers/logs/assistantaudit.log` |

## Sauvegardes

| Cible | Methode | Frequence |
|---|---|---|
| Volume `pgdata` (PostgreSQL) | `docker compose exec db pg_dump -U assistantaudit assistantaudit > backup-$(date +%F).sql` | Quotidienne |
| Volume `app-certs` (CA mTLS) | `docker run --rm -v assistantaudit_app-certs:/data -v $PWD:/backup alpine tar czf /backup/app-certs-$(date +%F).tgz /data` | A chaque rotation CA |
| Bind-mount `./data` (uploads + DEK) | rsync ou tar vers stockage chiffre | Quotidienne |
| `.env` | gestionnaire de secrets (Vault, 1Password, etc.) | A chaque changement |
| Frameworks YAML | suivis dans git (`frameworks/`) | A chaque commit |

Tester regulierement la restauration : `psql < backup.sql` sur une instance jetable.

## Rollback

| Type | Procedure |
|---|---|
| Migration DB | `docker compose exec backend python -m alembic downgrade -1` puis redeployer l'image precedente |
| Image Docker | `docker compose pull` (tag precedent) ou rebuild depuis le tag git anterieur, `docker compose up -d` |
| Code applicatif | `git checkout <tag-stable>` puis `docker compose build && docker compose up -d` |
| `.env` | restaurer depuis le gestionnaire de secrets ; redemarrer les services impactes |
| Donnees | restauration `pg_restore` du dump le plus recent, replay des fichiers depuis sauvegarde `./data` |

## Troubleshooting

| Symptome | Cause probable | Resolution |
|---|---|---|
| Backend ne demarre pas (exit immediat) | `SECRET_KEY` manquante ou < 32 chars en prod/staging/preprod | Definir `SECRET_KEY` (cf. [Generation des cles](#generation-des-cles)) puis `docker compose up -d backend` |
| Erreur "ENCRYPTION_KEY required" | `ENCRYPTION_KEY` ou `FILE_ENCRYPTION_KEY` absente en prod | Generer 64 hex chars, ajouter au `.env`, redemarrer |
| Frontend affiche "Network Error" | CORS bloque ou `BACKEND_INTERNAL_URL` mal configure | Ajuster `CORS_ORIGINS` dans `.env` ; verifier que `BACKEND_INTERNAL_URL` est `http://backend:8000` au build du frontend |
| HTTP 429 frequents | Rate-limiter declenche (5/30/100 par minute par IP) | Relacher temporairement via `RATE_LIMIT_AUTH_MAX`, `RATE_LIMIT_API_MAX`, `RATE_LIMIT_PUBLIC_MAX` (E2E : valeurs >= 10000) |
| Agent Windows ne se connecte pas | Certificat mTLS expire ou revoque (`CRL_PATH`) | Reexecuter `scripts/init_ca.py`, redeployer le bundle agent, redemarrer le backend |
| Uploads echouent (403/500) | Permissions `DATA_DIR` manquantes ou bind-mount incorrect | Verifier `DATA_DIR=./data` ; `chown -R 1000:1000 ./data` (UID conteneur) ; verifier espace disque |
| Migrations Alembic en conflit | Branche divergente | `alembic merge -m "merge heads" <rev1> <rev2>` puis `alembic upgrade head` |
| Healthcheck backend KO | DB pas prete au demarrage | `start_period: 15s` deja configure ; verifier `db` healthy via `docker compose ps` |
| Login admin impossible au 1er run | `ADMIN_PASSWORD` non defini lors du `up -d` | Ajouter au `.env`, `docker compose down && docker compose up -d` (admin cree sur DB vide uniquement) |
| Redirection 307 leak hostname Docker (CI) | Reverse proxy ou test client mal configure | Forcer `Host` header dans les requetes ; ajuster `FORWARDED_ALLOW_IPS` |
| `EmailStr` rejette un email de test | TLD reserve (`.test`, `.invalid`) | Utiliser un domaine reel-like (`example.com`) dans les fixtures |

## Securite operationnelle

Avant tout deploiement en production, valider la checklist (issue de `.env.example`) :

- [ ] `SECRET_KEY` defini, >= 32 caracteres, genere aleatoirement
- [ ] `ADMIN_PASSWORD` fort et unique
- [ ] `ENCRYPTION_KEY` defini (64 hex chars)
- [ ] `FILE_ENCRYPTION_KEY` defini (64 hex chars)
- [ ] `POSTGRES_PASSWORD` fort et unique
- [ ] `DATABASE_URL` pointe vers PostgreSQL avec `sslmode=require` (pas SQLite)
- [ ] `ENV=production`
- [ ] `.env` jamais commit (verifier `.gitignore` et `secret-scan.yml`)
- [ ] Cles stockees dans un gestionnaire de secrets (Vault, 1Password, etc.)
- [ ] `FORWARDED_ALLOW_IPS` restreint a l'IP du reverse proxy si le port 8000 devient public
- [ ] Reverse proxy (NPMPlus prod / Caddy staging) termine TLS et applique HSTS
- [ ] `DEMO` reste a `false` en production
- [ ] Sauvegardes `pgdata`, `app-certs`, `./data` testees et chiffrees au repos

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

| Champ | Valeur |
|---|---|
| Owner | ln-115-devops-docs-creator |
| Sources lues | `.env.example`, `docker-compose.yml`, `start.ps1`, `backend/docker_entrypoint.py`, `backend/init_db.py`, context store |
| Mise a jour | A chaque changement dans `.env.example`, `docker-compose.yml`, `Dockerfile*`, scripts `backend/scripts/`, ou procedures d'exploitation |
| Documents lies | `docs/project/infrastructure.md` (inventaire), `docs/project/architecture.md`, `docs/project/tech_stack.md` |
| Verification | Apres chaque modification, executer `docker compose up -d` sur une machine propre et derouler la section [Demarrage rapide Docker](#demarrage-rapide-docker) ; verifier `pytest -q` et `npx playwright test` |
