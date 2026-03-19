# AssistantAudit — Concept & Feuille de Route

> **Document vivant** — Dernière mise à jour : Sprint 0 Audit (2026-03-20)
> Ce fichier est notre boussole : il décrit la vision, l'architecture, les décisions prises et l'avancement réel du projet.

---

## 🎯 Vision

Un outil d'audit d'infrastructure IT inspiré de CISO Assistant, mais centré sur **l'audit technique d'infrastructure**, avec :

- Des **référentiels d'audit par type d'équipement** (firewall, switch, serveur, AD, M365…)
- Des **outils intégrés** de collecte et d'évaluation automatique
- Un **moteur Monkey365** pour l'audit cloud Microsoft 365
- Une **interface web moderne** pour piloter les campagnes d'audit
- Un **système de scoring** automatique de la conformité

---

## 📐 Architecture Réelle du Projet

```text
┌──────────────────────────────────────────────────────────────┐
│                      AssistantAudit                          │
├──────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 16 + React + Tailwind + shadcn/ui)       │
│  ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐ │
│  │ Dashboard │ │Gestion   │ │ Audits &  │ │ Référentiels │ │
│  │ & Stats   │ │Entreprise│ │ Campagnes │ │ & Contrôles  │ │
│  └───────────┘ └──────────┘ └───────────┘ └──────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  API REST (FastAPI + Pydantic v2 + JWT OAuth2)              │
│  45 endpoints — Documentation Swagger auto-générée          │
├──────────────────────────────────────────────────────────────┤
│  Core Engine                                                │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │ Référentiels  │ │ Moteur       │ │ Scoring &        │   │
│  │ dynamiques    │ │ d'évaluation │ │ Conformité auto  │   │
│  │ (12 YAML)     │ │              │ │                  │   │
│  └───────────────┘ └──────────────┘ └──────────────────┘   │
│  ┌───────────────┐ ┌──────────────┐                        │
│  │ Monkey365     │ │ Versioning   │                        │
│  │ Bridge (M365) │ │ frameworks   │                        │
│  └───────────────┘ └──────────────┘                        │
├──────────────────────────────────────────────────────────────┤
│  Outils Intégrés (Phase 4 — à venir)                        │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐         │
│  │Scanner │ │Config  │ │Collecte│ │Analyse      │         │
│  │Réseau  │ │Parser  │ │Auto    │ │Auto         │         │
│  └────────┘ └────────┘ └────────┘ └─────────────┘         │
├──────────────────────────────────────────────────────────────┤
│  Data Layer (SQLAlchemy 2.0 + Alembic)                      │
│  SQLite (dev) → PostgreSQL (prod)                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Technique (Choix définitifs)

| Couche | Technologie | Statut |
| -------- | ------------- | -------- |
| **Backend** | Python 3.13 + FastAPI | ✅ En place |
| **ORM** | SQLAlchemy 2.0 + Alembic | ✅ En place |
| **Validation** | Pydantic v2 | ✅ En place |
| **Auth** | JWT (python-jose) + bcrypt direct + OAuth2 | ✅ En place |
| **BDD** | SQLite (dev) → PostgreSQL (prod) | ✅ SQLite actif |
| **Frontend** | Next.js 16 + React + TypeScript | ✅ En place |
| **UI Components** | shadcn/ui + Tailwind CSS v4 | ✅ En place |
| **HTTP Client** | Axios avec intercepteur JWT | ✅ En place |
| **Icônes** | Lucide React | ✅ En place |
| **Référentiels** | YAML dynamiques (sync SHA-256) | ✅ En place |
| **Cloud Audit** | Monkey365 (PowerShell) | ✅ Bridge prêt |
| **Rapports** | Jinja2 + WeasyPrint | 🔜 Phase 5 |
| **Outils** | python-nmap, paramiko, pywinrm, ldap3 | 🔜 Phase 4 |
| **Déploiement** | Docker + Docker Compose | ✅ Fichiers prêts |

---

## 📁 Structure Réelle du Projet

```text
AssistantAudit/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # 8 routeurs : auth, entreprises, sites,
│   │   │                        #   equipements, audits, frameworks,
│   │   │                        #   assessments, health
│   │   ├── core/                # config, database, security, deps
│   │   ├── models/              # 8 modèles SQLAlchemy (user, entreprise,
│   │   │                        #   site, equipement, audit, framework,
│   │   │                        #   assessment, scan)
│   │   ├── schemas/             # Schémas Pydantic v2 (in/out/update)
│   │   ├── services/            # Logique métier (auth, framework,
│   │   │                        #   assessment, monkey365)
│   │   └── tools/               # Monkey365 runner (parser, mapper),
│   │                            #   collectors, config_parsers, nmap_scanner
│   ├── alembic/                 # 2 migrations
│   ├── tests/                   # Tests API
│   ├── instance/                # SQLite DB
│   ├── init_db.py               # Script d'initialisation (admin + frameworks)
│   ├── test_phase1.py           # 38 tests Phase 1
│   ├── test_phase2.py           # 55 tests Phase 1+2
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Pages Next.js (App Router)
│   │   │   ├── page.tsx         # Dashboard (stats, audits, campagnes)
│   │   │   ├── login/page.tsx   # Page de connexion JWT
│   │   │   ├── layout.tsx       # Layout racine + Providers
│   │   │   └── providers.tsx    # AuthProvider + AuthGuard
│   │   ├── components/          # app-layout (sidebar), auth-guard,
│   │   │   └── ui/              #   + 20 composants shadcn/ui
│   │   ├── contexts/            # AuthContext (login/logout/refresh)
│   │   ├── services/            # API services (axios calls)
│   │   ├── types/               # Types TypeScript complets
│   │   └── lib/                 # api-client (axios + JWT interceptor)
│   ├── .env.local               # NEXT_PUBLIC_API_URL
│   └── package.json
│
├── frameworks/                  # 12 référentiels YAML
│   ├── firewall_audit.yaml
│   ├── switch_audit.yaml
│   ├── server_windows_audit.yaml
│   ├── server_linux_audit.yaml
│   ├── active_directory_audit.yaml
│   ├── wifi_audit.yaml
│   ├── sauvegarde_audit.yaml
│   ├── peripheriques_audit.yaml
│   ├── m365_audit.yaml
│   ├── messagerie_audit.yaml
│   ├── vpn_audit.yaml
│   └── dns_dhcp_audit.yaml
│
├── API.md                       # Documentation 45 endpoints
├── ARCHITECTURE.md              # Architecture technique
├── CONCEPT.md                   # ← Ce fichier (feuille de route)
├── README.md
├── docker-compose.yml
└── Dockerfile
```

---

## 📋 Plan en 6 Phases — État d'avancement

### ✅ Phase 1 — Fondations & Modèle de données (TERMINÉE)

**Objectif** : Poser l'architecture, le modèle de données et l'API REST complète.

| Tâche | Détail | Statut | Audit Sprint 0 |
| -------- | ------------- | -------- | -------- |
| Stack technique | Python 3.13 + FastAPI + SQLAlchemy 2.0 | ✅ | ✅ Validée |
| Modèle de données | 8 entités (User, Entreprise, Site, Equipement, Audit, Framework, Assessment, Scan) | ✅ | ⚠️ 24 models (audit counting inconsistency) |
| Structure projet | Monorepo backend/frontend/frameworks | ✅ | ✅ OK |
| Auth JWT | Inscription, login, refresh token, rôles (admin/auditor/viewer) | ✅ | ✅ Validated |
| CRUD complet | 45 endpoints REST pour toutes les entités | ✅ | ✅ All verified |
| Migrations | Alembic configuré avec 7 migrations | ✅ | ✅ Applied successfully |
| Tests | 12 tests automatisés | ✅ | ⚠️ Coverage gaps identified |
| CORS | Configuré pour localhost:3000 et localhost:5173 | ✅ | ⚠️ Must be env-based for prod |
| Docker | Dockerfile + docker-compose.yml | ✅ | ⏳ Not containerized yet |

**Modèle de données implémenté :**

```text
User (admin/auditor/viewer)
  └── Entreprise
       └── Site
            └── Equipement (type: serveur, firewall, switch...)

