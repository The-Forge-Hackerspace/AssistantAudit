# AssistantAudit — Architecture

> Outil d'audit d'infrastructure IT inspiré de CISO Assistant,
> centré sur l'évaluation de conformité des équipements réseau, serveurs et services cloud.

---

## Vue d'ensemble

```
AssistantAudit/
├── backend/              ← API FastAPI (Python 3.12+)
│   ├── app/
│   │   ├── api/          ← Routes HTTP (controllers)
│   │   ├── core/         ← Configuration, sécurité, BDD
│   │   ├── models/       ← Modèles SQLAlchemy (ORM)
│   │   ├── schemas/      ← Schémas Pydantic (validation)
│   │   ├── services/     ← Logique métier
│   │   └── tools/        ← Outils intégrés (nmap, monkey365…)
│   ├── alembic/          ← Migrations de base de données
│   ├── tests/            ← Tests automatisés
│   └── init_db.py        ← Script d'initialisation
├── frameworks/           ← Référentiels d'audit (YAML)
├── Dockerfile
├── docker-compose.yml
└── .env                  ← Variables d'environnement
```

---

## Stack technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| **API** | FastAPI 0.128+ | Framework web async, validation automatique, Swagger UI |
| **ORM** | SQLAlchemy 2.0 | Accès base de données avec `mapped_column` |
| **Validation** | Pydantic v2 | Sérialisation/désérialisation, validation des entrées |
| **Auth** | python-jose + bcrypt | Tokens JWT (access + refresh), hashing bcrypt |
| **BDD** | SQLite (dev) / PostgreSQL (prod) | Stockage persistant |
| **Migrations** | Alembic | Versioning du schéma de BDD |
| **Serveur** | Uvicorn | Serveur ASGI haute performance |

---

## Architecture en couches

Le backend suit le pattern **Service Layer** qui sépare clairement les responsabilités :

```
Requête HTTP
     │
     ▼
┌─────────────┐
│   API Layer │  Routes FastAPI (api/v1/*.py)
│  (Routes)   │  Validation entrée/sortie via Pydantic
└──────┬──────┘  Gestion des erreurs HTTP
       │
       ▼
┌─────────────┐
│  Services   │  Logique métier (services/*.py)
│   Layer     │  Orchestration, règles de gestion
└──────┬──────┘  Indépendant du transport HTTP
       │
       ▼
┌─────────────┐
│   Models    │  Modèles SQLAlchemy (models/*.py)
│   Layer     │  Définition du schéma de données
└──────┬──────┘  Relations, contraintes
       │
       ▼
   ┌────────┐
   │  BDD   │   SQLite / PostgreSQL
   └────────┘
```

### Règles

- Les **routes** ne contiennent pas de logique métier, uniquement du routing et de la validation.
- Les **services** sont des classes statiques appelées par les routes. Ils reçoivent une session SQLAlchemy.
- Les **modèles** définissent le schéma et les relations. Pas de logique applicative.
- Les **schémas Pydantic** sont séparés des modèles ORM pour découpler la validation de la persistance.

---

## Modules détaillés

### `backend/app/core/` — Noyau

| Fichier | Responsabilité |
|---------|---------------|
| `config.py` | Configuration centralisée via `pydantic-settings`. Charge `.env` automatiquement. Singleton avec `@lru_cache`. |
| `database.py` | Engine SQLAlchemy, session factory (`SessionLocal`), `get_db()` pour l'injection de dépendances. Active les FK SQLite. |
| `security.py` | Hashing bcrypt (sans passlib), création/décodage de tokens JWT (access + refresh). |
| `deps.py` | Dépendances FastAPI réutilisables : `get_current_user`, `get_current_admin`, `PaginationParams`. |

### `backend/app/models/` — Modèles de données

```
models/
├── user.py           ← Utilisateurs (admin, auditeur, lecteur)
├── entreprise.py     ← Entreprises et contacts
├── audit.py          ← Projets d'audit (avec statut)
├── site.py           ← Sites physiques
├── equipement.py     ← Équipements (héritage STI : réseau, serveur, firewall)
├── scan.py           ← Scans réseau (hosts, ports)
├── framework.py      ← Référentiels, catégories, contrôles
└── assessment.py     ← Campagnes, assessments, résultats de contrôle
```

#### Diagramme relationnel simplifié

