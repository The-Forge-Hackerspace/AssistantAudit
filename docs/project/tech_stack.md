# Stack technique — AssistantAudit

## Backend

| Catégorie | Bibliothèques / Versions |
|-----------|--------------------------|
| Framework | Python 3.13, FastAPI 0.135.1, Uvicorn 0.42.0 |
| ORM / Migrations | SQLAlchemy 2.0.48, Alembic 1.18.4 |
| Validation | Pydantic 2.12.5 |
| Sécurité | python-jose 3.5.0 (JWT), bcrypt 5.0.0, cryptography 46.0.6 |
| Protocoles réseau | paramiko 4.0.0 (SSH), pywinrm 0.5.0, ldap3 2.9.1, defusedxml 0.7.1 |
| Génération de documents | WeasyPrint 63.1 (PDF), python-docx 1.1.2, Jinja2 3.1.6 |
| Base de données | psycopg2-binary (PostgreSQL), PyYAML 6.0.3 |
| Observabilité | sentry-sdk 2.55.0, prometheus-client 0.24.1, python-json-logger 4.0.0 |

## Frontend

| Catégorie | Bibliothèques / Versions |
|-----------|--------------------------|
| Framework | Next.js 16.2.0, React 19.2.3, TypeScript 5 |
| Style | Tailwind CSS v4, shadcn/ui (Radix UI primitives) |
| Données | Axios 1.13.5, SWR 2.4.0, Zod 4.3.6 |
| Formulaires / Graphiques | react-hook-form 7.72.0, recharts 2.15.4, @xyflow/react 12.9.2 |
| UI divers | lucide-react, next-themes, sonner (toasts), js-cookie |
| Terminal | @xterm/xterm 6.0.0 |

## Base de données

| Environnement | Technologie |
|---------------|-------------|
| Développement | SQLite |
| Production | PostgreSQL 16 (Docker) |
| Migrations | 31 migrations Alembic, 36+ tables |

## Infrastructure

| Composant | Détail |
|-----------|--------|
| Conteneurisation | Docker multi-stage (Python 3.13-slim + Node 22-alpine) |
| Orchestration | Docker Compose — 3 services : `db`, `backend`, `frontend` |
| Automatisation | PowerShell 7 (modules Monkey365) |

## Outils intégrés

| Catégorie | Outils |
|-----------|--------|
| Réseau / Audit | Nmap, OpenSSL, Paramiko, pywinrm, ldap3 |
| Cloud / AD | Monkey365 (PowerShell) |
| Parseurs config | Fortinet, OPNsense |

## Tests

| Catégorie | Outils |
|-----------|--------|
| Backend | pytest 9.0.2, pytest-cov, pytest-mock, pytest-asyncio |
| Frontend E2E | Playwright |
