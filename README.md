# AssistantAudit

Plateforme d'audit de sécurité IT destinée aux équipes Red Team, auditeurs de conformité et consultants en cybersécurité.

AssistantAudit centralise l'ensemble du cycle d'audit : collecte automatique de données, évaluation de conformité sur des référentiels standards (CIS, ANSSI, ISO 27001, NIS2…), gestion des preuves et reporting — le tout depuis une interface web unique.

---

## Objectifs

- **Automatiser la collecte** — scans réseau (Nmap), vérification TLS, collecte SSH/WinRM, audit Active Directory, audit Microsoft 365 (Monkey365), analyse de configs pare-feu
- **Centraliser l'évaluation** — 15 référentiels de conformité YAML (363 contrôles), auto-synchronisés à chaque démarrage
- **Tracer les résultats** — statuts par contrôle (conforme / non conforme / partiel / N/A), pièces justificatives, historique par campagne
- **Exposer une API REST complète** — 45+ endpoints documentés (Swagger/ReDoc), intégration possible avec des outils tiers

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.13, FastAPI 0.115+, SQLAlchemy 2, Pydantic v2, Alembic |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, shadcn/ui |
| Base de données | SQLite (développement) — PostgreSQL (production, planifié) |
| Auth | JWT (access 15 min + refresh 7 jours), RBAC 3 niveaux |
| Outils intégrés | Nmap, OpenSSL, Paramiko (SSH), pywinrm, ldap3, Monkey365 (PowerShell), PingCastle |

---

## Prérequis

- **Python 3.13+**
- **Node.js 18+**
- **PowerShell 7+** (`pwsh` dans le PATH) — requis uniquement pour Monkey365
- **Git**
- Optionnel : Nmap (scan réseau), OpenSSL (analyse TLS)

---

## Démarrage rapide (Windows)

```powershell
# 1. Cloner le dépôt
git clone https://github.com/The-Forge-Hackerspace/AssistantAudit
cd AssistantAudit

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env : au minimum, définir SECRET_KEY

# 3. Lancer la stack complète
.\start.ps1 --dev
```

`start.ps1` crée le venv Python, installe les dépendances, initialise la base, lance le backend (port 8000) et le frontend (port 3000).

```
Frontend  : http://localhost:3000
API       : http://localhost:8000
Swagger   : http://localhost:8000/docs
ReDoc     : http://localhost:8000/redoc
```

Les identifiants admin par défaut sont affichés dans le terminal au premier démarrage — à changer immédiatement.

---

## Démarrage manuel

### Backend

```bash
cd backend
python -m venv ../venv
# Windows : ..\venv\Scripts\Activate.ps1
# Linux/macOS : source ../venv/bin/activate
pip install -r requirements.txt

python init_db.py                                          # première fois uniquement
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000
```

---

## Configuration

Copier `.env.example` en `.env` à la racine du projet :

```env
# Obligatoire en production
SECRET_KEY=your-secret-key-min-32-chars

# Base de données
DATABASE_URL=sqlite:///./instance/assistantaudit.db
# DATABASE_URL=postgresql://user:password@localhost:5432/assistantaudit

# Environnement
ENV=development          # development | production
LOG_LEVEL=INFO

# Outils (chemins absolus)
MONKEY365_PATH=C:\path\to\Invoke-Monkey365.ps1
MONKEY365_ARCHIVE_PATH=C:\data\monkey365
PINGCASTLE_PATH=C:\path\to\PingCastle.exe

# Timeouts (secondes)
NMAP_TIMEOUT=600
PINGCASTLE_TIMEOUT=300
MONKEY365_TIMEOUT=600

# Admin initial (optionnel — généré automatiquement sinon)
ADMIN_PASSWORD=your-secure-password
```

---

## Architecture

```
Frontend (Next.js)
    │ Axios + JWT interceptor
    ▼
REST API (FastAPI) — 45 endpoints, RBAC
    │
    ├── Services (logique métier)
    │     ├── framework_service    — sync YAML ↔ DB (SHA-256)
    │     ├── assessment_service   — campagnes, évaluations, scoring
    │     ├── monkey365_service    — scan M365, mapping vers contrôles
    │     ├── scan_service         — Nmap
    │     ├── collect_service      — SSH/WinRM (Linux, Windows, FortiGate, OPNsense)
    │     ├── ad_audit_service     — LDAP
    │     ├── pingcastle_service   — PingCastle runner
    │     └── config_analysis_service — parse configs pare-feu
    │
    └── SQLAlchemy ORM → SQLite / PostgreSQL
```