```
Entreprise ──1:N── Contact
     │
     ├──1:N── Audit ──1:N── AssessmentCampaign ──1:N── Assessment
     │                                                     │
     └──1:N── Site ──1:N── Equipement (STI) ───────────────┘
                       │                           │
                       └──1:N── ScanHost           ├── framework_id → Framework
                                  ↑                │
                       ScanReseau─┘                └──1:N── ControlResult
                                                                │
                                                                └── control_id → Control

Framework ──1:N── FrameworkCategory ──1:N── Control
```

#### Héritage STI (Single Table Inheritance)

Les équipements utilisent l'héritage à table unique :

| Classe | Type | Champs spécifiques |
|--------|------|--------------------|
| `Equipement` | Base | ip_address, hostname, fabricant, os_detected, status_audit |
| `EquipementReseau` | `reseau` | vlan_config, ports_status, firmware_version |
| `EquipementServeur` | `serveur` | os_version_detail, modele_materiel, role_list, cpu_ram_info |
| `EquipementFirewall` | `firewall` | license_status, vpn_users_count, rules_count |

### `backend/app/schemas/` — Validation Pydantic

Chaque domaine a ses schémas `Create`, `Update`, `Read` :

| Fichier | Schémas principaux |
|---------|-------------------|
| `common.py` | `PaginatedResponse[T]`, `MessageResponse` |
| `user.py` | `LoginRequest`, `TokenResponse`, `UserCreate`, `UserRead`, `PasswordChange` |
| `entreprise.py` | `EntrepriseCreate/Update/Read`, `ContactCreate/Read` |
| `audit.py` | `AuditCreate/Update/Read/Detail` |
| `site.py` | `SiteCreate/Update/Read` |
| `equipement.py` | `EquipementCreate/Update/Read/Summary` |
| `framework.py` | `FrameworkRead`, `FrameworkSummary`, `CategoryRead`, `ControlRead` |
| `assessment.py` | `CampaignCreate/Update/Read/Summary`, `AssessmentCreate/Read`, `ControlResultUpdate/Read` |

Tous les schémas `Read` utilisent `model_config = {"from_attributes": True}` pour la conversion ORM → Pydantic.

### `backend/app/services/` — Logique métier

| Service | Rôle |
|---------|------|
| `AuthService` | Authentification, création de tokens, gestion utilisateurs, changement de mot de passe. |
| `FrameworkService` | Import/export YAML ↔ BDD, listing et recherche de référentiels. Supporte la mise à jour (upsert par `ref_id`). |
| `AssessmentService` | Création de campagnes, génération automatique des `ControlResult` à partir des contrôles d'un framework, mise à jour unitaire et en masse. |

### `backend/app/api/v1/` — Routes API

| Fichier | Préfixe | Endpoints |
|---------|---------|-----------|
| `health.py` | `/health` | 1 |
| `auth.py` | `/auth` | 5 |
| `entreprises.py` | `/entreprises` | 5 |
| `audits.py` | `/audits` | 5 |
| `sites.py` | `/sites` | 5 |
| `equipements.py` | `/equipements` | 5 |
| `frameworks.py` | `/frameworks` | 4 |
| `assessments.py` | `/assessments` | 8 |
| **Total** | | **38** |

Tous les sous-routers sont agrégés dans `router.py` sous le préfixe `/api/v1`.

### `backend/app/tools/` — Outils intégrés

| Outil | Statut | Description |
|-------|--------|-------------|
| `nmap_scanner/` | Fonctionnel | Scanner réseau via subprocess nmap, parsing XML avec defusedxml. |
| `monkey365_runner/` | Fonctionnel | Exécuteur Monkey365 (audit M365) via PowerShell, parsing JSON des résultats. |
| `config_parsers/` | Stub | Parseurs de configurations réseau (futur). |
| `collectors/` | Stub | Collecteurs SSH/WinRM pour récupérer des configs (futur). |

---

## Référentiels d'audit (`frameworks/`)

Les référentiels sont définis en **YAML** et importés en base de données. Chacun décrit un ensemble de contrôles organisés par catégories.

### Structure d'un fichier YAML

```yaml
id: FW                                   # Identifiant unique
name: Audit Firewall
description: Référentiel d'audit firewall
version: "1.0"
engine: null                             # ou "monkey365" pour M365

categories:
  - name: Configuration générale
    order: 1
    controls:
      - ref_id: FW-CFG-01
        title: Vérifier la version du firmware
        description: Le firmware doit être à jour
        severity: high                   # critical | high | medium | low | info
        check_type: manual               # manual | automatic | semi-automatic
        remediation: Mettre à jour le firmware
        evidence_required: true
        cis_reference: "CIS 1.1"        # Référence CIS Benchmark (optionnel)
        engine_rule_id: null             # Règle Monkey365 (optionnel)
```