Framework (référentiel YAML)
  └── categories[] → controls[]
       └── Versionné (parent_version_id, ref_id unique + version)

Audit (campagne d'audit)
  └── Campaign (lien audit ↔ framework)
       └── Assessment (évaluation d'un équipement)
            └── ControlResult (résultat par contrôle)
                 ├── status: compliant/non_compliant/partial/not_applicable
                 ├── evidence (preuve)
                 ├── score (0-100)
                 └── recommendation

Score (calculé automatiquement par assessment)
  ├── total_controls
  ├── compliant_count / non_compliant_count
  ├── compliance_score (%)
  └── by_severity {critical, high, medium, low}
```

**Décisions techniques Phase 1 :**

- **bcrypt direct** au lieu de passlib (déprécié avec Python 3.13)
- **python-jose** pour les JWT
- **SQLite** en dev avec chemin absolu pour éviter les problèmes de CWD
- **Pydantic v2** avec `model_config = ConfigDict(from_attributes=True)`
- **Scoring automatique** : calcul du score de conformité à chaque évaluation

---

### ✅ Phase 2 — Moteur de Référentiels (TERMINÉE)

**Objectif** : Référentiels YAML structurés, versioning, export, et pont Monkey365.

| Tâche | Détail | Statut |
| ------- | ------------- | -------- |
| Format YAML | Structure standardisée pour tous les référentiels | ✅ |
| Import dynamique | Chargement depuis fichiers YAML avec sync auto | ✅ |
| 12 référentiels | Firewall, Switch, Windows, Linux, AD, Wi-Fi, Sauvegarde, Périphériques, M365, Messagerie, VPN, DNS/DHCP | ✅ |
| Versioning | Clone de framework avec incrémentation de version | ✅ |
| Export YAML | Endpoint d'export de framework vers YAML | ✅ |
| Sync dynamique | SHA-256 hash-based, sync au démarrage + endpoint POST /sync | ✅ |
| Monkey365 bridge | Parser JSON + Mapper règles → contrôles + Simulation | ✅ |
| Tests | 55 tests automatisés (Phase 1 + 2) — tous passent | ✅ |

**Les 12 référentiels :**

| # | Référentiel | Fichier YAML | Contrôles |
| -------- | ------------- | -------- | --------- |
| 1 | 🔥 Firewall | `firewall_audit.yaml` | Config, règles, logs, HA, VPN |
| 2 | 🔀 Switch | `switch_audit.yaml` | VLAN, STP, ACL, monitoring |
| 3 | 🖥️ Serveur Windows | `server_windows_audit.yaml` | OS, AD, services, sécurité |
| 4 | 🐧 Serveur Linux | `server_linux_audit.yaml` | SSH, firewall, users, logs |
| 5 | 📁 Active Directory | `active_directory_audit.yaml` | GPO, comptes, réplication |
| 6 | 📶 Wi-Fi | `wifi_audit.yaml` | SSID, chiffrement, auth, rogue |
| 7 | 💾 Sauvegarde | `sauvegarde_audit.yaml` | Politique, tests, offsite |
| 8 | 🖨️ Périphériques | `peripheriques_audit.yaml` | Firmware, accès, réseau |
| 9 | ☁️ Microsoft 365 | `m365_audit.yaml` | Entra ID, Exchange, SPO, Teams |
| 10 | 📧 Messagerie | `messagerie_audit.yaml` | SPF, DKIM, DMARC, anti-spam |
| 11 | 🔒 VPN | `vpn_audit.yaml` | Tunnels, auth, chiffrement |
| 12 | 🌐 DNS / DHCP | `dns_dhcp_audit.yaml` | Zones, DNSSEC, baux, scopes |

**Mécanisme de sync dynamique :**

```text
Au démarrage du serveur :
  1. Scan du dossier frameworks/*.yaml
  2. Calcul SHA-256 de chaque fichier
  3. Comparaison avec source_hash en base
  4. Si nouveau fichier → import automatique
  5. Si hash différent → mise à jour du framework
  6. Log détaillé des changements

Endpoint POST /api/v1/frameworks/sync :
  → Même logique, déclenchable manuellement
  → Retourne le détail : nouveaux, mis à jour, inchangés
```

**Décisions techniques Phase 2 :**

- **SHA-256** pour détecter les changements dans les fichiers YAML
- **`source_hash`** colonne ajoutée au modèle Framework
- **`engine_config`** JSON pour stocker la config Monkey365 dans le framework M365
- **`UniqueConstraint("ref_id", "version")`** pour gérer les versions
- **Simulation Monkey365** : endpoint de test sans environnement PowerShell réel

---

### 🔄 Phase 3 — Interface Utilisateur (EN COURS)

**Objectif** : Interface web moderne pour piloter les audits.

**Choix de stack frontend (décidé en session) :**

- **Next.js 16** (App Router, Turbopack)
- **React + TypeScript**
- **Tailwind CSS v4** + **shadcn/ui** (20 composants installés)
- **Axios** avec intercepteur JWT automatique
- **js-cookie** pour le stockage des tokens
- **Lucide React** pour les icônes

**Approche progressive — Dashboard en premier, puis CRUD.**

| Tâche | Détail | Statut |
| ------- | ------------- | -------- |
| Initialisation Next.js | Projet créé, shadcn/ui configuré | ✅ |
| Système d'auth | AuthContext, login page, AuthGuard, JWT cookies | ✅ |
| Layout principal | Sidebar avec navigation groupée, avatar utilisateur | ✅ |
| Dashboard | 6 stat cards cliquables, graphiques recharts, filtre entreprise | ✅ |
| Page Entreprises | Liste, création, modification, suppression | ✅ |
| Page Sites | CRUD avec lien vers entreprise parente | ✅ |
| Page Équipements | CRUD avec lien vers site parent, filtres type/statut | ✅ |
| Page Audits | Campagnes, assessments, évaluation, DELETE endpoints | ✅ |
| Page Référentiels | Liste, détail, éditeur/créateur YAML, versioning | ✅ |
| Page Évaluation | Interface contrôle par contrôle avec preuves & pièces jointes | ✅ |
| Visualisation | Graphiques radar, camembert, barres (recharts) | ✅ |
| Page Profil | Infos utilisateur, changement de mot de passe | ✅ |
| Dark mode | Toggle clair/sombre/système (next-themes) | ✅ |
| Toasts | Notifications sonner sur toutes les actions CRUD | ✅ |
| Skeletons | Chargement squelette sur toutes les pages listes | ✅ |

**Ce qui est déjà fonctionnel :**

```text
📊 Dashboard (page d'accueil après login)
  ├── 6 cartes statistiques cliquables (navigation vers page correspondante)
  ├── Filtre par entreprise pour les visualisations
  ├── Graphique camembert (statuts des audits)
  ├── Graphique barres (conformité par campagne)
  ├── Graphique radar (contrôles par sévérité)
  ├── Liste des audits récents avec statut et date
  ├── Campagnes en cours avec barre de progression et score
  └── Grille des référentiels disponibles

🔐 Authentification
  ├── Page de login avec formulaire username/password
  ├── Stockage JWT dans cookies (access_token + refresh_token)
  ├── Intercepteur Axios : injection automatique du token
  ├── Redirect automatique vers /login si token expiré (401)
  └── AuthGuard : protection de toutes les routes

🧭 Navigation (Sidebar)
  ├── Général → Dashboard
  ├── Gestion → Entreprises, Sites, Équipements
  ├── Audit → Projets d'audit, Référentiels
  └── Footer → Avatar utilisateur, rôle, menu (profil, déconnexion)

📋 Pages CRUD (toutes avec recherche, pagination, toast notifications)
  ├── Entreprises — Tableau + dialog création/modification/suppression
  ├── Sites — Filtrage par entreprise, CRUD complet
  ├── Équipements — Filtrage par site/type/statut, CRUD complet
  ├── Audits — Campagnes, assessments, suivi progression
  ├── Référentiels — Liste, détail, éditeur YAML complet, versioning
  └── Évaluation — Contrôle par contrôle, statut, preuves, pièces jointes

👤 Profil utilisateur
  ├── Informations du compte (nom, email, rôle, date création)
  └── Changement de mot de passe

🎨 Qualité UX
  ├── Dark mode (toggle clair/sombre/système)
  ├── Toast notifications (sonner) sur toutes les actions
  ├── Skeleton loading sur les pages listes
  ├── AlertDialog pour suppression (pas confirm())
  └── Constantes centralisées (labels, couleurs, icônes)
```

---

### 🔜 Phase 4 — Outils Intégrés (PLANIFIÉE)

**Objectif** : Automatiser la collecte et l'évaluation technique.

#### Phase 4a — Outils infrastructure

| Outil | Fonction | Technologie |
| -------- | ------------- | -------- |
| **Scanner réseau** | Découverte d'assets, ports ouverts | Nmap (python-nmap) |
| **Config Parser** | Analyser les configs exportées (Fortinet, Cisco...) | Parsers custom Python |
| **Collecte WinRM/SSH** | Récupérer infos serveurs automatiquement | Paramiko, pywinrm |
| **AD Auditor** | Requêtes LDAP pour auditer AD | ldap3, BloodHound integration |
| **Analyseur de règles FW** | Détecter les règles trop permissives | Parser custom |
| **Vérificateur SSL/TLS** | Tester les certificats et protocoles | ssl, cryptography |
| **Benchmark CIS** | Comparer configs vs CIS Benchmarks | Scripts d'évaluation |

#### Phase 4b — Monkey365 pour M365/Azure (Bridge prêt)

Le bridge Monkey365 est déjà implémenté en Phase 2 :

- `tools/monkey365_runner/parser.py` — Parse les JSON de sortie Monkey365
- `tools/monkey365_runner/mapper.py` — Mappe les findings vers les contrôles via `engine_rule_id`
- `services/monkey365_service.py` — `run_scan_and_map()` (réel) + `simulate_scan()` (dev/test)

**Workflow M365 :**

```text
1. Campagne avec référentiel M365 → config auth tenant
2. Lancement Monkey365 via bridge Python → PowerShell
3. Parse JSON résultats → Mapping auto vers contrôles
4. Pré-remplissage des statuts + preuves
5. Revue manuelle par l'auditeur
6. Rapport final
```

**Ce que Monkey365 couvre :**

| Domaine | Exemples de checks |
| -------- | ------------------- |
| **Entra ID** | MFA, Conditional Access, PIM, Guest policies |
| **Exchange Online** | Transport rules, DKIM/DMARC/SPF, Audit logging |
| **SharePoint Online** | Partage externe, accès anonyme, versioning |
| **OneDrive** | Politique de partage, sync client |
| **Teams** | Guest access, external sharing, meeting policies |
| **Compliance Center** | DLP, Retention, Audit logs |
| **Azure** | NSG, Storage, Key Vault, VMs, RBAC |

---

### 🔜 Phase 5 — Rapports & Remédiation (PLANIFIÉE)

| Tâche | Détail |
| ------- | -------- |
| Génération PDF | Rapport d'audit complet avec Jinja2 + WeasyPrint |
| Export Word | Template .docx personnalisable (python-docx) |
| Plan de remédiation | Priorisation automatique par sévérité et effort |
| Suivi des remédiations | Statut des actions correctives |
| Comparaison | Comparer deux audits dans le temps (progression) |

---

### 🔜 Phase 6 — Fonctionnalités Avancées (PLANIFIÉE)

| Tâche | Détail |
| ------- | -------- |
| Multi-tenant | Gestion de plusieurs clients |
| Scheduling | Planification d'audits récurrents |
| IA/LLM | Suggestions de remédiation assistées par IA |
| Marketplace de référentiels | Partage communautaire |
| Intégration SIEM | Import de données depuis Wazuh, Elastic... |
| Notifications | Alertes email/webhook sur événements |

---

## 🔑 Décisions Techniques Clés

### Authentification

- **bcrypt direct** (pas passlib, déprécié avec Python 3.13)
- **python-jose** pour encoder/décoder les JWT
- **OAuth2PasswordRequestForm** de FastAPI
- Tokens stockés dans **cookies** côté frontend (pas localStorage)
- Rôles : `admin`, `auditor`, `viewer` — vérification via dépendance FastAPI

### Base de données

- **SQLite** en développement (fichier `instance/assistantaudit.db`)
- Chemin absolu construit depuis `BASE_DIR` pour éviter les problèmes de CWD
- **Alembic** pour les migrations (2 migrations : schéma initial + phase 2)
- Migration vers **PostgreSQL** prévue pour la production

### Frameworks dynamiques

- Les référentiels YAML dans `frameworks/` sont la **source de vérité**
- **SHA-256** hash du fichier stocké en base (`source_hash`)
- **Sync automatique** au démarrage du serveur (lifespan FastAPI)
- **POST /api/v1/frameworks/sync** pour déclencher manuellement
- Modification du YAML → mise à jour automatique au prochain démarrage

### Frontend

- **Next.js App Router** (pas Pages Router)
- **shadcn/ui** — composants copiés dans le projet (pas de dépendance externe)
- **Intercepteur Axios** — ajoute le JWT à chaque requête, redirige vers `/login` sur 401
- **AuthGuard** — composant wrapper qui protège toutes les routes
- **Approche progressive** — Dashboard fonctionnel d'abord, puis pages CRUD

---

## 📊 Métriques du Projet

| Métrique | Valeur | Notes Sprint 0 |
| -------- | ------- | --------------- |
| Endpoints API | **45** | Backend audit verified |
| Models | **24** | Includes inherited types (audit discrepancy noted) |
| Frontend Pages | **17** | 100% implemented (16/17 protected) |
| Tests | **12** | Coverage gaps - only 40% of tools have tests |
| Lines of Code | **~37.59 MB** | Including dependencies |
| Référentiels YAML | 12 | With SHA-256 sync engine |
| Composants shadcn/ui | 25 | All actively used |
| Migrations Alembic | 7 | All applied successfully |

---

## 🚨 Known Issues & Technical Debt

**Status:** Sprint 0 audit completed 2026-03-20. Issues categorized by severity with recommended remediation timeline.

### 🚨 CRITICAL (Must Fix Before Production)

- **[Frontend]** Dashboard chart colors hardcoded (#22c55e, #ef4444, etc.) — don't adapt to dark mode (Keaton-Jr)
  - *Impact:* Poor UX contrast in dark mode; potential WCAG failure
  - *Fix:* Use `useTheme()` hook to apply theme-aware colors
  - *Effort:* 1-2 hours
  
- **[Frontend]** 4 icon buttons missing aria-labels in attachments section (eye, download, delete icons)
  - *Impact:* Accessibility violation; screen reader users cannot determine button purpose
  - *Fix:* Add `aria-label` to Button components
  - *Effort:* 15 minutes

- **[DevSecOps]** 7 npm high-severity vulnerabilities in frontend dependencies
  - *Packages:* Next.js (4 MODERATE), minimatch (HIGH), flatted (HIGH), @hono/node-server (HIGH)
  - *Fix:* `npm audit fix && npm audit fix --force`
  - *Effort:* 30 minutes
  - *Blocking:* Yes — must resolve before any deployment

- **[DevSecOps]** No CI/CD pipeline (Renault)
  - *Impact:* No automated security scanning; vulnerable packages not detected
  - *Fix:* Create .github/workflows for build-test, security-scan, gitleaks
  - *Effort:* 4-6 hours
  - *Timeline:* Sprint 0+1

### ⚠️ HIGH PRIORITY (Next Sprint)

- **[Database]** 5 N+1 query patterns identified (Kobayashi)
  - *Files:* Various ORM queries missing eager-loading
  - *Impact:* Performance degradation at scale
  - *Fix:* Use `joinedload()` and `selectinload()` in service layer
  - *Effort:* 3-4 hours

- **[Database]** 4 undeclared models need migration 008 (Kobayashi)
  - *Status:* Schema mismatch between code and database
  - *Fix:* Create migration for polymorphic inheritance subtypes
  - *Effort:* 2 hours

- **[Infrastructure]** 8 environment variable issues (Fortier)
  - *Examples:* Default admin credentials hardcoded; no health check retry logic; no env validation
  - *Fix:* Move to .env; add validation; improve error messages
  - *Effort:* 2 hours

- **[Tools]** Nmap scanner has no unit tests (Redfoot)
  - *Impact:* Whitelist/blacklist validation not covered
  - *Fix:* Add pytest tests for argument sanitization
  - *Effort:* 3 hours
  - *Critical Gap:* Strictest security posture; needs test coverage

- **[Tools]** SSL checker missing unit tests (Redfoot)
  - *Impact:* Protocol detection not verified
  - *Fix:* Add tests for TLS version detection, expiration logic
  - *Effort:* 2 hours

- **[Tools]** Config parsers (Fortinet, OPNsense) lack dedicated tests (Redfoot)
  - *Impact:* Vendor-specific parsing logic not covered
  - *Fix:* Create pytest suite with sample configs
  - *Effort:* 4 hours

### 📋 MEDIUM PRIORITY (Next 2 Sprints)

- **[Security]** SSH private keys passed as plaintext in API requests (Kujan)
  - *Issue:* `/api/v1/scans` accepts SSH keys in request body
  - *Fix:* Implement SSH key encryption at rest (AES-256)
  - *Effort:* 3-4 hours

- **[Security]** CORS origins hardcoded to localhost (Kujan)
  - *Issue:* production code will expose CORS to dev origins
  - *Fix:* Load CORS_ORIGINS from environment variables
  - *Effort:* 30 minutes
  - *Blocker:* For production deployment

- **[Database]** SQLite→PostgreSQL migration incomplete (Kobayashi)
  - *Status:* 85% compatible; 3 SQL dialect issues remain
  - *Examples:* AUTOINCREMENT syntax, CAST behavior, JSON operators
  - *Fix:* Create dialect-agnostic migration helper
  - *Effort:* 4-6 hours
  - *Timeline:* Before production scaling

- **[Infrastructure]** Hardcoded ports prevent multi-instance deployment (Fortier)
  - *Issue:* Backend port 8000, frontend port 3000 hard-coded
  - *Fix:* Parameterize PORT in .env
  - *Effort:* 1 hour

- **[Tools]** WinRM SSL validation disabled (development mode) (Redfoot)
  - *File:* `winrm_collector.py` lines 199-204
  - *TODO:* `configurer un CA bundle + validation stricte`
  - *Fix:* Implement proper certificate validation before production
  - *Effort:* 2 hours
  - *Status:* Acceptable for current phase; must fix before prod

- **[Tools]** AD Auditor, PingCastle, Collectors missing unit tests (Redfoot)
  - *Impact:* Remote execution logic not verified
  - *Effort:* 6-8 hours combined
  - *Timeline:* Before load testing

### 🔧 LOW PRIORITY / Tech Debt

- **[DevSecOps]** No Docker containerization yet (Renault)
  - *Status:* Application runs directly on Windows PowerShell
  - *Fix:* Create production-grade Dockerfile + docker-compose.yml
  - *Effort:* 4 hours

- **[DevSecOps]** Rate limiter in-memory only (acceptable for dev, need Redis for prod scale) (Renault)
  - *Effort:* 2 hours (for production scaling)

- **[Infrastructure]** PID files not cleaned on abnormal shutdown (zombie process risk) (Fortier)
  - *Fix:* Add cleanup handler in start.ps1
  - *Effort:* 1 hour

- **[Backend]** `ssh_collector.py` monolithic file (1,245 lines) should be split by profile (Redfoot)
  - *Effort:* 4 hours refactoring

- **[Backend]** `ad_auditor.py` monolithic file (669 lines) should be split by function category (Redfoot)
  - *Effort:* 3 hours refactoring

---

## 🧪 Tests & Qualité

### Comment lancer les tests backend

```bash
# 1. Arrêter le serveur s'il tourne
# 2. Supprimer la base existante
del backend\instance\assistantaudit.db

# 3. Réinitialiser la base (crée admin + importe les 12 frameworks)
cd backend
python init_db.py

# 4. Lancer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Lancer les tests (dans un autre terminal)
cd backend
python test_phase2.py
```

**Identifiants admin** : `admin` / mot de passe affiché lors de l'exécution de `init_db.py`

Vous pouvez forcer un mot de passe fixe en définissant `ADMIN_PASSWORD` avant l'initialisation.

### Comment lancer le frontend

```bash
cd frontend
npm run dev
# → http://localhost:3000
```

---

## 📝 Journal de Bord

### Session 1 — Phase 1 : Fondations

- Création du projet FastAPI complet
- 8 modèles, schémas, services, routes
- Auth JWT avec bcrypt
- 38 tests passent
- Analyse de gaps → ajout Alembic, scoring, rôles

### Session 2 — Phase 2 : Référentiels & Monkey365

- Versioning des frameworks (clone + version++)
- Export YAML d'un framework
- 5 nouveaux référentiels (total 12)
- Bridge Monkey365 : parser JSON, mapper, service de simulation
- 55 tests passent

### Session 3 — Frameworks Dynamiques

- Ajout `source_hash` SHA-256 sur les frameworks
- Sync automatique au démarrage du serveur
- Endpoint POST /frameworks/sync
- Les YAML sont désormais la source de vérité

### Session 4 — Phase 3 : Frontend (en cours)

- Choix du stack : Next.js + React + TypeScript + Tailwind + shadcn/ui
- Installation de 20 composants UI
- Pages créées : login, dashboard, layout avec sidebar
- Système d'auth complet : AuthContext, AuthGuard, intercepteur JWT
- Dashboard avec stats live depuis l'API
- Bug fix : gestion des scores null (`toFixed` sur undefined)

### Session 5 — Phase 3 : Pages CRUD complètes

- Pages CRUD : Entreprises, Sites, Équipements (tableaux + formulaires + pagination)
- Page Audits : gestion campagnes, assessments, navigation audit-détail
- Page Référentiels : liste, détail, éditeur/créateur YAML complet avec versioning
- Page Évaluation : interface contrôle par contrôle, statuts, preuves, pièces jointes
- Upload & gestion de pièces jointes (drag-drop, preview image/texte, téléchargement)
- Visualisation : graphiques radar, camembert, barres avec recharts

### Session 6 — Corrections & Améliorations UX (P0→P3)

- **Sécurité (P0)** : Correction path traversal dans attachments, upload streaming 8KB chunks
- **Fonctionnel (P1)** : DELETE endpoints campagnes/assessments, toast notifications (sonner), AlertDialog pour suppressions
- **Qualité (P2)** : Centralisation constantes UI, page profil + changement mot de passe, lien profil dans sidebar, suppression passlib
- **UX (P3)** : Dark mode (next-themes), skeleton loading, hooks SWR pour cache client, extraction composants (AttachmentSection)
- Dashboard : cartes statistiques cliquables, filtre par entreprise, graphiques recharts

---

## 🗺️ Prochaines Étapes (Phase 4)

1. **Scanner réseau** : Intégration Nmap pour découverte d'assets
2. **Config Parser** : Analyse des configurations exportées (Fortinet, Cisco...)
3. **Monkey365** : Lancement réel des scans M365/Azure via le bridge existant
4. **Intégration WinRM/SSH** : Collecte automatique d'infos serveurs
5. **Rapports** : Génération PDF/Word avec synthèse et plan de remédiation

---

## 🐒 Détail technique : Intégration Monkey365

### Architecture du bridge

```text
AssistantAudit (Python/FastAPI)
│
├── tools/monkey365_runner/
│   ├── parser.py        # Parse les JSON de sortie Monkey365
│   ├── mapper.py        # Mappe findings → contrôles via engine_rule_id
│   └── config.py        # Configuration auth tenant
│
├── services/
│   └── monkey365_service.py
│       ├── run_scan_and_map()    # Exécution réelle (PowerShell)
│       └── simulate_scan()       # Simulation pour dev/test
│
└── Référentiel m365_audit.yaml
    └── engine: "monkey365"
    └── engine_config: {provider, rulesets, auth_methods}
    └── Chaque contrôle a un engine_rule_id mappé
```

### Workflow d'audit M365

```text
┌──────────────────────────────────────────────────────────────┐
│ 1. CRÉATION CAMPAGNE                                         │
│    Sélection du référentiel "Audit M365"                     │
│    Configuration du tenant (tenant_id, auth method)          │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. SCAN AUTOMATIQUE                                          │
│    Lancement Monkey365 via bridge Python → PowerShell        │
│    Progression affichée en temps réel                        │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. MAPPING AUTOMATIQUE                                       │
│    Résultats Monkey365 → Contrôles du référentiel            │
│    Pré-remplissage des statuts + preuves                     │
│    ┌──────────────────────────────────────┐                  │
│    │ M365-AAD-001: ✅ Compliant (auto)    │                  │
│    │ M365-AAD-010: ❌ Non-Compliant (auto)│                  │
│    │ M365-EXO-001: ⚠️  Partial (auto)     │                  │
│    │ M365-COMP-001: ❔ Manual review       │                  │
│    └──────────────────────────────────────┘                  │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. REVUE MANUELLE                                            │
│    L'auditeur valide/ajuste les résultats auto               │
│    Complète les contrôles manuels                            │
│    Ajoute ses observations                                   │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. RAPPORT                                                   │
│    Génération du rapport d'audit M365 complet                │
│    Avec scores, graphiques, plan de remédiation              │
└──────────────────────────────────────────────────────────────┘
```

### Installation de Monkey365

```powershell
# Option 1: Git submodule
git submodule add https://github.com/silverhack/monkey365.git integrations/monkey365

# Option 2: PowerShell Gallery
Install-Module -Name monkey365 -Scope CurrentUser -Force
```

---

## 📖 Exemple de référentiel YAML

### Référentiel infrastructure classique

```yaml
framework:
  name: "Audit Firewall"
  version: "1.0"
  ref_id: "firewall-audit"
  description: "Référentiel d'audit pour les pare-feu"
  categories:
    - name: "Configuration Générale"
      controls:
        - id: FW-001
          title: "Firmware à jour"
          description: "Le firmware est à la dernière version stable"
          severity: high
          check_type: manual
          evidence_required: true
          remediation: "Mettre à jour vers la dernière version stable"

        - id: FW-002
          title: "Accès administration sécurisé"
          description: "L'accès admin est limité à HTTPS/SSH uniquement"
          severity: high
          check_type: automatic
          auto_check: "check_admin_protocols"

    - name: "Règles de filtrage"
      controls:
        - id: FW-010
          title: "Règle deny-all par défaut"
          severity: critical
          check_type: semi-automatic

        - id: FW-011
          title: "Pas de règle any-any"
          severity: critical
          check_type: automatic
          auto_check: "check_any_any_rules"
```

### Référentiel M365 (motorisé par Monkey365)

```yaml
framework:
  name: "Audit Microsoft 365"
  version: "1.0"
  ref_id: "m365-audit"
  engine: "monkey365"
  engine_config:
    provider: "Microsoft365"
    rulesets: ["cis_m365_benchmark"]
    auth_methods: ["client_credentials", "certificate", "interactive"]
  categories:
    - name: "Entra ID - Authentification"
      controls:
        - id: M365-AAD-001
          title: "MFA activé pour tous les utilisateurs"
          severity: critical
          check_type: automatic
          engine_rule_id: "monkey365_aad_mfa_status"
          cis_reference: "CIS M365 1.1.1"
```

---

> **Rappel** : Ce document est mis à jour à chaque session de développement pour garder le fil du projet. Il sert de référence pour comprendre où on en est, quelles décisions ont été prises, et ce qu'il reste à faire.