Règle fondamentale : `Router → Service → Model`. Les routers ne font jamais de requêtes DB directement.

---

## Référentiels de conformité

15 référentiels YAML dans `frameworks/` — auto-synchronisés au démarrage via hash SHA-256 :

| ref_id | Nom | Moteur | Contrôles |
|--------|-----|--------|-----------|
| `ANSSI-GUIDE-SECURITE-AD` | Guide sécurité AD (ANSSI) | `manual` | 29 |
| `ANSSI-PA-022` | Recommandations AD (ANSSI PA-022) | `manual` | 18 |
| `CIS-AZURE-V3` | CIS Microsoft Azure Foundations v3 | `manual` | 29 |
| `CIS-ENTRA-ID-V2` | CIS Microsoft Entra ID v2 | `manual` | 12 |
| `CIS-LINUX-V3` | CIS Linux Benchmark v3 | `collect_ssh` | 27 |
| `CIS-M365-V3` | CIS Microsoft 365 Foundations v3 | `monkey365` | 52 |
| `CIS-M365-V5` | CIS Microsoft 365 Foundations v5 | `monkey365` | 130 |
| `CIS-WINDOWS-SERVER-2022` | CIS Windows Server 2022 | `manual` | 23 |
| `DORA` | Digital Operational Resilience Act | `manual` | 14 |
| `HADS` | Hébergement de Données de Santé | `manual` | 18 |
| `ISO-27001-2022` | ISO/IEC 27001:2022 | `manual` | 23 |
| `NIS2` | Directive NIS2 | `manual` | 16 |
| `PASSI` | Prestataires d'Audit de la Sécurité des SI | `manual` | 8 |
| `SOC2-TYPE2` | SOC 2 Type II | `manual` | 20 |

Moteurs : `manual` (évaluation humaine), `monkey365` (automatisé via PowerShell), `collect_ssh` (collecte SSH).

Pour ajouter un référentiel : créer `frameworks/{REF_ID}.yaml` et redémarrer le backend.

---

## Outils intégrés

| Outil | Usage | Dépendance |
|-------|-------|------------|
| **Nmap** | Découverte réseau, ports, OS | `nmap` dans le PATH |
| **SSL Checker** | Analyse certificats TLS, protocoles | `openssl` |
| **SSH/WinRM Collector** | Collecte config Linux, Windows, FortiGate, OPNsense, Stormshield | `paramiko`, `pywinrm` |
| **AD Auditor** | Audit Active Directory via LDAP | `ldap3` |
| **PingCastle** | Score de santé AD, rapport HTML | `PingCastle.exe` (Windows) |
| **Monkey365** | Audit complet Microsoft 365 / Entra ID | `pwsh` + `Invoke-Monkey365.ps1` |
| **Config Parser** | Analyse règles pare-feu FortiGate / OPNsense | — |

### Monkey365 — installation des modules PowerShell

```powershell
# Une seule fois, sur le poste Windows qui exécute les scans
.\install_m365_modules.ps1
```

Monkey365 nécessite une session desktop Windows pour l'authentification interactive MSAL (Device Code / Interactive). Il n'est pas compatible avec les serveurs headless.

---

## Commandes de développement

```bash
# Tests backend
cd backend
pytest -q
pytest tests/test_monkey365_executor.py -v

# Migrations DB
alembic revision --autogenerate -m "description"
alembic upgrade head

# Build frontend
cd frontend
npm run build
npm run lint

# Démarrage production
.\start.ps1 --build
```

---

## Modèle de sécurité

- **JWT** : access token 15 min + refresh token 7 jours
- **RBAC** : `admin` > `auditeur` > `lecteur` (vérifié dans `core/deps.py`)
- **Rate limiting** : 5 tentatives/minute sur `POST /auth/login`, blocage 5 min
- **Mots de passe** : hachés avec bcrypt
- **Isolation** : pas de `shell=True` dans les appels subprocess, pas de chemins absolus codés en dur

---

## Feuille de route

**Court terme**
- Génération de rapports PDF/Word
- Tests unitaires et E2E (couverture > 80 %)
- Pipeline CI/CD

**Moyen terme**
- Migration PostgreSQL pour la production
- Permissions RBAC avancées
- Intégration SIEM

**Long terme**
- Suggestions de remédiation assistées par IA
- Marketplace de référentiels personnalisés

---

## Licence

Propriétaire — tous droits réservés. Pour toute demande de licence, contacter les mainteneurs.

---

**Mainteneur :** T0SAGA97
**Dépôt :** https://github.com/The-Forge-Hackerspace/AssistantAudit
