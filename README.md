# AssistantAudit

Outil d'audit d'infrastructure IT — évaluation de conformité des équipements réseau, serveurs et services cloud.

## Démarrage rapide

```bash
# Installer les dépendances
cd backend
pip install -r requirements.txt

# Initialiser la base de données + admin + référentiels
python init_db.py

# Lancer le serveur
python -m uvicorn app.main:app --reload --port 8000
```

**Swagger UI** : http://localhost:8000/docs
**Identifiants** : `admin` / `Admin@2026!`

## Structure du projet

```
AssistantAudit/
├── backend/            API FastAPI (Python)
│   ├── app/
│   │   ├── api/v1/     Routes (28 endpoints)
│   │   ├── core/       Config, auth JWT, BDD
│   │   ├── models/     Modèles SQLAlchemy
│   │   ├── schemas/    Schémas Pydantic
│   │   ├── services/   Logique métier
│   │   └── tools/      Nmap, Monkey365
│   ├── alembic/        Migrations
│   ├── tests/          Tests pytest
│   └── init_db.py      Initialisation
├── frameworks/         7 référentiels YAML (114 contrôles)
├── API.md              Documentation API
├── ARCHITECTURE.md     Architecture détaillée
├── Dockerfile
└── docker-compose.yml
```

## Référentiels d'audit

| Référentiel | Contrôles |
|-------------|-----------|
| Firewall | 20 |
| Switch / Réseau | 18 |
| Serveur Windows | 15 |
| Serveur Linux | 16 |
| Active Directory | 17 |
| Microsoft 365 | 18 |
| Wi-Fi | 10 |

## Documentation

- [API.md](API.md) — Référence complète des endpoints
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture et choix techniques

## Stack

FastAPI · SQLAlchemy 2.0 · Pydantic v2 · JWT · SQLite/PostgreSQL · Alembic
