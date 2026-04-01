# Infrastructure et déploiement

---

## Docker — Image multi-stage

| Stage | Base | Rôle |
|-------|------|------|
| Stage 1 | `node:22-alpine` | Build du frontend Next.js (export statique) |
| Stage 2 | `python:3.13-slim` | Backend FastAPI + static frontend intégré |

L'image finale contient uniquement le runtime Python, les fichiers statiques du frontend et le code backend. L'utilisateur applicatif est `appuser` (non-root).

---

## Docker Compose — Services

| Service | Image | Port | Dépendance |
|---------|-------|------|------------|
| `db` | `postgres:16-alpine` | 5432 | — |
| `backend` | Image locale | 8000 | `db` |
| `frontend` | Image locale (ou dev) | 3000 | `backend` |

**Volumes Docker :**

| Volume | Contenu |
|--------|---------|
| `pgdata` | Données PostgreSQL persistantes |
| `app-data` | Fichiers uploadés, rapports PDF |
| `app-certs` | Certificats TLS |
| `frameworks` | Bind mount vers `./frameworks/` (YAML auto-sync) |

---

## Environnements

| Variable | Development | Production |
|----------|-------------|------------|
| Base de données | SQLite (`dev.db`) | PostgreSQL 16 |
| Swagger UI | Activé (`/docs`) | Désactivé |
| DEBUG | `true` | `false` |
| Reload uvicorn | `--reload` | — |

---

## Entrypoint — `docker_entrypoint.py`

Logique d'initialisation au démarrage du conteneur :

1. **Nouvelle base** — `create_all()` (SQLAlchemy) + `alembic stamp head`
2. **Base existante** — `alembic upgrade head` (migrations incrémentales)
3. Sync automatique des frameworks YAML vers la DB

---

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé de signature JWT |
| `DATABASE_URL` | URL SQLAlchemy (`postgresql://` ou `sqlite:///`) |
| `ENCRYPTION_KEY` | Clé AES-256-GCM pour EncryptedText |
| `FILE_ENCRYPTION_KEY` | Clé AES-256-GCM pour les fichiers joints |
| `ENV` | `development` ou `production` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CORS_ORIGINS` | Liste des origines autorisées (JSON array) |
| `MONKEY365_PATH` | Chemin vers l'installation Monkey365 |
| `DATA_DIR` | Répertoire de stockage des fichiers |
| `CERTS_DIR` | Répertoire des certificats TLS |

---

## Sécurité

- Conteneur exécuté sous `appuser` (UID non-root)
- Swagger UI désactivé en production (`ENV=production`)
- Middleware de security headers sur toutes les réponses
- Tokens JWT signés avec `SECRET_KEY` (HS256)

---

## CI/CD — GitHub Actions

| Workflow | Déclencheur | Description |
|----------|-------------|-------------|
| `playwright.yml` | push / pull_request | Tests end-to-end Playwright |
