# AssistantAudit

Plateforme d'audit d'infrastructure IT — évaluation de conformité des équipements réseau, serveurs, services cloud et périphériques. Interface web complète avec outils intégrés (Nmap, analyse SSL/TLS, parseurs de configuration).

---

## Fonctionnalités

- **Gestion multi-entreprises / multi-sites** — suivi des entreprises, sites et équipements audités
- **14 référentiels d'audit YAML** (200 contrôles) — firewall, switch, serveurs Windows/Linux, Active Directory, Microsoft 365, Wi-Fi, VPN, DNS/DHCP, messagerie, sauvegarde, périphériques, OPNsense
- **Évaluation de conformité** — scoring par contrôle (conforme / partiel / non-conforme / N/A), commentaires, pièces jointes
- **Scanner réseau Nmap** — découverte d'hôtes, scan de ports, détection d'OS, mode personnalisé (commande nmap libre), import automatique des équipements
- **Analyse SSL/TLS** — vérification des certificats, protocoles, suites de chiffrement
- **Parseur de configuration** — analyse des configs Fortinet FortiGate et OPNsense (interfaces, règles, VPN, NAT)
- **Intégration Monkey365** — audit Microsoft 365 / Azure AD automatisé
- **Authentification JWT** — rôles admin, auditeur, lecteur
- **Export YAML** — export des référentiels personnalisés
- **Versioning** — historique des modifications sur les référentiels

## Stack technique

| Composant | Technologies |
| ----------- | ------------- |
| **Backend** | Python 3.13 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Alembic |
| **Frontend** | Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · shadcn/ui · Recharts |
| **Auth** | JWT (python-jose + bcrypt) |
| **BDD** | SQLite (dev) / PostgreSQL (prod) |
| **Outils** | Nmap · OpenSSL · Monkey365 · PingCastle |
| **Infra** | Docker · Docker Compose |

## Démarrage rapide

### Prérequis

- **Python 3.12+**
- **Node.js 20+** et npm
- **PowerShell 7+** (recommandé pour Monkey365)
- **Git** (recommandé pour le téléchargement automatique des outils)
- **Nmap** (optionnel, pour le scanner réseau)

### Installation automatique

```bash
# Cloner le projet
git clone <url> && cd AssistantAudit

# Windows (PowerShell 7 recommandé) :

# Mode standard
.\start.ps1

# Mode développement (logs DEBUG + hot-reload)
.\start.ps1 --dev

# Mode production (build optimisé)
.\start.ps1 --build
```

**Nouveautés v2.0 du script de démarrage :**
- ✨ Téléchargement automatique de **Monkey365** (similaire à PingCastle)
- ✨ Création automatique du fichier `.env` avec SECRET_KEY générée
- ✨ Mode `--dev` avec logs verbeux sur tous les composants
- ✨ Mode `--build` pour tests de performance
- ✨ Rotation automatique des logs (max 10MB)
- ✨ Gestion améliorée des processus avec fichiers PID
- ✨ Validation PowerShell 7+ pour Monkey365

📖 **Guide détaillé :** Voir [START_GUIDE.md](START_GUIDE.md) pour toutes les fonctionnalités

### Installation manuelle

```bash
# 1. Backend
cd backend
python -m venv ../venv
# Linux: source ../venv/bin/activate
# Windows: ..\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Initialiser la BDD + admin + référentiels
python init_db.py

# 3. Lancer le backend
cd ..
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Frontend (dans un autre terminal)
cd frontend
npm install
npm run dev
```

### Accès

| Service | URL |
| ----------- | ----- |
| **Frontend** | <http://localhost:3000> |
| **API** | <http://localhost:8000> |
| **Swagger UI** | <http://localhost:8000/docs> |
| **ReDoc** | <http://localhost:8000/redoc> |

**Identifiants par défaut** : `admin` / `Admin@2026!`

### Docker

```bash
docker-compose up --build
```