### Référentiels livrés

| Référentiel | Contrôles | Categories | Engine |
|-------------|-----------|------------|--------|
| Firewall | 20 | 6 | — |
| Switch / Réseau | 18 | 5 | — |
| Serveur Windows | 15 | 6 | — |
| Serveur Linux | 16 | 5 | — |
| Active Directory | 17 | 6 | — |
| Microsoft 365 | 18 | 8 | Monkey365 |
| Wi-Fi | 10 | 4 | — |

---

## Authentification & Sécurité

### Flux JWT

```
Client                          API
  │                              │
  ├── POST /auth/login ────────► │
  │   (username + password)      │
  │                              ├── Vérifie bcrypt hash
  │  ◄── { access_token,  ──────┤
  │       refresh_token }        │
  │                              │
  ├── GET /entreprises ────────► │
  │   Authorization: Bearer xxx  │
  │                              ├── Décode JWT
  │                              ├── Charge User depuis BDD
  │  ◄── { items: [...] } ──────┤
```

### Injection de dépendances

```python
@router.get("/entreprises")
async def list_entreprises(
    pagination: PaginationParams = Depends(),    # Pagination auto
    db: Session = Depends(get_db),               # Session BDD
    user: User = Depends(get_current_user),      # Auth JWT
):
```

FastAPI résout automatiquement la chaîne : Token → Décodage → Chargement User → Injection.

---

## Base de données

### Développement

SQLite, fichier stocké dans `backend/instance/assistantaudit.db`. Créé automatiquement au premier démarrage.

### Production

PostgreSQL recommandé. Changer `DATABASE_URL` dans `.env` :

```env
DATABASE_URL=postgresql://user:password@localhost:5432/assistantaudit
```

### Migrations

```bash
cd backend
alembic revision --autogenerate -m "description"   # Générer
alembic upgrade head                                # Appliquer
alembic downgrade -1                                # Rollback
```

---

## Démarrage

### Développement

```bash
cd backend
python init_db.py                                           # Première fois
python -m uvicorn app.main:app --reload --port 8000         # Serveur dev
```

### Docker

```bash
docker-compose up --build
```

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DEBUG` | `True` | Mode debug (logs SQL, auto-create tables) |
| `SECRET_KEY` | `dev-only-...` | Clé de signature JWT — **changer en prod** |
| `DATABASE_URL` | `sqlite:///...` | URL de connexion BDD |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Durée de validité du token |
| `FRAMEWORKS_DIR` | `../frameworks` | Chemin vers les fichiers YAML |
| `MONKEY365_PATH` | — | Chemin vers `Invoke-Monkey365.ps1` |
| `NMAP_TIMEOUT` | `600` | Timeout nmap en secondes |

---

## Flux d'audit typique

```
1. Créer une Entreprise
        │
2. Créer un Audit (projet) lié à l'entreprise
        │
3. Créer des Sites et Équipements dans l'audit
        │
4. Créer une Campagne d'évaluation
        │
5. Pour chaque équipement :
   └── Créer un Assessment (équipement + référentiel)
       └── Les ControlResults sont générés automatiquement
            │
6. Évaluer chaque contrôle :
   └── PUT /assessments/results/{id}
       └── status: compliant / non_compliant / ...
            │
7. Le score de conformité se calcule automatiquement
        │
8. Terminer la campagne → rapport
```

---

## Évolutions prévues

| Phase | Composant | Description |
|-------|-----------|-------------|
| **Frontend** | React / Next.js | Interface web avec dashboards de conformité |
| **Rapports** | Jinja2 + WeasyPrint | Génération PDF automatique |
| **Scans** | Nmap intégré | Découverte réseau automatique → création d'équipements |
| **M365** | Monkey365 | Exécution automatique des contrôles Microsoft 365 |
| **Collecteurs** | SSH / WinRM | Récupération automatique de configurations |
| **Référentiels** | YAML supplémentaires | Backup, DNS/DHCP, VPN, imprimantes |
| **Multi-tenant** | Isolation par entreprise | Gestion multi-clients |