## Structure du projet

```text
AssistantAudit/
├── backend/                    API FastAPI (Python)
│   ├── app/
│   │   ├── api/v1/             75 endpoints REST
│   │   │   ├── auth.py         Authentification (login, register, refresh, password)
│   │   │   ├── entreprises.py  CRUD entreprises
│   │   │   ├── sites.py        CRUD sites
│   │   │   ├── equipements.py  CRUD équipements
│   │   │   ├── audits.py       CRUD audits
│   │   │   ├── frameworks.py   Référentiels (CRUD, sync, import/export, clone)
│   │   │   ├── assessments.py  Évaluations (scoring, résultats, statistiques)
│   │   │   ├── attachments.py  Pièces jointes
│   │   │   ├── scans.py        Scanner réseau (lancement, résultats, décisions)
│   │   │   ├── tools.py        Outils (config parser, SSL checker)
│   │   │   └── health.py       Healthcheck
│   │   ├── core/               Config, auth JWT, BDD, dépendances
│   │   ├── models/             10 modèles SQLAlchemy
│   │   ├── schemas/            Schémas Pydantic (validation I/O)
│   │   ├── services/           Logique métier
│   │   └── tools/              Outils intégrés
│   │       ├── nmap_scanner/   Scanner Nmap (discovery, ports, full, custom)
│   │       ├── ssl_checker/    Vérificateur SSL/TLS
│   │       ├── config_parsers/ Parseurs Fortinet + OPNsense
│   │       ├── monkey365_runner/ Bridge Monkey365
│   │       └── collectors/     Collecteurs de données
│   ├── alembic/                Migrations de schéma
│   ├── tests/                  Tests pytest
│   ├── init_db.py              Initialisation BDD + admin
│   └── requirements.txt
├── frontend/                   Interface Next.js
│   └── src/
│       ├── app/                13 pages
│       │   ├── login/          Connexion
│       │   ├── entreprises/    Gestion des entreprises
│       │   ├── sites/          Gestion des sites
│       │   ├── equipements/    Inventaire des équipements
│       │   ├── audits/         Audits et évaluation
│       │   ├── frameworks/     Référentiels d'audit
│       │   ├── outils/         Hub outils
│       │   │   ├── scanner/    Scanner réseau Nmap
│       │   │   ├── ssl-checker/Analyse SSL/TLS
│       │   │   └── config-parser/ Parseur de configuration
│       │   └── profile/        Profil utilisateur
│       ├── components/         Composants UI (shadcn/ui)
│       ├── services/           Client API Axios
│       ├── contexts/           Auth context
│       ├── hooks/              Hooks personnalisés
│       └── types/              Types TypeScript
├── frameworks/                 14 référentiels YAML (200 contrôles)
├── data/                       Données d'audit (configs, exports)
├── start.sh                    Script de démarrage (Linux/macOS)
├── start.ps1                   Script de démarrage (Windows)
├── docker-compose.yml
├── Dockerfile
├── API.md                      Documentation API complète
├── ARCHITECTURE.md             Architecture et choix techniques
└── CONCEPT.md                  Concept et vision du projet
```

## Référentiels d'audit

| Référentiel | Contrôles | Description |
| ------------- | --------- | ------------- |
| Firewall | 20 | Règles, NAT, VPN, HA, logs |
| Switch / Réseau | 18 | VLAN, STP, port security, ACL |
| Messagerie | 18 | SPF, DKIM, DMARC, antispam, chiffrement |
| Microsoft 365 | 18 | Azure AD, MFA, conditional access, DLP |
| Active Directory | 17 | GPO, Kerberos, LDAPS, comptes à privilèges |
| DNS / DHCP | 17 | DNSSEC, transferts de zone, baux, scope |
| Sauvegarde | 17 | Politique 3-2-1, rétention, tests de restauration |
| Périphériques | 16 | Imprimantes, IoT, firmwares, accès réseau |
| Serveur Linux | 16 | SSH, firewall, mises à jour, partitionnement |
| VPN | 16 | Protocoles, certificats, split tunneling, MFA |
| Serveur Windows | 15 | GPO, BitLocker, pare-feu, RDP, antivirus |
| Wi-Fi | 10 | WPA3, segmentation, portail captif, rogue AP |
| OPNsense | 1 | Audit spécifique OPNsense |

## Configuration

Variables d'environnement (fichier `.env` à la racine) :

```env
# Sécurité (OBLIGATOIRE en production)
SECRET_KEY=votre-cle-secrete-de-32-caracteres-minimum

# Base de données
DATABASE_URL=sqlite:///./instance/assistantaudit.db
# DATABASE_URL=postgresql://user:password@localhost:5432/assistantaudit

# Application
ENV=development          # development | production
DEBUG=true
LOG_LEVEL=INFO

# Outils
NMAP_TIMEOUT=600         # Timeout Nmap en secondes
MONKEY365_PATH=          # Chemin vers Invoke-Monkey365.ps1
PINGCASTLE_PATH=         # Chemin vers PingCastle.exe (auto-configuré par start.ps1)
PINGCASTLE_TIMEOUT=300   # Timeout PingCastle en secondes
```

## PingCastle — Audit Active Directory avancé

PingCastle est un outil d'audit Active Directory qui fournit un healthcheck approfondi du domaine AD avec des scores de risque et des recommandations de sécurité.

### Configuration automatique (Windows)

Sur Windows, le script `start.ps1` clone automatiquement le dépôt PingCastle depuis GitHub et configure le chemin dans `.env` :

```powershell
# Le script télécharge et configure PingCastle automatiquement
.\start.ps1
```

Le dépôt PingCastle sera cloné dans `tools/pingcastle/` et mis à jour automatiquement à chaque lancement.

### Configuration manuelle

Si vous préférez télécharger PingCastle manuellement :

1. Téléchargez la dernière version depuis [https://github.com/netwrix/pingcastle/releases](https://github.com/netwrix/pingcastle/releases)
2. Extrayez `PingCastle.exe` dans un répertoire de votre choix
3. Configurez le chemin dans `.env` :

```env
PINGCASTLE_PATH=C:\chemin\vers\PingCastle.exe
```

### Utilisation

PingCastle propose deux modes d'utilisation dans AssistantAudit :

#### 1. Audit automatisé (Healthcheck)

Depuis l'interface web (`http://localhost:3000/outils/pingcastle`), onglet **Audit automatisé** :

- Saisissez les informations du contrôleur de domaine
- Lancez l'audit en arrière-plan
- Consultez les résultats : scores de risque, règles violées, niveau de maturité
- Utilisez les findings pour pré-remplir automatiquement les contrôles d'audit AD

#### 2. Terminal interactif

Depuis l'interface web, onglet **Terminal interactif** :

- Ouvrez un terminal PingCastle complet avec menu interactif
- Naviguez dans les options d'audit (healthcheck, scanner, etc.)
- Consultez les rapports en temps réel

### Intégration avec les référentiels d'audit

Les résultats PingCastle peuvent être utilisés pour pré-remplir automatiquement les contrôles du référentiel Active Directory :

- **AD-001** : Comptes privilégiés (score PingCastle Privileged Accounts)
- **AD-002** : Objets obsolètes (score Stale Objects)
- **AD-010** : Relations d'approbation (score Trusts)
- **AD-012** : Anomalies (score Anomaly)
- **AD-020** : Score global

```

## Documentation

- [API.md](API.md) — Référence complète des 75 endpoints
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture technique et choix de conception
- [CONCEPT.md](CONCEPT.md) — Vision et concept du projet
- [Swagger UI](http://localhost:8000/docs) — Documentation interactive des API

## Licence

Projet interne — tous droits réservés.
