# AssistantAudit — Architecture Serveur / Client / Agent

> **Version** : 2.0  
> **Date** : 2026-03-26  
> **Statut** : Spécification d'implémentation  
> **Audience** : Claude Code / développeur implémenteur

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture des composants](#2-architecture-des-composants)
3. [Base de données — PostgreSQL](#3-base-de-données--postgresql)
4. [Sécurité et chiffrement](#4-sécurité-et-chiffrement)
5. [Authentification et autorisation](#5-authentification-et-autorisation)
6. [Agent local — Daemon Windows](#6-agent-local--daemon-windows)
7. [Communication Serveur ↔ Agent](#7-communication-serveur--agent)
8. [Monkey365 et Device Code Flow](#8-monkey365-et-device-code-flow)
9. [WebSocket — Streaming temps réel](#9-websocket--streaming-temps-réel)
10. [Stockage des fichiers preuves](#10-stockage-des-fichiers-preuves)
11. [API REST — Endpoints complets](#11-api-rest--endpoints-complets)
12. [Structure du projet](#12-structure-du-projet)
13. [Migration depuis l'existant](#13-migration-depuis-lexistant)
14. [Configuration et déploiement](#14-configuration-et-déploiement)
15. [Séquences de flux critiques](#15-séquences-de-flux-critiques)
16. [Référentiel ANSSI et Parser ORADAD](#16-référentiel-anssi-et-parser-oradad)

---

## 1. Vue d'ensemble

### 1.1 Contexte

Le projet AssistantAudit est un outil d'audit de sécurité informatique (réseau, Active Directory, Microsoft 365) assisté par IA. Il tourne actuellement en local sur le poste du technicien via `start.ps1`. Cette architecture est migrée vers un modèle Serveur / Client / Agent pour centraliser les données, supporter le multi-techniciens, et séparer les outils selon leur contrainte réseau.

### 1.2 Trois composants

| Composant | Environnement | Rôle |
|-----------|--------------|------|
| **Serveur central** | Ubuntu self-hosted | Backend FastAPI, PostgreSQL, LLM/AI, Monkey365, frontend web, stockage centralisé |
| **Client** | Navigateur du technicien | Frontend React/Vue accessible depuis n'importe où, reçoit les événements temps réel via WebSocket |
| **Agent local** | Poste Windows du technicien | Daemon léger exécutant uniquement les outils nécessitant d'être physiquement dans le réseau cible |

### 1.3 Répartition des outils

| Outil | Tourne sur | Raison |
|-------|-----------|--------|
| Monkey365 | Serveur Ubuntu | Interroge les APIs Microsoft 365 depuis internet |
| ORADAD (ANSSI) | Agent Windows | Requiert Windows + être dans le domaine AD (collecte LDAP) |
| nmap | Agent Windows | Requiert être dans le réseau local cible |
| Collectors AD | Agent Windows | Requiert accès LDAP local |

### 1.4 Principes directeurs

- **Isolation totale inter-techniciens** : un technicien ne peut jamais voir ou agir sur les données d'un autre
- **Chiffrement bout en bout** : données sensibles chiffrées au repos (AES-256-GCM) et en transit (mTLS)
- **Least privilege** : chaque agent ne peut exécuter que les outils qui lui sont autorisés
- **Auditabilité** : chaque action est tracée avec horodatage et auteur

### 1.5 Décisions d'implémentation (validées)

> **Ces décisions priment sur le reste du document en cas de contradiction.**

1. **Sync d'abord, async ensuite** — Le backend reste synchrone (psycopg2-binary) pour préserver les 224 tests existants. La migration vers asyncpg sera une étape séparée ultérieure. Exception : les WebSockets sont async par nature et isolés dans leurs propres fichiers. **Attention : certains exemples de code dans ce document utilisent encore `async/await` et `AsyncSession` — les convertir en sync lors de l'implémentation.** Les sections concernées sont : §5.2, §5.3, §10.2, §11. Le code de l'agent (§6) et du Monkey365 executor (§8) restent async car ce sont des processus séparés.

2. **Noms de colonnes existants préservés** — Les tables existantes gardent leurs noms de colonnes actuels (ex: `nom_projet` et non `title` sur Audit, `password_hash` et non `hashed_password` sur User, `username` conservé). Les nouvelles tables (`agents`, `agent_tasks`, `anssi_checkpoints`) utilisent les noms anglais de la spec.

3. **3 rôles conservés** — `admin`, `auditeur`, `lecteur` (pas de simplification à 2 rôles). Le rôle `auditeur` est l'équivalent du "technician" de la spec — c'est lui qui possède les agents et dispatch les tâches. Le rôle `lecteur` peut consulter mais pas agir.

4. **RBAC par ressource prévu** — Table `ResourcePermission` (user_id, resource_type, resource_id, permission level : owner/write/read) avec héritage entreprise → audit. Non implémenté — chantier dédié après la création de l'agent. Pattern de référence dans `agents.py` et `oradad.py`.

5. **TaskRunner abstraction** — `core/task_runner.py` fournit `SyncTaskRunner` (threads) et `DummyTaskRunner` (tests). Interface prévue pour migration Celery future sans changer les services.

6. **EncryptedJSON type prévu** — Pour les colonnes JSON contenant des données sensibles (`agent_tasks.parameters`, `ad_audit_result.dc_list`). Combinera `EncryptedText` + JSON serialize/deserialize.

7. **Swagger/ReDoc désactivés en production** — `docs_url=None, redoc_url=None, openapi_url=None` quand `ENV` est production/preprod/staging.

8. **Security headers en place** — Middleware dans `main.py` : CSP, HSTS (si HTTPS), X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy. Header `Server` supprimé.

---

## 2. Architecture des composants

### 2.1 Serveur central (Ubuntu)

```
┌─────────────────────────────────────────────────────────┐
│  Serveur Ubuntu                                         │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  FastAPI      │  │  PostgreSQL  │  │  LLM / AI    │  │
│  │  (async)      │──│  (asyncpg)   │  │  Orchestrat° │  │
│  │  api/v1/      │  │  pool=10     │  │              │  │
│  └──────┬───────┘  └──────────────┘  └──────────────┘  │
│         │                                               │
│  ┌──────┴───────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Agent Mgr   │  │  Monkey365   │  │  Stockage    │  │
│  │  mTLS + JWT  │  │  DeviceCode  │  │  UUID+AES256 │  │
│  │  dispatch    │  │  PowerShell  │  │  Envelope enc│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Frontend web (statique, servi par FastAPI)      │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Client (Navigateur)

Le frontend existant, servi comme fichiers statiques par FastAPI. Communique avec le backend via :
- **REST API** : CRUD audits, entreprises, résultats
- **WebSocket** : réception temps réel des logs de scan, device codes, progression, résultats d'agent

### 2.3 Agent local (Windows)

Daemon Python léger packagé en `.exe` via PyInstaller. Communique avec le serveur via HTTPS avec mTLS. Ne contient aucune logique métier — il reçoit des tâches, exécute les outils locaux, et remonte les résultats bruts.

---

## 3. Base de données — PostgreSQL

### 3.1 Configuration de connexion

> **Note : approche sync-first (voir §1.5).** Le code ci-dessous utilise psycopg2 synchrone. La migration vers asyncpg sera une étape ultérieure.

```python
# backend/app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
# PostgreSQL : "postgresql+psycopg2://user:pass@localhost:5432/assistantaudit"
# SQLite (dev/tests) : "sqlite:///./database.db"

# Pool config — appliqué uniquement pour PostgreSQL
engine_kwargs = {}
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs = {
        "pool_size": 10,
        "max_overflow": 5,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
elif DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
    }

engine = create_engine(DATABASE_URL, echo=False, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

### 3.2 Modèles de données

#### 3.2.1 Modèle User (existant, colonnes préservées)

> **Les noms de colonnes existants sont conservés** (voir §1.5). Le code ci-dessous reflète la structure réelle, pas la spec idéale.

```python
# backend/app/models/user.py — ADAPTER au fichier existant, ne pas réécrire

# Colonnes existantes à GARDER telles quelles :
#   username, password_hash, full_name, email, role, is_active, created_at, updated_at
# 
# Rôles existants : "admin", "auditeur", "lecteur"
#   - "auditeur" = équivalent du "technician" de la spec, possède les agents
#   - "lecteur" = consultation seule, pas de dispatch de tâches
#
# Relations à AJOUTER :
#   audits = relationship("Audit", back_populates="owner")
#   agents = relationship("Agent", back_populates="owner")
```

#### 3.2.2 Modèle Agent (NOUVEAU)

```python
# backend/app/models/agent.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)  # nom lisible : "PC-Bureau-Jean", "Laptop-Terrain"

    # Liaison au technicien — 1:N (un tech peut avoir plusieurs agents)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Sécurité mTLS
    cert_fingerprint = Column(String(64), unique=True, nullable=True)  # SHA-256 du cert client
    cert_serial = Column(String(64), nullable=True)  # serial number du certificat pour révocation

    # Enrollment
    enrollment_token_hash = Column(String(128), nullable=True)  # SHA-256 du token d'enrollment
    enrollment_token_expires = Column(DateTime(timezone=True), nullable=True)
    enrollment_used = Column(Boolean, default=False)

    # Statut
    status = Column(String(20), nullable=False, default="pending")
    # Valeurs : "pending" (créé, pas encore enrollé), "active", "revoked", "offline"
    last_seen = Column(DateTime(timezone=True), nullable=True)
    last_ip = Column(String(45), nullable=True)  # IPv4 ou IPv6

    # Outils autorisés
    allowed_tools = Column(JSON, nullable=False, default=lambda: ["nmap", "oradad", "ad_collector"])

    # Métadonnées
    os_info = Column(String(255), nullable=True)  # "Windows 11 Pro 23H2"
    agent_version = Column(String(20), nullable=True)  # "1.0.0"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relations
    owner = relationship("User", back_populates="agents")
    tasks = relationship("AgentTask", back_populates="agent")
```

#### 3.2.3 Modèle AgentTask (NOUVEAU)

```python
# backend/app/models/agent_task.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    # Qui
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=True, index=True)

    # Quoi
    tool = Column(String(50), nullable=False)  # "nmap", "oradad", "ad_collector"
    parameters = Column(JSON, nullable=False)
    # Exemples :
    #   nmap : {"target": "192.168.1.0/24", "scan_type": "comprehensive", "ports": "1-65535"}
    #   oradad : {"domain": "corp.local", "output_files": 0, "confidential": 0}
    #   ad_collector : {"domain": "corp.local", "collect": ["users", "groups", "gpos", "trusts"]}

    # Statut
    status = Column(String(20), nullable=False, default="pending")
    # Valeurs : "pending", "dispatched", "running", "completed", "failed", "cancelled"
    progress = Column(Integer, default=0)  # 0-100
    status_message = Column(String(500), nullable=True)  # dernier message de statut

    # Résultats
    result_summary = Column(JSON, nullable=True)  # résumé structuré du résultat
    result_raw = Column(Text, nullable=True)  # sortie brute (stdout/stderr)
    error_message = Column(Text, nullable=True)

    # Timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relations
    agent = relationship("Agent", back_populates="tasks")
    owner = relationship("User")
    audit = relationship("Audit")
```

#### 3.2.4 Modèle Audit (existant, MODIFIÉ — ajout owner_id)

> **Colonnes existantes préservées** (nom_projet, date_debut, objectifs, etc.). Seul `owner_id` est ajouté.

```python
# backend/app/models/audit.py — ADAPTER au fichier existant

# Colonnes existantes à GARDER : nom_projet, date_debut, objectifs, entreprise_id, etc.
# NE PAS renommer en title/description/status
#
# SEULE modification : ajouter owner_id
#   owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
#   owner = relationship("User", back_populates="audits")
#
# La migration Alembic doit :
#   1. Ajouter la colonne owner_id (nullable=True temporairement)
#   2. Migrer les audits existants vers le premier admin
#   3. Passer owner_id en nullable=False
```

#### 3.2.5 Modèle Attachment (existant, MODIFIÉ — FK sur uploaded_by)

```python
# backend/app/models/attachment.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    file_uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=False, index=True)

    # MODIFICATION : uploaded_by devient une vraie FK (était String libre)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Métadonnées fichier
    original_filename = Column(String(255), nullable=False)  # nom original pour affichage
    file_size = Column(Integer, nullable=False)  # taille en bytes
    mime_type = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, default="evidence")
    # Valeurs : "evidence", "scan_result", "report", "screenshot", "config"

    # Chiffrement envelope
    encrypted_dek = Column(LargeBinary, nullable=False)  # DEK chiffrée avec la KEK
    dek_nonce = Column(LargeBinary, nullable=False)       # nonce utilisé pour chiffrer la DEK
    kek_version = Column(Integer, nullable=False, default=1)  # version de la KEK utilisée

    # Le fichier sur disque est nommé {file_uuid}.enc dans data/blobs/
    # Pas de chemin stocké en base — il se déduit de file_uuid

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relations
    audit = relationship("Audit", back_populates="attachments")
    uploader = relationship("User")
```

#### 3.2.6 Modèle Scan (existant, à adapter)

```python
# backend/app/models/scan.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.core.encryption import EncryptedText  # type custom — voir section 4


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    scan_type = Column(String(50), nullable=False)
    # Valeurs : "monkey365", "nmap", "oradad", "ad_collector"

    source = Column(String(20), nullable=False)
    # Valeurs : "server" (Monkey365), "agent" (nmap, ORADAD, AD)

    auth_method = Column(String(30), nullable=True)
    # Valeurs : "device_code", "certificate", "ntlm", null

    status = Column(String(20), nullable=False, default="pending")
    # Valeurs : "pending", "authenticating", "running", "completed", "failed", "cancelled"

    progress = Column(Integer, default=0)
    status_message = Column(String(500), nullable=True)

    # Résultats — les colonnes sensibles sont chiffrées au niveau applicatif
    results_summary = Column(JSON, nullable=True)              # résumé structuré
    results_raw = Column(EncryptedText, nullable=True)         # CHIFFRÉ : sortie brute complète
    vulnerabilities = Column(EncryptedText, nullable=True)     # CHIFFRÉ : CVE, findings
    credentials_found = Column(EncryptedText, nullable=True)   # CHIFFRÉ : credentials détectés

    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relations
    audit = relationship("Audit", back_populates="scans")
    owner = relationship("User")
```

#### 3.2.7 Modèles NetworkMap et AdAuditResult (existants, colonnes sensibles chiffrées)

```python
# backend/app/models/network_map.py

class NetworkMap(Base):
    __tablename__ = "network_maps"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Données réseau — chiffrées
    hosts = Column(EncryptedText, nullable=True)          # JSON string chiffré : [{ip, mac, hostname, os, ports}]
    topology = Column(EncryptedText, nullable=True)        # JSON string chiffré : graphe réseau
    open_ports_summary = Column(JSON, nullable=True)       # résumé non-sensible pour dashboard

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


# backend/app/models/ad_audit_result.py

class AdAuditResult(Base):
    __tablename__ = "ad_audit_results"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source_tool = Column(String(50), nullable=False)  # "oradad", "ad_collector"

    # Résultats AD — chiffrés
    domain_info = Column(EncryptedText, nullable=True)     # infos domaine
    users_data = Column(EncryptedText, nullable=True)      # utilisateurs AD
    groups_data = Column(EncryptedText, nullable=True)     # groupes et membres
    gpo_data = Column(EncryptedText, nullable=True)        # GPOs
    trust_data = Column(EncryptedText, nullable=True)      # relations de confiance
    vulnerabilities = Column(EncryptedText, nullable=True) # findings (analysés par l'AI côté serveur)

    # Score non-sensible pour dashboard
    health_score = Column(Integer, nullable=True)  # score calculé par l'AI 0-100
    findings_count = Column(JSON, nullable=True)   # {"critical": 2, "high": 5, ...}

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
```

### 3.3 Classification des données par sensibilité

| Tier | Exemples | Colonnes | Traitement |
|------|----------|----------|------------|
| 🔴 Critique | CVE, résultats ORADAD, credentials | `Scan.vulnerabilities`, `Scan.credentials_found`, `AdAuditResult.vulnerabilities` | Chiffré AES-256-GCM (`EncryptedText`) |
| 🟠 Sensible | Résultats scans, hosts réseau, données AD | `Scan.results_raw`, `NetworkMap.hosts`, `AdAuditResult.users_data` | Chiffré AES-256-GCM (`EncryptedText`) |
| 🟡 Interne | Audits, assessments, entreprises | `Audit.*`, `Enterprise.*` | RLS applicatif (filtrage par `owner_id`) |
| 🟢 Technique | Logs, métriques, progression | `AgentTask.progress`, `Scan.status` | Pseudonymisé dans les logs |

### 3.4 Migrations Alembic

```python
# alembic/versions/001_add_owner_id_to_audits.py

"""Add owner_id to audits, FK on attachments.uploaded_by, create agents table"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # 1. Ajouter owner_id sur audits
    op.add_column("audits", sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    # Migrer : affecter tous les audits existants au premier admin
    op.execute("UPDATE audits SET owner_id = (SELECT id FROM users WHERE role = 'admin' LIMIT 1)")
    op.alter_column("audits", "owner_id", nullable=False)
    op.create_index("ix_audits_owner_id", "audits", ["owner_id"])

    # 2. Migrer uploaded_by de String vers Integer FK
    op.add_column("attachments", sa.Column("uploaded_by_new", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.execute("""
        UPDATE attachments SET uploaded_by_new = (
            SELECT id FROM users WHERE email = attachments.uploaded_by OR full_name = attachments.uploaded_by LIMIT 1
        )
    """)
    op.drop_column("attachments", "uploaded_by")
    op.alter_column("attachments", "uploaded_by_new", new_column_name="uploaded_by", nullable=False)

    # 3. Créer la table agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_uuid", sa.String(36), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cert_fingerprint", sa.String(64), unique=True, nullable=True),
        sa.Column("cert_serial", sa.String(64), nullable=True),
        sa.Column("enrollment_token_hash", sa.String(128), nullable=True),
        sa.Column("enrollment_token_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enrollment_used", sa.Boolean(), default=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ip", sa.String(45), nullable=True),
        sa.Column("allowed_tools", sa.JSON(), nullable=False, server_default='["nmap","oradad","ad_collector"]'),
        sa.Column("os_info", sa.String(255), nullable=True),
        sa.Column("agent_version", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agents_user_id", "agents", ["user_id"])

    # 4. Créer la table agent_tasks
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_uuid", sa.String(36), unique=True, nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("audit_id", sa.Integer(), sa.ForeignKey("audits.id"), nullable=True),
        sa.Column("tool", sa.String(50), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("progress", sa.Integer(), default=0),
        sa.Column("status_message", sa.String(500), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("result_raw", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_tasks_agent_id", "agent_tasks", ["agent_id"])
    op.create_index("ix_agent_tasks_owner_id", "agent_tasks", ["owner_id"])

    # 5. Ajouter les colonnes de chiffrement envelope sur attachments
    op.add_column("attachments", sa.Column("file_uuid", sa.String(36), unique=True, nullable=True))
    op.add_column("attachments", sa.Column("encrypted_dek", sa.LargeBinary(), nullable=True))
    op.add_column("attachments", sa.Column("dek_nonce", sa.LargeBinary(), nullable=True))
    op.add_column("attachments", sa.Column("kek_version", sa.Integer(), nullable=True, server_default="1"))


def downgrade():
    op.drop_table("agent_tasks")
    op.drop_table("agents")
    op.drop_column("audits", "owner_id")
    op.drop_column("attachments", "file_uuid")
    op.drop_column("attachments", "encrypted_dek")
    op.drop_column("attachments", "dek_nonce")
    op.drop_column("attachments", "kek_version")
```

---

## 4. Sécurité et chiffrement

### 4.1 Chiffrement AES-256-GCM — Type SQLAlchemy custom

```python
# backend/app/core/encryption.py

import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import TypeDecorator, Text
from app.core.config import settings


class AES256GCMCipher:
    """
    Chiffrement AES-256-GCM pour les colonnes sensibles en base.
    La clé ENCRYPTION_KEY est une variable d'environnement distincte de SECRET_KEY.
    Format stocké : nonce (12 bytes) || ciphertext || tag (16 bytes), encodé en hex.
    """

    def __init__(self):
        key_hex = settings.ENCRYPTION_KEY  # 64 caractères hex = 32 bytes = 256 bits
        if not key_hex or len(key_hex) != 64:
            raise ValueError("ENCRYPTION_KEY must be a 64-character hex string (256 bits)")
        self.key = bytes.fromhex(key_hex)

    def encrypt(self, plaintext: str) -> str:
        """Chiffre une chaîne UTF-8, retourne hex(nonce || ciphertext+tag)."""
        nonce = os.urandom(12)  # 96 bits, recommandé pour GCM
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return (nonce + ciphertext).hex()

    def decrypt(self, data_hex: str) -> str:
        """Déchiffre hex(nonce || ciphertext+tag), retourne la chaîne UTF-8."""
        raw = bytes.fromhex(data_hex)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


class EncryptedText(TypeDecorator):
    """
    Type SQLAlchemy qui chiffre/déchiffre automatiquement les colonnes Text.
    
    Usage :
        results_raw = Column(EncryptedText, nullable=True)
    
    En Python on manipule du texte clair, en base c'est chiffré.
    """
    impl = Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cipher = AES256GCMCipher()

    def process_bind_param(self, value, dialect):
        """Python → DB : chiffre."""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return self._cipher.encrypt(value)

    def process_result_value(self, value, dialect):
        """DB → Python : déchiffre."""
        if value is None:
            return None
        return self._cipher.decrypt(value)
```

### 4.2 Envelope Encryption pour les fichiers

```python
# backend/app/core/file_encryption.py

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


class EnvelopeEncryption:
    """
    Chiffrement enveloppe pour les fichiers preuves sur disque.
    
    Architecture :
    - Chaque fichier est chiffré avec une DEK (Data Encryption Key) unique et aléatoire
    - La DEK est elle-même chiffrée avec la KEK (Key Encryption Key) globale
    - La DEK chiffrée + son nonce sont stockés en base (modèle Attachment)
    - Le fichier chiffré est stocké sur disque sous un nom UUID
    
    Avantage : la rotation de la KEK ne nécessite que de re-chiffrer les DEK (quelques bytes),
    pas les fichiers (potentiellement des centaines de Mo).
    """

    def __init__(self):
        key_hex = settings.FILE_ENCRYPTION_KEY  # KEK — distincte de ENCRYPTION_KEY
        if not key_hex or len(key_hex) != 64:
            raise ValueError("FILE_ENCRYPTION_KEY must be a 64-character hex string (256 bits)")
        self.kek = bytes.fromhex(key_hex)

    def encrypt_file(self, plaintext_data: bytes) -> tuple[bytes, bytes, bytes]:
        """
        Chiffre des données fichier.
        
        Returns:
            (encrypted_file_data, encrypted_dek, dek_nonce)
            - encrypted_file_data : nonce_fichier (12B) || ciphertext+tag → à écrire sur disque
            - encrypted_dek : la DEK chiffrée avec la KEK → à stocker en base
            - dek_nonce : le nonce utilisé pour chiffrer la DEK → à stocker en base
        """
        # 1. Générer une DEK aléatoire
        dek = os.urandom(32)  # 256 bits

        # 2. Chiffrer le fichier avec la DEK
        file_nonce = os.urandom(12)
        aesgcm_file = AESGCM(dek)
        encrypted_file = file_nonce + aesgcm_file.encrypt(file_nonce, plaintext_data, None)

        # 3. Chiffrer la DEK avec la KEK
        dek_nonce = os.urandom(12)
        aesgcm_kek = AESGCM(self.kek)
        encrypted_dek = aesgcm_kek.encrypt(dek_nonce, dek, None)

        return encrypted_file, encrypted_dek, dek_nonce

    def decrypt_file(self, encrypted_file_data: bytes, encrypted_dek: bytes, dek_nonce: bytes) -> bytes:
        """
        Déchiffre des données fichier.
        
        Args:
            encrypted_file_data : contenu lu depuis le disque (nonce || ciphertext+tag)
            encrypted_dek : DEK chiffrée lue depuis la base
            dek_nonce : nonce de la DEK lu depuis la base
        """
        # 1. Déchiffrer la DEK avec la KEK
        aesgcm_kek = AESGCM(self.kek)
        dek = aesgcm_kek.decrypt(dek_nonce, encrypted_dek, None)

        # 2. Déchiffrer le fichier avec la DEK
        file_nonce = encrypted_file_data[:12]
        file_ciphertext = encrypted_file_data[12:]
        aesgcm_file = AESGCM(dek)
        return aesgcm_file.decrypt(file_nonce, file_ciphertext, None)

    def rotate_kek(self, encrypted_dek: bytes, dek_nonce: bytes, old_kek_hex: str) -> tuple[bytes, bytes]:
        """
        Re-chiffre une DEK avec la nouvelle KEK.
        Appelé lors de la rotation de clé — itère sur tous les Attachments.
        
        Returns:
            (new_encrypted_dek, new_dek_nonce)
        """
        # Déchiffrer la DEK avec l'ancienne KEK
        old_kek = bytes.fromhex(old_kek_hex)
        aesgcm_old = AESGCM(old_kek)
        dek = aesgcm_old.decrypt(dek_nonce, encrypted_dek, None)

        # Re-chiffrer avec la nouvelle KEK
        new_nonce = os.urandom(12)
        aesgcm_new = AESGCM(self.kek)
        new_encrypted_dek = aesgcm_new.encrypt(new_nonce, dek, None)

        return new_encrypted_dek, new_nonce
```

### 4.3 Script de rotation de KEK

```python
# backend/scripts/rotate_kek.py

"""
Script de rotation de la KEK (Key Encryption Key).
Usage : python rotate_kek.py --old-key <ancien_hex_64chars>

Ce script :
1. Lit l'ancienne KEK depuis --old-key
2. Utilise la nouvelle KEK depuis FILE_ENCRYPTION_KEY (env var)
3. Itère sur tous les Attachments et re-chiffre chaque DEK
4. Incrémente kek_version
5. Les fichiers sur disque ne sont PAS touchés
"""

import asyncio
import argparse
from app.core.database import async_session
from app.core.file_encryption import EnvelopeEncryption
from app.models.attachment import Attachment
from sqlalchemy import select


async def rotate(old_key_hex: str):
    envelope = EnvelopeEncryption()  # utilise la nouvelle KEK depuis env
    
    async with async_session() as session:
        result = await session.execute(select(Attachment))
        attachments = result.scalars().all()
        
        count = 0
        for att in attachments:
            if att.encrypted_dek is None:
                continue
            new_dek, new_nonce = envelope.rotate_kek(att.encrypted_dek, att.dek_nonce, old_key_hex)
            att.encrypted_dek = new_dek
            att.dek_nonce = new_nonce
            att.kek_version += 1
            count += 1
        
        await session.commit()
        print(f"Rotated {count} DEKs successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-key", required=True, help="Ancienne KEK en hex (64 chars)")
    args = parser.parse_args()
    asyncio.run(rotate(args.old_key))
```

---

## 5. Authentification et autorisation

### 5.1 Deux types de tokens JWT

Le système utilise deux types de JWT distincts avec des claims différents :

```python
# backend/app/core/security.py

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
import secrets
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


# ─── Tokens utilisateur (technicien via frontend) ───

def create_user_token(user_id: int, role: str) -> str:
    """Token JWT pour un utilisateur humain connecté via le frontend."""
    payload = {
        "type": "user",
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_user_token(token: str) -> dict:
    """Vérifie un token utilisateur. Raise JWTError si invalide."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != "user":
        raise JWTError("Invalid token type")
    return payload


# ─── Tokens agent (daemon Windows) ───

def create_agent_token(agent_uuid: str, owner_id: int) -> str:
    """
    Token JWT pour un agent enrollé. Longue durée (30 jours).
    L'owner_id est embarqué — l'agent ne peut agir qu'au nom de son propriétaire.
    """
    payload = {
        "type": "agent",
        "sub": agent_uuid,
        "owner_id": owner_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_agent_token(token: str) -> dict:
    """Vérifie un token agent. Raise JWTError si invalide."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != "agent":
        raise JWTError("Invalid token type")
    return payload


# ─── Enrollment tokens (usage unique, éphémère) ───

def create_enrollment_token() -> tuple[str, str, datetime]:
    """
    Génère un code d'enrollment pour un nouvel agent.
    
    Returns:
        (code_clair, code_hash, expiration)
        - code_clair : 8 caractères alphanumériques, affiché à l'admin dans le dashboard
        - code_hash : SHA-256 du code, stocké en base
        - expiration : datetime UTC, 10 minutes
    """
    code = secrets.token_urlsafe(6)[:8].upper()  # 8 chars alphanumériques
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    expiration = datetime.now(timezone.utc) + timedelta(minutes=10)
    return code, code_hash, expiration


def verify_enrollment_token(code: str, stored_hash: str, expiration: datetime) -> bool:
    """Vérifie un code d'enrollment contre son hash et son expiration."""
    if datetime.now(timezone.utc) > expiration:
        return False
    return hashlib.sha256(code.encode()).hexdigest() == stored_hash


# ─── Dépendances FastAPI (SYNC — voir §1.5) ───

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Dépendance pour les routes utilisateur (tous rôles)."""
    try:
        payload = verify_user_token(credentials.credentials)
        return {"user_id": int(payload["sub"]), "role": payload["role"]}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_agent(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Dépendance pour les routes agent."""
    try:
        payload = verify_agent_token(credentials.credentials)
        return {"agent_uuid": payload["sub"], "owner_id": payload["owner_id"]}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token")


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dépendance : requiert le rôle admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return current_user


def require_auditeur(current_user: dict = Depends(get_current_user)) -> dict:
    """Dépendance : requiert le rôle auditeur ou admin (peut dispatcher des tâches, gérer des agents)."""
    if current_user["role"] not in ("admin", "auditeur"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditeur or admin required")
    return current_user
```

### 5.2 Isolation inter-techniciens — RLS applicatif

Chaque service/route applique un filtrage systématique par `owner_id` :

```python
# backend/app/services/audit_service.py — Exemple de pattern RLS

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import Audit
from fastapi import HTTPException


async def get_audit(db: AsyncSession, audit_id: int, current_user_id: int) -> Audit:
    """
    Récupère un audit avec vérification d'ownership.
    Retourne 404 (pas 403) pour ne pas révéler l'existence d'un audit d'un autre tech.
    """
    result = await db.execute(
        select(Audit).where(Audit.id == audit_id, Audit.owner_id == current_user_id)
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


async def list_audits(db: AsyncSession, current_user_id: int) -> list[Audit]:
    """Liste uniquement les audits du technicien connecté."""
    result = await db.execute(
        select(Audit).where(Audit.owner_id == current_user_id).order_by(Audit.created_at.desc())
    )
    return result.scalars().all()
```

### 5.3 Double vérification au dispatch de tâche

```python
# backend/app/services/task_service.py

async def dispatch_task(
    db: AsyncSession,
    agent_uuid: str,
    audit_id: int,
    tool: str,
    parameters: dict,
    current_user_id: int,
) -> AgentTask:
    """
    Crée et dispatch une tâche vers un agent.
    Double vérification :
    1. L'audit appartient au technicien connecté
    2. L'agent cible appartient au même technicien
    3. L'outil demandé est dans les allowed_tools de l'agent
    """
    # Vérif 1 : l'audit est au bon tech
    audit = await get_audit(db, audit_id, current_user_id)

    # Vérif 2 : l'agent est au bon tech
    result = await db.execute(
        select(Agent).where(Agent.agent_uuid == agent_uuid, Agent.user_id == current_user_id, Agent.status == "active")
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Vérif 3 : l'outil est autorisé
    if tool not in agent.allowed_tools:
        raise HTTPException(status_code=403, detail=f"Tool '{tool}' not allowed for this agent")

    # Création de la tâche
    task = AgentTask(
        agent_id=agent.id,
        owner_id=current_user_id,
        audit_id=audit.id,
        tool=tool,
        parameters=parameters,
        status="pending",
    )
    db.add(task)
    await db.flush()

    # Notification à l'agent via WebSocket (voir section 9)
    await notify_agent(agent.agent_uuid, task)

    return task
```

---

## 6. Agent local — Daemon Windows

### 6.1 Structure du sous-projet

```
agent/
├── main.py                     # Point d'entrée du daemon
├── config.py                   # Configuration (URL serveur, chemins certs)
├── comms/
│   ├── __init__.py
│   ├── client.py               # Client HTTPS + mTLS vers le serveur
│   └── websocket_client.py     # Client WebSocket pour recevoir les tâches en temps réel
├── handlers/
│   ├── __init__.py
│   ├── base_handler.py         # Classe abstraite pour les handlers
│   ├── nmap_handler.py         # Exécution nmap + parsing résultats
│   ├── oradad_handler.py    # Exécution ORADAD + collecte tar
│   └── ad_collector_handler.py # Requêtes LDAP + collecte AD
├── enrollment.py               # Logique d'enrollment au premier lancement
├── cert_store.py               # Gestion du certificat client et de la CA
├── service.py                  # Installation/gestion en tant que service Windows
├── requirements.txt
├── pyinstaller.spec             # Config PyInstaller pour le .exe
└── README.md
```

### 6.2 Point d'entrée du daemon

```python
# agent/main.py

import asyncio
import logging
import sys
from config import AgentConfig
from comms.websocket_client import AgentWebSocketClient
from comms.client import AgentHTTPClient
from enrollment import EnrollmentManager
from handlers.nmap_handler import NmapHandler
from handlers.oradad_handler import OradadHandler
from handlers.ad_collector_handler import AdCollectorHandler

logger = logging.getLogger("agent")

HANDLERS = {
    "nmap": NmapHandler,
    "oradad": OradadHandler,
    "ad_collector": AdCollectorHandler,
}


class AgentDaemon:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.http_client = AgentHTTPClient(config)
        self.ws_client = AgentWebSocketClient(config, self.on_task_received)
        self.running = True

    async def start(self):
        """Démarrage principal du daemon."""
        # 1. Vérifier l'enrollment
        enrollment = EnrollmentManager(self.config)
        if not enrollment.is_enrolled():
            logger.info("Agent not enrolled. Starting enrollment process...")
            await enrollment.enroll_interactive()

        # 2. Vérifier la rotation du token JWT
        if self.config.token_needs_refresh():
            logger.info("JWT token approaching expiration, requesting refresh...")
            await self.http_client.refresh_token()

        # 3. Se connecter au serveur via WebSocket
        logger.info(f"Connecting to server at {self.config.server_url}...")
        await self.ws_client.connect()

        # 4. Envoyer un heartbeat initial
        await self.http_client.heartbeat()

        # 5. Boucle principale
        try:
            await asyncio.gather(
                self.ws_client.listen(),          # Écoute des tâches
                self.heartbeat_loop(),             # Heartbeat toutes les 60s
                self.token_refresh_loop(),         # Vérification rotation JWT
            )
        except asyncio.CancelledError:
            logger.info("Agent shutting down...")
        finally:
            await self.ws_client.disconnect()

    async def heartbeat_loop(self):
        """Envoie un heartbeat au serveur toutes les 60 secondes."""
        while self.running:
            await asyncio.sleep(60)
            try:
                await self.http_client.heartbeat()
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

    async def token_refresh_loop(self):
        """Vérifie si le JWT doit être renouvelé (à J-7 de l'expiration)."""
        while self.running:
            await asyncio.sleep(3600)  # vérif toutes les heures
            if self.config.token_needs_refresh():
                try:
                    await self.http_client.refresh_token()
                    logger.info("JWT token refreshed successfully.")
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")

    async def on_task_received(self, task_data: dict):
        """Callback appelé quand le serveur envoie une tâche via WebSocket."""
        tool = task_data["tool"]
        task_uuid = task_data["task_uuid"]

        logger.info(f"Task received: {task_uuid} / tool={tool}")

        handler_class = HANDLERS.get(tool)
        if not handler_class:
            logger.error(f"Unknown tool: {tool}")
            await self.http_client.report_task_status(task_uuid, "failed", error=f"Unknown tool: {tool}")
            return

        handler = handler_class(self.config, self.http_client)
        try:
            await self.http_client.report_task_status(task_uuid, "running")
            result = await handler.execute(task_data["parameters"], task_uuid)
            await self.http_client.report_task_result(task_uuid, result)
        except Exception as e:
            logger.exception(f"Task {task_uuid} failed")
            await self.http_client.report_task_status(task_uuid, "failed", error=str(e))


if __name__ == "__main__":
    config = AgentConfig.load()
    daemon = AgentDaemon(config)
    asyncio.run(daemon.start())
```

### 6.3 Enrollment interactif

```python
# agent/enrollment.py

import hashlib
import httpx
from config import AgentConfig


class EnrollmentManager:
    def __init__(self, config: AgentConfig):
        self.config = config

    def is_enrolled(self) -> bool:
        """Vérifie si l'agent possède un JWT valide et un certificat client."""
        return (
            self.config.agent_token is not None
            and self.config.client_cert_path.exists()
            and self.config.client_key_path.exists()
        )

    async def enroll_interactive(self):
        """
        Processus d'enrollment interactif au premier lancement.
        
        L'installeur .exe contient uniquement :
        - L'URL du serveur (settings.ini)
        - Le certificat CA (ca.pem) — public, pas sensible
        
        Le technicien doit :
        1. Aller dans le dashboard admin → "Enregistrer un agent"
        2. Copier le code d'enrollment affiché (8 chars, valide 10 min)
        3. Le saisir dans le prompt de l'agent
        """
        print("=" * 60)
        print("  AssistantAudit Agent — Enrollment")
        print("=" * 60)
        print()
        print(f"Serveur : {self.config.server_url}")
        print()

        code = input("Entrez le code d'enrollment : ").strip().upper()

        if not code:
            print("Code vide. Abandon.")
            raise SystemExit(1)

        # Appel au serveur pour l'enrollment
        async with httpx.AsyncClient(verify=str(self.config.ca_cert_path)) as client:
            response = await client.post(
                f"{self.config.server_url}/api/v1/agents/enroll",
                json={"enrollment_code": code},
            )

        if response.status_code != 200:
            print(f"Enrollment échoué : {response.json().get('detail', 'Unknown error')}")
            raise SystemExit(1)

        data = response.json()

        # Sauvegarder le JWT
        self.config.save_token(data["agent_token"])

        # Sauvegarder le certificat client signé par la CA
        self.config.save_client_cert(data["client_cert_pem"], data["client_key_pem"])

        print()
        print(f"Enrollment réussi ! Agent UUID : {data['agent_uuid']}")
        print(f"Certificat client installé.")
        print()
```

### 6.4 Handler nmap (exemple)

```python
# agent/handlers/nmap_handler.py

import asyncio
import xml.etree.ElementTree as ET
from handlers.base_handler import BaseHandler


class NmapHandler(BaseHandler):
    """
    Exécute un scan nmap et parse les résultats XML.
    Nécessite que nmap soit installé sur la machine.
    """

    async def execute(self, parameters: dict, task_uuid: str) -> dict:
        target = parameters["target"]         # ex: "192.168.1.0/24"
        scan_type = parameters.get("scan_type", "comprehensive")
        ports = parameters.get("ports", "1-65535")

        # Construire la commande nmap
        cmd = ["nmap", "-oX", "-"]  # sortie XML sur stdout

        if scan_type == "comprehensive":
            cmd.extend(["-sV", "-sC", "-O", "--osscan-guess"])
        elif scan_type == "quick":
            cmd.extend(["-sV", "-F"])
        elif scan_type == "stealth":
            cmd.extend(["-sS", "-Pn"])

        cmd.extend(["-p", ports, target])

        # Exécuter avec streaming de progression
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"nmap exited with code {process.returncode}: {stderr.decode()}")

        # Parser le XML
        xml_output = stdout.decode("utf-8", errors="replace")
        parsed = self._parse_nmap_xml(xml_output)

        return {
            "summary": parsed,
            "raw_xml": xml_output,
        }

    def _parse_nmap_xml(self, xml_str: str) -> dict:
        """Parse la sortie XML de nmap en structure JSON."""
        root = ET.fromstring(xml_str)
        hosts = []

        for host_elem in root.findall("host"):
            status = host_elem.find("status")
            if status is not None and status.get("state") != "up":
                continue

            host = {
                "ip": None,
                "mac": None,
                "hostname": None,
                "os": None,
                "ports": [],
            }

            # Adresses
            for addr in host_elem.findall("address"):
                if addr.get("addrtype") == "ipv4":
                    host["ip"] = addr.get("addr")
                elif addr.get("addrtype") == "mac":
                    host["mac"] = addr.get("addr")

            # Hostname
            hostnames = host_elem.find("hostnames")
            if hostnames is not None:
                hn = hostnames.find("hostname")
                if hn is not None:
                    host["hostname"] = hn.get("name")

            # OS
            os_elem = host_elem.find("os")
            if os_elem is not None:
                osmatch = os_elem.find("osmatch")
                if osmatch is not None:
                    host["os"] = osmatch.get("name")

            # Ports
            ports_elem = host_elem.find("ports")
            if ports_elem is not None:
                for port in ports_elem.findall("port"):
                    state = port.find("state")
                    service = port.find("service")
                    host["ports"].append({
                        "port": int(port.get("portid")),
                        "protocol": port.get("protocol"),
                        "state": state.get("state") if state is not None else "unknown",
                        "service": service.get("name") if service is not None else None,
                        "version": service.get("version") if service is not None else None,
                    })

            hosts.append(host)

        return {
            "hosts_count": len(hosts),
            "hosts": hosts,
        }
```

### 6.5 Handler ORADAD (ANSSI)

```python
# agent/handlers/oradad_handler.py

import asyncio
import os
import tarfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from handlers.base_handler import BaseHandler


class OradadHandler(BaseHandler):
    """
    Exécute ORADAD (ANSSI) pour collecter les données Active Directory via LDAP.
    
    ORADAD est un outil de COLLECTE, pas d'analyse :
    - Il dump les objets AD (users, groups, GPOs, trusts, etc.) via requêtes LDAP
    - La sortie est une archive .tar contenant des fichiers texte tabulés
    - L'ANALYSE des données est faite côté serveur par l'AI
    - Ne nécessite aucun privilège spécifique — un simple compte du domaine suffit
    - Requiert d'être sur une machine membre du domaine
    
    Fichiers nécessaires à côté de ORADAD.exe :
    - config-oradad.xml (configuration)
    - oradad-schema.xml (schéma des attributs à collecter)
    """

    async def execute(self, parameters: dict, task_uuid: str) -> dict:
        domain = parameters.get("domain")  # ex: "corp.local" (optionnel, auto-détecté sinon)
        output_files = parameters.get("output_files", 0)  # 0=tar only, 1=text files
        confidential = parameters.get("confidential", 0)  # 0=skip confidential attrs, 1=fetch

        oradad_path = self.config.get_tool_path("oradad")
        if not oradad_path or not Path(oradad_path).exists():
            raise FileNotFoundError("ORADAD.exe not found. Check agent configuration.")

        oradad_dir = Path(oradad_path).parent

        # Vérifier que config-oradad.xml existe à côté de l'exécutable
        config_xml = oradad_dir / "config-oradad.xml"
        if not config_xml.exists():
            raise FileNotFoundError("config-oradad.xml not found next to ORADAD.exe")

        # Personnaliser la config si nécessaire
        if output_files != 0 or confidential != 0:
            self._patch_config(config_xml, output_files, confidential)

        # Répertoire de sortie pour cette exécution
        output_dir = Path(self.config.temp_dir) / task_uuid
        output_dir.mkdir(parents=True, exist_ok=True)

        # Commande : ORADAD.exe <outputDirectory>
        cmd = [str(oradad_path), str(output_dir)]

        await self.report_progress(task_uuid, 10, "Lancement de la collecte ORADAD...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(oradad_dir),  # ORADAD lit config-oradad.xml dans son CWD
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if process.returncode != 0:
            raise RuntimeError(f"ORADAD exited with code {process.returncode}: {stderr_text}")

        await self.report_progress(task_uuid, 70, "Collecte terminée, packaging des résultats...")

        # ORADAD génère une archive .tar dans le outputDirectory
        results = {
            "domain": domain or "auto-detected",
            "raw_stdout": stdout_text,
            "files_collected": [],
            "tar_data": None,
        }

        # Chercher l'archive tar générée
        tar_files = list(output_dir.glob("*.tar"))
        if tar_files:
            tar_path = tar_files[0]
            results["tar_size_bytes"] = tar_path.stat().st_size

            # Lire le contenu du tar pour inventaire
            with tarfile.open(tar_path, "r") as tar:
                members = tar.getnames()
                results["files_collected"] = members
                results["files_count"] = len(members)

                # Extraire les fichiers texte pour parsing rapide côté agent
                # (le serveur recevra aussi le tar complet comme attachment)
                summary = self._extract_summary(tar)
                results["summary"] = summary

            # Lire le tar en bytes pour envoi au serveur
            results["tar_data"] = tar_path.read_bytes()

        # Chercher aussi les fichiers texte si output_files=1
        txt_files = list(output_dir.glob("**/*.txt"))
        for txt_file in txt_files[:10]:  # limiter pour le résumé
            try:
                content = txt_file.read_text(encoding="utf-8", errors="replace")
                lines = content.strip().split("\n")
                results.setdefault("text_summaries", []).append({
                    "filename": txt_file.name,
                    "lines_count": len(lines),
                    "preview": "\n".join(lines[:20]),  # 20 premières lignes
                })
            except Exception:
                pass

        await self.report_progress(task_uuid, 90, "Envoi des résultats au serveur...")

        # Nettoyage
        shutil.rmtree(output_dir, ignore_errors=True)

        return results

    def _extract_summary(self, tar: tarfile.TarFile) -> dict:
        """
        Extrait un résumé rapide des données collectées par ORADAD.
        Les fichiers dans le tar sont des dumps LDAP tabulés (TSV).
        """
        summary = {
            "domains_found": [],
            "total_objects": 0,
            "object_types": {},
        }

        for member in tar.getmembers():
            if not member.isfile():
                continue

            name = member.name.lower()

            # Compter les objets par type de fichier
            if "user" in name:
                summary["object_types"]["users"] = summary["object_types"].get("users", 0) + 1
            elif "group" in name:
                summary["object_types"]["groups"] = summary["object_types"].get("groups", 0) + 1
            elif "gpo" in name or "grouppolicy" in name:
                summary["object_types"]["gpos"] = summary["object_types"].get("gpos", 0) + 1
            elif "trust" in name:
                summary["object_types"]["trusts"] = summary["object_types"].get("trusts", 0) + 1

            # Compter les lignes (= objets AD) dans les fichiers texte
            try:
                f = tar.extractfile(member)
                if f:
                    content = f.read().decode("utf-8", errors="replace")
                    lines = content.strip().split("\n")
                    # Première ligne = header, le reste = données
                    object_count = max(0, len(lines) - 1)
                    summary["total_objects"] += object_count
            except Exception:
                pass

        return summary

    def _patch_config(self, config_path: Path, output_files: int, confidential: int):
        """
        Modifie temporairement config-oradad.xml pour ajuster les paramètres.
        Sauvegarde l'original et le restaure après (géré dans execute via cleanup).
        """
        try:
            tree = ET.parse(config_path)
            root = tree.getroot()

            config_elem = root.find(".//config")
            if config_elem is not None:
                of_elem = config_elem.find("outputFiles")
                if of_elem is not None:
                    of_elem.text = str(output_files)
                conf_elem = config_elem.find("confidential")
                if conf_elem is not None:
                    conf_elem.text = str(confidential)

            tree.write(config_path, xml_declaration=True, encoding="utf-8")
        except ET.ParseError:
            pass  # Si le XML est malformé, on continue avec la config par défaut
```

### 6.6 Handler AD Collector

```python
# agent/handlers/ad_collector_handler.py

import asyncio
import json
from handlers.base_handler import BaseHandler

# L'agent utilise ldap3 pour interroger l'AD directement
# pip install ldap3
from ldap3 import Server, Connection, ALL, SUBTREE


class AdCollectorHandler(BaseHandler):
    """
    Collecte des informations Active Directory via LDAP.
    Requiert d'être dans le réseau/domaine AD.
    """

    async def execute(self, parameters: dict, task_uuid: str) -> dict:
        domain = parameters["domain"]          # "corp.local"
        collect = parameters.get("collect", ["users", "groups", "gpos", "trusts"])
        # Auth : utilise le contexte Windows (Kerberos/NTLM automatique)

        # ldap3 est synchrone, on l'exécute dans un thread
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._collect_sync, domain, collect)
        return result

    def _collect_sync(self, domain: str, collect: list) -> dict:
        """Collecte synchrone — exécutée dans un thread."""
        # Construire le base DN depuis le domaine
        base_dn = ",".join(f"DC={part}" for part in domain.split("."))

        server = Server(domain, get_info=ALL)
        # Connexion avec les credentials Windows de la session
        conn = Connection(server, auto_bind=True, authentication="NTLM")

        results = {}

        if "users" in collect:
            conn.search(base_dn, "(objectClass=user)", SUBTREE,
                       attributes=["cn", "sAMAccountName", "mail", "memberOf",
                                   "lastLogonTimestamp", "userAccountControl", "whenCreated"])
            results["users"] = [dict(entry.entry_attributes_as_dict) for entry in conn.entries]

        if "groups" in collect:
            conn.search(base_dn, "(objectClass=group)", SUBTREE,
                       attributes=["cn", "member", "groupType", "description"])
            results["groups"] = [dict(entry.entry_attributes_as_dict) for entry in conn.entries]

        if "gpos" in collect:
            conn.search(base_dn, "(objectClass=groupPolicyContainer)", SUBTREE,
                       attributes=["displayName", "gPCFileSysPath", "flags", "whenCreated"])
            results["gpos"] = [dict(entry.entry_attributes_as_dict) for entry in conn.entries]

        if "trusts" in collect:
            conn.search(base_dn, "(objectClass=trustedDomain)", SUBTREE,
                       attributes=["cn", "trustDirection", "trustType", "trustAttributes"])
            results["trusts"] = [dict(entry.entry_attributes_as_dict) for entry in conn.entries]

        conn.unbind()

        return {
            "domain": domain,
            "base_dn": base_dn,
            "collected": collect,
            "data": results,
            "summary": {
                "users_count": len(results.get("users", [])),
                "groups_count": len(results.get("groups", [])),
                "gpos_count": len(results.get("gpos", [])),
                "trusts_count": len(results.get("trusts", [])),
            },
        }
```

---

## 7. Communication Serveur ↔ Agent

### 7.1 mTLS — Certificats mutuels

L'authentification serveur-agent repose sur mTLS (mutual TLS) avec une CA privée interne.

#### 7.1.1 Génération de la CA et des certificats

```python
# backend/app/core/cert_manager.py

"""
Gestion des certificats pour l'infrastructure mTLS.
CA privée interne — ne PAS utiliser de CA publique pour les agents.
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta, timezone
from pathlib import Path


class CertManager:
    def __init__(self, ca_cert_path: Path, ca_key_path: Path):
        self.ca_cert_path = ca_cert_path
        self.ca_key_path = ca_key_path

    @staticmethod
    def generate_ca(ca_cert_path: Path, ca_key_path: Path, cn: str = "AssistantAudit Internal CA"):
        """Génère la paire CA (une seule fois, à l'installation du serveur)."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AssistantAudit"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))  # 10 ans
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(
                x509.KeyUsage(
                    key_cert_sign=True, crl_sign=True,
                    digital_signature=False, key_encipherment=False,
                    content_commitment=False, data_encipherment=False,
                    key_agreement=False, encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )

        ca_cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        ca_key_path.write_bytes(
            key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        )

    def sign_agent_cert(self, agent_uuid: str) -> tuple[bytes, bytes]:
        """
        Génère et signe un certificat client pour un agent.
        
        Returns:
            (cert_pem, key_pem)
        """
        ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
        ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)

        agent_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"agent-{agent_uuid}"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AssistantAudit"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(agent_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))  # 1 an
            .add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True,
            )
            .add_extension(
                x509.SubjectAlternativeName([x509.UniformResourceIdentifier(f"urn:agent:{agent_uuid}")]),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = agent_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )

        return cert_pem, key_pem

    def get_cert_fingerprint(self, cert_pem: bytes) -> str:
        """Retourne le SHA-256 fingerprint d'un certificat."""
        cert = x509.load_pem_x509_certificate(cert_pem)
        return cert.fingerprint(hashes.SHA256()).hex()

    def get_cert_serial(self, cert_pem: bytes) -> str:
        """Retourne le serial number d'un certificat (pour révocation)."""
        cert = x509.load_pem_x509_certificate(cert_pem)
        return format(cert.serial_number, "x")
```

#### 7.1.2 Configuration mTLS sur FastAPI

```python
# Configuration uvicorn avec mTLS (dans le script de démarrage)
# start_server.py

import uvicorn

uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=8443,
    ssl_keyfile="certs/server.key",
    ssl_certfile="certs/server.pem",
    ssl_ca_certs="certs/ca.pem",          # CA pour vérifier les clients
    ssl_cert_reqs=1,                       # 1 = CERT_OPTIONAL (permet les connexions sans cert pour le frontend)
                                            # Les routes agent vérifient le cert dans le middleware
)
```

### 7.2 Client HTTP côté agent

```python
# agent/comms/client.py

import httpx
import ssl
from pathlib import Path
from config import AgentConfig


class AgentHTTPClient:
    """Client HTTP avec mTLS pour communiquer avec le serveur."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.base_url = config.server_url

        # SSL context avec certificat client
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.ssl_context.load_cert_chain(
            certfile=str(config.client_cert_path),
            keyfile=str(config.client_key_path),
        )
        self.ssl_context.load_verify_locations(str(config.ca_cert_path))

    def _headers(self):
        return {"Authorization": f"Bearer {self.config.agent_token}"}

    async def heartbeat(self):
        """Envoie un heartbeat au serveur."""
        async with httpx.AsyncClient(verify=self.ssl_context) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/agents/heartbeat",
                headers=self._headers(),
                json={
                    "agent_version": self.config.agent_version,
                    "os_info": self.config.os_info,
                },
            )
            response.raise_for_status()

    async def refresh_token(self):
        """Demande un nouveau JWT avant expiration."""
        async with httpx.AsyncClient(verify=self.ssl_context) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/agents/refresh",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            self.config.save_token(data["agent_token"])

    async def report_task_status(self, task_uuid: str, status: str, error: str = None):
        """Rapporte le statut d'une tâche."""
        async with httpx.AsyncClient(verify=self.ssl_context) as client:
            response = await client.patch(
                f"{self.base_url}/api/v1/agents/tasks/{task_uuid}/status",
                headers=self._headers(),
                json={"status": status, "error_message": error},
            )
            response.raise_for_status()

    async def report_task_result(self, task_uuid: str, result: dict):
        """Envoie les résultats d'une tâche terminée."""
        async with httpx.AsyncClient(verify=self.ssl_context) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/agents/tasks/{task_uuid}/result",
                headers=self._headers(),
                json=result,
            )
            response.raise_for_status()
```

---

## 8. Monkey365 et Device Code Flow

### 8.1 Problème résolu

Monkey365 tourne sur le serveur Ubuntu (headless, pas de navigateur). L'authentification MSAL interactive est remplacée par le Device Code Flow : MSAL génère un code, le technicien l'utilise dans son propre navigateur.

### 8.2 Enum AuthMethod

```python
# backend/app/models/enums.py

from enum import Enum


class AuthMethod(str, Enum):
    DEVICE_CODE = "device_code"
    CERTIFICATE = "certificate"
    CLIENT_SECRET = "client_secret"
    # INTERACTIVE est supprimé — pas possible sur Ubuntu headless
```

### 8.3 Executor Monkey365 avec streaming

```python
# backend/app/services/monkey365_executor.py

import asyncio
import re
import json
from datetime import datetime, timezone
from typing import Callable, Optional
from app.models.enums import AuthMethod


class Monkey365Executor:
    """
    Exécute Monkey365 via PowerShell sur le serveur Ubuntu.
    
    Le scan utilise le Device Code Flow :
    1. Monkey365 demande à MSAL un device code
    2. Le code est capturé depuis stdout en temps réel
    3. Streamé via WebSocket au frontend du technicien
    4. Le tech s'authentifie dans son navigateur
    5. MSAL reçoit le token → scan démarre
    6. Logs streamés en temps réel au frontend
    """

    DEVICE_CODE_PATTERN = re.compile(
        r"(https?://microsoft\.com/devicelogin|https?://aka\.ms/devicelogin).*?code[:\s]+([A-Z0-9\-]{6,12})",
        re.IGNORECASE,
    )

    def __init__(self, scan_id: int, ws_callback: Callable):
        """
        Args:
            scan_id: ID du scan en cours
            ws_callback: async callable(event_type, data) pour streamer au frontend
        """
        self.scan_id = scan_id
        self.ws_callback = ws_callback
        self.process: Optional[asyncio.subprocess.Process] = None

    async def run_scan_streaming(
        self,
        tenant_id: str,
        subscriptions: list[str],
        ruleset: str = "cis",
        auth_method: AuthMethod = AuthMethod.DEVICE_CODE,
    ) -> dict:
        """
        Lance un scan Monkey365 avec streaming des logs.
        
        Returns:
            dict avec les résultats du scan
        """
        # Construire le script PowerShell
        ps_script = self._build_ps_script(tenant_id, subscriptions, ruleset, auth_method)

        # Lancer PowerShell en mode async
        self.process = await asyncio.create_subprocess_exec(
            "pwsh", "-NoProfile", "-Command", ps_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Lire stdout ligne par ligne
        output_lines = []
        device_code_sent = False

        async for line_bytes in self.process.stdout:
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            output_lines.append(line)

            # Détecter le device code
            if not device_code_sent:
                match = self.DEVICE_CODE_PATTERN.search(line)
                if match:
                    url = match.group(1)
                    code = match.group(2)
                    await self.ws_callback("device_code", {
                        "scan_id": self.scan_id,
                        "url": url,
                        "code": code,
                        "message": f"Authentifiez-vous sur {url} avec le code : {code}",
                    })
                    device_code_sent = True
                    continue

            # Streamer les logs
            await self.ws_callback("scan_log", {
                "scan_id": self.scan_id,
                "line": line,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # Attendre la fin
        stderr_data = await self.process.stderr.read()
        await self.process.wait()

        if self.process.returncode != 0:
            error = stderr_data.decode("utf-8", errors="replace")
            await self.ws_callback("scan_error", {
                "scan_id": self.scan_id,
                "error": error,
            })
            raise RuntimeError(f"Monkey365 exited with code {self.process.returncode}: {error}")

        # Parser les résultats
        full_output = "\n".join(output_lines)
        results = self._parse_results(full_output)

        await self.ws_callback("scan_complete", {
            "scan_id": self.scan_id,
            "summary": results.get("summary"),
        })

        return results

    def _build_ps_script(self, tenant_id: str, subscriptions: list, ruleset: str, auth_method: AuthMethod) -> str:
        """Construit le script PowerShell Monkey365."""
        subs_str = ",".join(f'"{s}"' for s in subscriptions) if subscriptions else ""

        auth_param = ""
        if auth_method == AuthMethod.DEVICE_CODE:
            auth_param = "-DeviceCode"
        elif auth_method == AuthMethod.CERTIFICATE:
            auth_param = "-Certificate"

        return f"""
Import-Module Monkey365

$params = @{{
    TenantId      = "{tenant_id}"
    Instance      = "Microsoft365"
    Analysis      = "{ruleset}"
    ExportTo      = "JSON"
    {f'Subscriptions = @({subs_str})' if subs_str else ''}
}}

Invoke-Monkey365 @params {auth_param} -Verbose
"""

    def _parse_results(self, output: str) -> dict:
        """Parse la sortie de Monkey365 pour extraire les résultats structurés."""
        # Monkey365 exporte en JSON — chercher le fichier de sortie
        # L'implémentation exacte dépend de la version de Monkey365
        return {
            "raw_output": output,
            "summary": {
                "status": "completed",
            },
        }

    async def cancel(self):
        """Annule le scan en cours."""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()
```

---

## 9. WebSocket — Streaming temps réel

### 9.1 Architecture WebSocket

Deux types de connexions WebSocket :

| Connexion | Authentification | Usage |
|-----------|-----------------|-------|
| `ws://server/ws/user/{user_id}` | JWT utilisateur | Frontend tech reçoit : logs de scan, device codes, progression, résultats agent |
| `ws://server/ws/agent/{agent_uuid}` | JWT agent | Agent reçoit : nouvelles tâches à exécuter, annulations |

### 9.2 Gestionnaire WebSocket avec buffer de reconnexion

```python
# backend/app/core/websocket_manager.py

import asyncio
import json
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional
from fastapi import WebSocket
from jose import JWTError
from app.core.security import verify_user_token, verify_agent_token


class ConnectionManager:
    """
    Gestionnaire centralisé des connexions WebSocket.
    
    Fonctionnalités :
    - Gestion des connexions user et agent
    - Buffer des événements pour reconnexion (max 1000 événements, TTL 30 min)
    - Envoi ciblé par user_id ou agent_uuid
    """

    def __init__(self):
        # Connexions actives
        self.user_connections: dict[int, WebSocket] = {}      # user_id → WebSocket
        self.agent_connections: dict[str, WebSocket] = {}     # agent_uuid → WebSocket

        # Buffer de reconnexion : user_id → list of (timestamp, event)
        self.user_event_buffer: dict[int, list[tuple[datetime, dict]]] = defaultdict(list)
        self.BUFFER_MAX_SIZE = 1000
        self.BUFFER_TTL_SECONDS = 1800  # 30 minutes

    async def connect_user(self, websocket: WebSocket, token: str) -> Optional[int]:
        """Authentifie et connecte un utilisateur."""
        try:
            payload = verify_user_token(token)
            user_id = int(payload["sub"])
        except JWTError:
            await websocket.close(code=4001, reason="Invalid token")
            return None

        await websocket.accept()
        self.user_connections[user_id] = websocket

        # Rejouer les événements bufferisés
        await self._replay_buffered_events(user_id, websocket)

        return user_id

    async def connect_agent(self, websocket: WebSocket, token: str) -> Optional[str]:
        """Authentifie et connecte un agent."""
        try:
            payload = verify_agent_token(token)
            agent_uuid = payload["sub"]
        except JWTError:
            await websocket.close(code=4001, reason="Invalid token")
            return None

        await websocket.accept()
        self.agent_connections[agent_uuid] = websocket
        return agent_uuid

    def disconnect_user(self, user_id: int):
        self.user_connections.pop(user_id, None)

    def disconnect_agent(self, agent_uuid: str):
        self.agent_connections.pop(agent_uuid, None)

    async def send_to_user(self, user_id: int, event_type: str, data: dict):
        """
        Envoie un événement à un utilisateur.
        Si l'utilisateur est déconnecté, bufferise l'événement pour le rejouer à la reconnexion.
        """
        event = {"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}

        ws = self.user_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(event)
                return
            except Exception:
                # Connexion morte, cleanup
                self.disconnect_user(user_id)

        # Bufferiser pour reconnexion
        buffer = self.user_event_buffer[user_id]
        buffer.append((datetime.now(timezone.utc), event))

        # Nettoyer le buffer (taille + TTL)
        self._clean_buffer(user_id)

    async def send_to_agent(self, agent_uuid: str, event_type: str, data: dict):
        """Envoie un événement à un agent."""
        event = {"type": event_type, "data": data}

        ws = self.agent_connections.get(agent_uuid)
        if ws:
            try:
                await ws.send_json(event)
            except Exception:
                self.disconnect_agent(agent_uuid)

    async def _replay_buffered_events(self, user_id: int, websocket: WebSocket):
        """Rejoue les événements bufferisés lors d'une reconnexion."""
        buffer = self.user_event_buffer.pop(user_id, [])
        for _, event in buffer:
            try:
                await websocket.send_json(event)
            except Exception:
                break

    def _clean_buffer(self, user_id: int):
        """Nettoie le buffer : supprime les vieux événements, limite la taille."""
        now = datetime.now(timezone.utc)
        buffer = self.user_event_buffer[user_id]

        # Supprimer les événements expirés
        buffer[:] = [
            (ts, event) for ts, event in buffer
            if (now - ts).total_seconds() < self.BUFFER_TTL_SECONDS
        ]

        # Limiter la taille
        if len(buffer) > self.BUFFER_MAX_SIZE:
            buffer[:] = buffer[-self.BUFFER_MAX_SIZE:]


# Instance globale
ws_manager = ConnectionManager()
```

### 9.3 Routes WebSocket

```python
# backend/app/api/v1/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ws/user")
async def websocket_user(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket pour le frontend d'un technicien.
    Reçoit : scan_log, device_code, scan_complete, scan_error, task_update, agent_status
    """
    user_id = await ws_manager.connect_user(websocket, token)
    if user_id is None:
        return

    try:
        while True:
            # Le frontend peut envoyer des commandes (ex: annuler un scan)
            data = await websocket.receive_json()
            # Traiter les commandes du frontend si nécessaire
            if data.get("type") == "cancel_scan":
                # Propager l'annulation au service de scan
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect_user(user_id)


@router.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket pour un agent local.
    Reçoit : new_task, cancel_task
    Envoie : task_status, task_progress, task_result
    """
    agent_uuid = await ws_manager.connect_agent(websocket, token)
    if agent_uuid is None:
        return

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "task_status":
                # L'agent rapporte un changement de statut
                await ws_manager.send_to_user(
                    data["owner_id"],
                    "task_update",
                    data,
                )
            elif data.get("type") == "task_progress":
                await ws_manager.send_to_user(
                    data["owner_id"],
                    "task_progress",
                    data,
                )
    except WebSocketDisconnect:
        ws_manager.disconnect_agent(agent_uuid)
```

---

## 10. Stockage des fichiers preuves

### 10.1 Structure sur disque

```
data/
└── blobs/
    ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.enc
    ├── b2c3d4e5-f6a7-8901-bcde-f12345678901.enc
    └── ...
```

- **Noms opaques** : UUID comme nom de fichier, pas de nom lisible
- **Contenu chiffré** : chaque fichier est chiffré individuellement avec AES-256-GCM via envelope encryption
- **Accès via API uniquement** : jamais de `StaticFiles` exposant le dossier

### 10.2 Service de gestion des fichiers

```python
# backend/app/services/file_service.py

import os
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.file_encryption import EnvelopeEncryption
from app.core.config import settings
from app.models.attachment import Attachment


BLOBS_DIR = Path(settings.DATA_DIR) / "blobs"


class FileService:
    def __init__(self):
        self.envelope = EnvelopeEncryption()
        BLOBS_DIR.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self,
        db: AsyncSession,
        file: UploadFile,
        audit_id: int,
        user_id: int,
        category: str = "evidence",
    ) -> Attachment:
        """Chiffre et stocke un fichier preuve."""
        # Lire le contenu
        content = await file.read()

        # Chiffrer avec envelope encryption
        encrypted_data, encrypted_dek, dek_nonce = self.envelope.encrypt_file(content)

        # Générer le UUID pour le fichier
        file_uuid = str(uuid4())
        file_path = BLOBS_DIR / f"{file_uuid}.enc"

        # Écrire sur disque
        file_path.write_bytes(encrypted_data)

        # Créer l'entrée en base
        attachment = Attachment(
            file_uuid=file_uuid,
            audit_id=audit_id,
            uploaded_by=user_id,
            original_filename=file.filename,
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            category=category,
            encrypted_dek=encrypted_dek,
            dek_nonce=dek_nonce,
            kek_version=1,
        )
        db.add(attachment)
        return attachment

    async def download_file(
        self,
        db: AsyncSession,
        attachment_id: int,
        user_id: int,
    ) -> tuple[bytes, str, str]:
        """
        Déchiffre et retourne un fichier.
        Vérifie l'ownership via l'audit parent.
        
        Returns:
            (content_bytes, original_filename, mime_type)
        """
        from app.models.audit import Audit
        from sqlalchemy import select

        # Récupérer l'attachment avec vérification d'ownership
        result = await db.execute(
            select(Attachment)
            .join(Audit, Attachment.audit_id == Audit.id)
            .where(Attachment.id == attachment_id, Audit.owner_id == user_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            raise HTTPException(status_code=404, detail="File not found")  # 404, pas 403

        # Lire et déchiffrer
        file_path = BLOBS_DIR / f"{attachment.file_uuid}.enc"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        encrypted_data = file_path.read_bytes()
        content = self.envelope.decrypt_file(encrypted_data, attachment.encrypted_dek, attachment.dek_nonce)

        return content, attachment.original_filename, attachment.mime_type

    async def delete_file(self, db: AsyncSession, attachment_id: int, user_id: int):
        """Supprime un fichier (disque + base) avec vérification d'ownership."""
        from app.models.audit import Audit
        from sqlalchemy import select

        result = await db.execute(
            select(Attachment)
            .join(Audit, Attachment.audit_id == Audit.id)
            .where(Attachment.id == attachment_id, Audit.owner_id == user_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            raise HTTPException(status_code=404, detail="File not found")

        # Supprimer le fichier sur disque
        file_path = BLOBS_DIR / f"{attachment.file_uuid}.enc"
        if file_path.exists():
            file_path.unlink()

        # Supprimer l'entrée en base
        await db.delete(attachment)
```

---

## 11. API REST — Endpoints complets

### 11.1 Routes Agent

```python
# backend/app/api/v1/agents.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import (
    get_current_user, require_admin, get_current_agent,
    create_enrollment_token, verify_enrollment_token, create_agent_token,
)
from app.core.cert_manager import CertManager
from app.core.config import settings
from app.models.agent import Agent
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


# ─── Schemas Pydantic ───

class AgentCreateRequest(BaseModel):
    name: str
    allowed_tools: list[str] = ["nmap", "oradad", "ad_collector"]
    # user_id est implicite : le technicien connecté, sauf si admin crée pour un autre

class AgentCreateResponse(BaseModel):
    agent_uuid: str
    enrollment_code: str  # à afficher dans le dashboard, usage unique
    expires_at: str

class EnrollRequest(BaseModel):
    enrollment_code: str

class EnrollResponse(BaseModel):
    agent_uuid: str
    agent_token: str
    client_cert_pem: str
    client_key_pem: str

class HeartbeatRequest(BaseModel):
    agent_version: str = None
    os_info: str = None

class TaskStatusUpdate(BaseModel):
    status: str
    error_message: str = None
    progress: int = None


# ─── Endpoints Admin ───

@router.post("/create", response_model=AgentCreateResponse)
async def create_agent(
    request: AgentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Crée un nouvel agent et génère un code d'enrollment.
    Le code est affiché dans le dashboard — le tech le saisit au premier lancement de l'agent.
    """
    code, code_hash, expiration = create_enrollment_token()

    agent = Agent(
        name=request.name,
        user_id=current_user["user_id"],
        allowed_tools=request.allowed_tools,
        enrollment_token_hash=code_hash,
        enrollment_token_expires=expiration,
        status="pending",
    )
    db.add(agent)
    await db.flush()

    return AgentCreateResponse(
        agent_uuid=agent.agent_uuid,
        enrollment_code=code,
        expires_at=expiration.isoformat(),
    )


@router.get("/")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Liste les agents du technicien connecté."""
    result = await db.execute(
        select(Agent).where(Agent.user_id == current_user["user_id"]).order_by(Agent.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{agent_uuid}")
async def revoke_agent(
    agent_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Révoque un agent (le rend inutilisable)."""
    result = await db.execute(
        select(Agent).where(Agent.agent_uuid == agent_uuid, Agent.user_id == current_user["user_id"])
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = "revoked"
    # TODO: ajouter le cert serial à la CRL


# ─── Endpoints Agent (appelés par le daemon) ───

@router.post("/enroll", response_model=EnrollResponse)
async def enroll_agent(
    request: EnrollRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint d'enrollment — appelé par l'agent au premier lancement.
    Pas d'auth JWT requise (l'agent n'en a pas encore), juste le code d'enrollment.
    """
    # Chercher un agent pending avec ce code
    result = await db.execute(
        select(Agent).where(
            Agent.enrollment_used == False,
            Agent.status == "pending",
        )
    )
    agents = result.scalars().all()

    enrolled_agent = None
    for agent in agents:
        if verify_enrollment_token(request.enrollment_code, agent.enrollment_token_hash, agent.enrollment_token_expires):
            enrolled_agent = agent
            break

    if not enrolled_agent:
        raise HTTPException(status_code=400, detail="Invalid or expired enrollment code")

    # Générer le certificat client
    cert_manager = CertManager(settings.CA_CERT_PATH, settings.CA_KEY_PATH)
    cert_pem, key_pem = cert_manager.sign_agent_cert(enrolled_agent.agent_uuid)

    # Mettre à jour l'agent
    enrolled_agent.enrollment_used = True
    enrolled_agent.status = "active"
    enrolled_agent.cert_fingerprint = cert_manager.get_cert_fingerprint(cert_pem)
    enrolled_agent.cert_serial = cert_manager.get_cert_serial(cert_pem)
    enrolled_agent.last_seen = datetime.now(timezone.utc)

    # Générer le JWT agent
    agent_token = create_agent_token(enrolled_agent.agent_uuid, enrolled_agent.user_id)

    return EnrollResponse(
        agent_uuid=enrolled_agent.agent_uuid,
        agent_token=agent_token,
        client_cert_pem=cert_pem.decode(),
        client_key_pem=key_pem.decode(),
    )


@router.post("/heartbeat")
async def agent_heartbeat(
    request: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: dict = Depends(get_current_agent),
):
    """Heartbeat de l'agent — met à jour last_seen et les métadonnées."""
    result = await db.execute(
        select(Agent).where(Agent.agent_uuid == current_agent["agent_uuid"])
    )
    agent = result.scalar_one_or_none()
    if not agent or agent.status == "revoked":
        raise HTTPException(status_code=401, detail="Agent revoked or not found")

    agent.last_seen = datetime.now(timezone.utc)
    if request.agent_version:
        agent.agent_version = request.agent_version
    if request.os_info:
        agent.os_info = request.os_info

    return {"status": "ok"}


@router.post("/refresh")
async def refresh_agent_token(
    db: AsyncSession = Depends(get_db),
    current_agent: dict = Depends(get_current_agent),
):
    """Renouvelle le JWT d'un agent (rotation transparente)."""
    result = await db.execute(
        select(Agent).where(Agent.agent_uuid == current_agent["agent_uuid"], Agent.status == "active")
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=401, detail="Agent not found or revoked")

    new_token = create_agent_token(agent.agent_uuid, agent.user_id)
    return {"agent_token": new_token}


@router.patch("/tasks/{task_uuid}/status")
async def update_task_status(
    task_uuid: str,
    update: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_agent: dict = Depends(get_current_agent),
):
    """L'agent rapporte un changement de statut d'une tâche."""
    from app.models.agent_task import AgentTask

    result = await db.execute(
        select(AgentTask)
        .join(Agent, AgentTask.agent_id == Agent.id)
        .where(AgentTask.task_uuid == task_uuid, Agent.agent_uuid == current_agent["agent_uuid"])
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = update.status
    if update.error_message:
        task.error_message = update.error_message
    if update.progress is not None:
        task.progress = update.progress
    if update.status == "running" and not task.started_at:
        task.started_at = datetime.now(timezone.utc)
    if update.status in ("completed", "failed"):
        task.completed_at = datetime.now(timezone.utc)

    # Notifier le frontend du technicien
    await ws_manager.send_to_user(current_agent["owner_id"], "task_update", {
        "task_uuid": task_uuid,
        "status": update.status,
        "progress": update.progress,
        "error": update.error_message,
    })

    return {"status": "ok"}


@router.post("/tasks/{task_uuid}/result")
async def submit_task_result(
    task_uuid: str,
    result_data: dict,
    db: AsyncSession = Depends(get_db),
    current_agent: dict = Depends(get_current_agent),
):
    """L'agent soumet les résultats d'une tâche terminée."""
    from app.models.agent_task import AgentTask

    result = await db.execute(
        select(AgentTask)
        .join(Agent, AgentTask.agent_id == Agent.id)
        .where(AgentTask.task_uuid == task_uuid, Agent.agent_uuid == current_agent["agent_uuid"])
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.result_summary = result_data.get("summary")
    task.result_raw = str(result_data.get("raw_xml") or result_data.get("raw_output", ""))
    task.status = "completed"
    task.progress = 100
    task.completed_at = datetime.now(timezone.utc)

    # Notifier le frontend
    await ws_manager.send_to_user(current_agent["owner_id"], "task_complete", {
        "task_uuid": task_uuid,
        "summary": task.result_summary,
    })

    return {"status": "ok"}
```

### 11.2 Routes Scan (Monkey365)

```python
# backend/app/api/v1/scans.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.scan import Scan
from app.services.monkey365_executor import Monkey365Executor
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


class M365ScanRequest(BaseModel):
    audit_id: int
    tenant_id: str
    subscriptions: list[str] = []
    ruleset: str = "cis"


@router.post("/monkey365")
async def start_monkey365_scan(
    request: M365ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Démarre un scan Monkey365 avec Device Code Flow."""
    # Vérifier l'ownership de l'audit
    from app.services.audit_service import get_audit
    audit = await get_audit(db, request.audit_id, current_user["user_id"])

    # Créer le scan en base
    scan = Scan(
        audit_id=audit.id,
        owner_id=current_user["user_id"],
        scan_type="monkey365",
        source="server",
        auth_method="device_code",
        status="authenticating",
    )
    db.add(scan)
    await db.flush()

    # Callback WebSocket
    async def ws_callback(event_type, data):
        await ws_manager.send_to_user(current_user["user_id"], event_type, data)

    # Lancer le scan en background
    executor = Monkey365Executor(scan.id, ws_callback)

    async def run_scan():
        try:
            results = await executor.run_scan_streaming(
                tenant_id=request.tenant_id,
                subscriptions=request.subscriptions,
                ruleset=request.ruleset,
            )
            async with async_session() as session:
                scan_db = await session.get(Scan, scan.id)
                scan_db.status = "completed"
                scan_db.results_raw = results.get("raw_output")
                scan_db.results_summary = results.get("summary")
                await session.commit()
        except Exception as e:
            async with async_session() as session:
                scan_db = await session.get(Scan, scan.id)
                scan_db.status = "failed"
                scan_db.error_message = str(e)
                await session.commit()

    background_tasks.add_task(run_scan)

    return {"scan_id": scan.id, "status": "authenticating"}
```

### 11.3 Routes Fichiers

```python
# backend/app/api/v1/files.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.file_service import FileService

router = APIRouter(prefix="/api/v1/files", tags=["files"])
file_service = FileService()


@router.post("/upload")
async def upload_file(
    audit_id: int,
    file: UploadFile = File(...),
    category: str = "evidence",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload et chiffre un fichier preuve."""
    attachment = await file_service.upload_file(
        db=db,
        file=file,
        audit_id=audit_id,
        user_id=current_user["user_id"],
        category=category,
    )
    return {
        "id": attachment.id,
        "file_uuid": attachment.file_uuid,
        "original_filename": attachment.original_filename,
        "file_size": attachment.file_size,
    }


@router.get("/download/{attachment_id}")
async def download_file(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Déchiffre et retourne un fichier preuve. Vérifie l'ownership."""
    content, filename, mime_type = await file_service.download_file(
        db=db,
        attachment_id=attachment_id,
        user_id=current_user["user_id"],
    )
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{attachment_id}")
async def delete_file(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Supprime un fichier preuve (disque + base)."""
    await file_service.delete_file(db, attachment_id, current_user["user_id"])
    return {"status": "deleted"}
```

---

## 12. Structure du projet

```
AssistantAudit/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                          # FastAPI app, montage des routers
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                    # Settings (env vars)
│   │   │   ├── database.py                  # Engine asyncpg + session
│   │   │   ├── security.py                  # JWT user + agent, enrollment tokens
│   │   │   ├── encryption.py                # AES-256-GCM, EncryptedText type
│   │   │   ├── file_encryption.py           # Envelope encryption pour fichiers
│   │   │   ├── cert_manager.py              # CA privée, signature certs agent
│   │   │   └── websocket_manager.py         # ConnectionManager avec buffer
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py                  # Login/register/token (existant)
│   │   │       ├── audits.py                # CRUD audits (existant, + owner_id)
│   │   │       ├── agents.py                # NOUVEAU : create, enroll, heartbeat, tasks
│   │   │       ├── scans.py                 # Monkey365 + scans agent (modifié)
│   │   │       ├── files.py                 # NOUVEAU : upload/download chiffré
│   │   │       ├── enterprises.py           # CRUD entreprises (existant)
│   │   │       └── websocket.py             # NOUVEAU : routes WebSocket
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                      # Existant
│   │   │   ├── audit.py                     # Modifié (ajout owner_id)
│   │   │   ├── enterprise.py                # Existant
│   │   │   ├── site.py                      # Existant
│   │   │   ├── scan.py                      # Modifié (colonnes EncryptedText)
│   │   │   ├── network_map.py               # Modifié (colonnes EncryptedText)
│   │   │   ├── ad_audit_result.py           # Modifié (colonnes EncryptedText)
│   │   │   ├── attachment.py                # Modifié (FK uploaded_by, envelope enc)
│   │   │   ├── agent.py                     # NOUVEAU
│   │   │   ├── agent_task.py                # NOUVEAU
│   │   │   └── enums.py                     # NOUVEAU (AuthMethod)
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── audit_service.py             # Logique métier audits (RLS)
│   │       ├── task_service.py              # NOUVEAU : dispatch + double vérification
│   │       ├── file_service.py              # NOUVEAU : upload/download chiffré
│   │       └── monkey365_executor.py        # Modifié (streaming + device code)
│   ├── scripts/
│   │   ├── rotate_kek.py                    # Rotation de la KEK
│   │   ├── init_ca.py                       # Génération initiale de la CA
│   │   └── backup.py                        # pg_dump chiffré GPG
│   ├── alembic/
│   │   ├── alembic.ini
│   │   └── versions/
│   │       └── 001_migration_v2.py
│   ├── certs/                               # Certificats (PAS dans le repo git)
│   │   ├── ca.pem
│   │   ├── ca.key
│   │   ├── server.pem
│   │   └── server.key
│   ├── data/                                # Données (PAS dans le repo git)
│   │   └── blobs/                           # Fichiers preuves chiffrés
│   ├── requirements.txt
│   └── .env.example
│
├── agent/
│   ├── main.py
│   ├── config.py
│   ├── enrollment.py
│   ├── cert_store.py
│   ├── service.py
│   ├── comms/
│   │   ├── __init__.py
│   │   ├── client.py                        # HTTP client mTLS
│   │   └── websocket_client.py              # WS client pour recevoir tâches
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base_handler.py
│   │   ├── nmap_handler.py
│   │   ├── oradad_handler.py
│   │   └── ad_collector_handler.py
│   ├── requirements.txt
│   ├── pyinstaller.spec
│   └── README.md
│
├── frontend/                                # Frontend existant
│   └── ...
│
├── start.ps1                                # Script legacy (à terme supprimé)
├── ARCHITECTURE.md                          # Ce document
└── README.md
```

---

## 13. Migration depuis l'existant

### 13.1 Ordre des opérations

1. **PostgreSQL** : Installer et configurer PostgreSQL sur le serveur Ubuntu
2. **Alembic** : Adapter `alembic.ini` pour pointer vers PostgreSQL
3. **Migration schema** : Exécuter la migration `001_migration_v2.py`
4. **Migration données SQLite → PostgreSQL** :
   ```bash
   # Exporter depuis SQLite
   sqlite3 database.db .dump > dump.sql
   # Adapter le SQL (types, syntaxe) puis importer
   psql -d assistantaudit -f dump_adapted.sql
   ```
5. **Chiffrement des colonnes existantes** : script one-shot qui lit les données en clair et les re-écrit via les colonnes `EncryptedText`
6. **Chiffrement des fichiers existants** : script one-shot qui lit les fichiers dans `data/`, les chiffre avec envelope encryption, les déplace dans `data/blobs/`, et crée les entrées `Attachment` correspondantes
7. **Test de la stack complète** avant de couper l'ancien `start.ps1`

### 13.2 Points de non-régression

- Tous les audits existants doivent rester accessibles
- Les résultats de scan existants doivent être lisibles après chiffrement
- Les fichiers preuves existants doivent être téléchargeables après migration

---

## 14. Configuration et déploiement

### 14.1 Variables d'environnement

```bash
# backend/.env.example

# ─── Base de données ───
DATABASE_URL=postgresql+asyncpg://assistantaudit:CHANGE_ME@localhost:5432/assistantaudit

# ─── Sécurité ───
SECRET_KEY=<64 chars hex>                  # Pour les JWT (utilisateur + agent)
ENCRYPTION_KEY=<64 chars hex>              # Pour le chiffrement des colonnes en base (AES-256-GCM)
FILE_ENCRYPTION_KEY=<64 chars hex>         # KEK pour le chiffrement des fichiers (envelope encryption)

# ─── Certificats mTLS ───
CA_CERT_PATH=certs/ca.pem
CA_KEY_PATH=certs/ca.key
SERVER_CERT_PATH=certs/server.pem
SERVER_KEY_PATH=certs/server.key

# ─── Stockage ───
DATA_DIR=data

# ─── LLM ───
LLM_API_KEY=<clé API du LLM>
LLM_MODEL=<modèle à utiliser>

# ─── Serveur ───
HOST=0.0.0.0
PORT=8443
```

### 14.2 Génération des clés

```bash
# Générer les 3 clés de 256 bits (64 chars hex chacune)
python -c "import secrets; print(secrets.token_hex(32))"  # SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"  # ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_hex(32))"  # FILE_ENCRYPTION_KEY
```

### 14.3 Initialisation de la CA

```bash
# À exécuter une seule fois à l'installation du serveur
python backend/scripts/init_ca.py
```

```python
# backend/scripts/init_ca.py

from pathlib import Path
from app.core.cert_manager import CertManager

CA_CERT = Path("certs/ca.pem")
CA_KEY = Path("certs/ca.key")

if CA_CERT.exists():
    print("CA already exists. Aborting.")
    exit(1)

Path("certs").mkdir(exist_ok=True)
CertManager.generate_ca(CA_CERT, CA_KEY)
print(f"CA generated: {CA_CERT}, {CA_KEY}")
print("IMPORTANT: Back up ca.key securely. If lost, all agent certs become invalid.")
```

### 14.4 Backups

```bash
# Backup base de données + fichiers chiffrés
# Les fichiers dans data/blobs/ sont déjà chiffrés individuellement
# Le dump PostgreSQL est chiffré avec GPG

pg_dump assistantaudit | gpg --symmetric --cipher-algo AES256 -o backup_$(date +%Y%m%d).sql.gpg

# JAMAIS dans les backups automatiques :
# - .env
# - certs/ca.key
# - ENCRYPTION_KEY, FILE_ENCRYPTION_KEY, SECRET_KEY
```

---

## 15. Séquences de flux critiques

### 15.1 Enrollment d'un agent

```
Admin (frontend)                  Serveur                         Agent (1er lancement)
      │                              │                                    │
      │  POST /agents/create         │                                    │
      │  {name: "PC-Jean"}           │                                    │
      │─────────────────────────────>│                                    │
      │                              │  Génère enrollment_code            │
      │                              │  (8 chars, SHA256 → DB, TTL 10m)  │
      │  {code: "A1B2C3D4"}         │                                    │
      │<─────────────────────────────│                                    │
      │                              │                                    │
      │  Affiche le code             │                                    │
      │  au technicien               │                                    │
      │                              │                                    │
      │                              │    POST /agents/enroll             │
      │                              │    {enrollment_code: "A1B2C3D4"}  │
      │                              │<───────────────────────────────────│
      │                              │                                    │
      │                              │  Vérifie code (hash + TTL)         │
      │                              │  Génère cert client (signé CA)    │
      │                              │  Génère JWT agent (30j)           │
      │                              │                                    │
      │                              │  {agent_token, cert_pem, key_pem} │
      │                              │───────────────────────────────────>│
      │                              │                                    │
      │                              │                          Sauvegarde cert + token
      │                              │                          Démarre le daemon
      │                              │                                    │
      │                              │    WebSocket /ws/agent             │
      │                              │<───────────────────────────────────│
      │                              │                                    │
      │                              │    POST /agents/heartbeat          │
      │                              │<───────────────────────────────────│
```

### 15.2 Scan nmap via agent

```
Tech (frontend)            Serveur                    Agent
      │                       │                          │
      │  POST /tasks/dispatch │                          │
      │  {tool: "nmap",       │                          │
      │   target: "10.0.0/24"}│                          │
      │──────────────────────>│                          │
      │                       │  Vérif ownership audit    │
      │                       │  Vérif ownership agent    │
      │                       │  Vérif allowed_tools      │
      │                       │                          │
      │                       │  WS: new_task            │
      │                       │─────────────────────────>│
      │                       │                          │
      │                       │                    Exécute nmap
      │                       │                          │
      │  WS: task_update      │  PATCH /tasks/{id}/status│
      │  {status: "running"}  │<─────────────────────────│
      │<──────────────────────│                          │
      │                       │                          │
      │  WS: task_progress    │  (streaming progression) │
      │  {progress: 45%}      │<─────────────────────────│
      │<──────────────────────│                          │
      │                       │                          │
      │  WS: task_complete    │  POST /tasks/{id}/result │
      │  {summary: {...}}     │<─────────────────────────│
      │<──────────────────────│                          │
      │                       │                          │
      │                       │  Stocke résultats         │
      │                       │  (EncryptedText en base)  │
      │                       │  Passe à l'AI pour analyse│
```

### 15.3 Scan Monkey365 avec Device Code

```
Tech (frontend)            Serveur                    Microsoft
      │                       │                          │
      │  POST /scans/monkey365│                          │
      │  {tenant_id: "..."}   │                          │
      │──────────────────────>│                          │
      │                       │                          │
      │                       │  Lance pwsh + Monkey365   │
      │                       │  (device_code mode)       │
      │                       │                          │
      │                       │  MSAL génère device code  │
      │                       │                          │
      │  WS: device_code      │                          │
      │  {url, code:"ABC-DEF"}│                          │
      │<──────────────────────│                          │
      │                       │                          │
      │  Affiche modale:      │                          │
      │  "Visitez             │                          │
      │   microsoft.com/      │                          │
      │   devicelogin         │                          │
      │   Code: ABC-DEF"      │                          │
      │                       │                          │
      │  Tech s'authentifie ──────────────────────────── │
      │  dans son navigateur  │                    MSAL reçoit token
      │                       │                          │
      │  WS: scan_log         │  Monkey365 scanne        │
      │  {line: "Scanning..."}│                          │
      │<──────────────────────│                          │
      │  ...                  │  ...                     │
      │                       │                          │
      │  WS: scan_complete    │  Résultats terminés      │
      │  {summary: {...}}     │                          │
      │<──────────────────────│                          │
```

---

## Annexe A — Dépendances Python

### Backend (requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
cryptography>=42.0.0
python-multipart>=0.0.6
httpx>=0.27.0
pydantic>=2.0.0
```

### Agent (requirements.txt)

```
httpx>=0.27.0
websockets>=12.0
ldap3>=2.9.1
cryptography>=42.0.0
pyinstaller>=6.0.0
```

---

## Annexe B — Checklist d'implémentation

Ordre recommandé pour l'implémentation :

- [ ] 1. Installer PostgreSQL, configurer la connexion asyncpg
- [ ] 2. Adapter `database.py` (engine, session, pool)
- [ ] 3. Créer `encryption.py` (AES256GCMCipher, EncryptedText)
- [ ] 4. Créer `file_encryption.py` (EnvelopeEncryption)
- [ ] 5. Créer les modèles `Agent`, `AgentTask`
- [ ] 6. Modifier les modèles existants (owner_id, FK, EncryptedText)
- [ ] 7. Écrire et exécuter la migration Alembic
- [ ] 8. Créer `security.py` étendu (tokens agent, enrollment)
- [ ] 9. Créer `cert_manager.py` (CA, signature certs)
- [ ] 10. Créer `websocket_manager.py` (ConnectionManager)
- [ ] 11. Créer les routes API agent (`agents.py`)
- [ ] 12. Créer les routes WebSocket
- [ ] 13. Modifier `monkey365_executor.py` (streaming + device code)
- [ ] 14. Créer `file_service.py` et routes fichiers
- [ ] 15. Créer le sous-projet agent/ (daemon, handlers, comms)
- [ ] 16. Tester l'enrollment complet
- [ ] 17. Tester le dispatch de tâche nmap
- [ ] 18. Tester le scan Monkey365 avec device code
- [ ] 19. Migrer les données existantes
- [ ] 20. Tests de sécurité (isolation inter-techniciens, accès croisés)
- [ ] 21. Implémenter le référentiel ANSSI et le parser ORADAD

---

## 16. Référentiel ANSSI et Parser ORADAD

### 16.1 Contexte

ORADAD (ANSSI) est un **collecteur de données brutes** — il dump les objets AD via LDAP et produit des fichiers tabulés (TSV) dans une archive `.tar`. Contrairement à PingCastle, il ne produit **aucun score ni finding**. L'analyse des données collectées doit être faite côté serveur.

Le référentiel de l'ANSSI ("Points de contrôle Active Directory") définit ~50 points de contrôle, chacun avec un niveau de sécurité (1-5) et un identifiant unique. Ce référentiel constitue la base du moteur d'analyse d'AssistantAudit.

**Flux complet :**
```
Agent Windows                   Serveur
     │                             │
     │  Exécute ORADAD.exe         │
     │  Collecte LDAP → .tar      │
     │                             │
     │  POST /tasks/{id}/result    │
     │  (tar complet en attachment)│
     │────────────────────────────>│
     │                             │
     │                   Parser ORADAD (TSV → JSON structuré)
     │                             │
     │                   Moteur de vérification ANSSI
     │                   (JSON structuré → findings avec vuln_id + niveau)
     │                             │
     │                   LLM / AI analyse les findings
     │                   (contexte, recommandations personnalisées)
     │                             │
     │                   Stocke dans AdAuditResult (chiffré)
```

### 16.2 Format de sortie ORADAD

ORADAD génère une archive `.tar` contenant des fichiers texte tabulés (TSV). La structure type est :

```
<outputDirectory>/
├── <timestamp>_<domain>/
│   ├── Domain/
│   │   ├── user.tsv              # Utilisateurs du domaine
│   │   ├── computer.tsv          # Comptes ordinateurs
│   │   ├── group.tsv             # Groupes
│   │   ├── ou.tsv                # Unités d'organisation
│   │   ├── gpo.tsv               # Objets GPO
│   │   ├── trust.tsv             # Relations d'approbation
│   │   ├── dns.tsv               # Zones DNS
│   │   ├── cert_template.tsv     # Modèles de certificats ADCS
│   │   └── ...                   # Autres classes d'objets
│   ├── Configuration/
│   │   ├── site.tsv
│   │   ├── subnet.tsv
│   │   └── ...
│   ├── Schema/
│   │   └── ...
│   ├── DomainDns/
│   │   └── ...
│   └── Sysvol/
│       ├── GPT.INI
│       ├── Registry.pol
│       ├── GptTmpl.inf
│       └── ...                   # Fichiers SYSVOL collectés selon sysvol_filter
```

**Format des fichiers TSV :**
- Première ligne = en-tête avec les noms d'attributs LDAP
- Lignes suivantes = un objet AD par ligne
- Séparateur = tabulation
- Attributs multi-valués séparés par `|`
- Les attributs collectés sont définis dans `oradad-schema.xml`

**Attributs critiques par type d'objet (ceux utiles pour les points de contrôle ANSSI) :**

| Type | Attributs clés |
|------|---------------|
| user | `sAMAccountName`, `userAccountControl`, `memberOf`, `pwdLastSet`, `lastLogonTimestamp`, `servicePrincipalName`, `msDS-AllowedToDelegateTo`, `primaryGroupID`, `sIDHistory`, `adminCount` |
| computer | `sAMAccountName`, `userAccountControl`, `operatingSystem`, `pwdLastSet`, `lastLogonTimestamp`, `msDS-AllowedToDelegateTo`, `msDS-AllowedToActOnBehalfOfOtherIdentity` |
| group | `sAMAccountName`, `member`, `groupType`, `adminCount`, `objectSid` |
| trust | `trustDirection`, `trustType`, `trustAttributes`, `flatName`, `securityIdentifier` |
| gpo | `displayName`, `gPCFileSysPath`, `flags`, `nTSecurityDescriptor` |
| dns_zone | `dNSProperty` (contient ZONE_ALLOW_UPDATE) |

### 16.3 Modèle du référentiel ANSSI

```python
# backend/app/models/anssi_checklist.py

from sqlalchemy import Column, Integer, String, Text, JSON, Boolean
from app.core.database import Base


class AnssiCheckpoint(Base):
    """
    Référentiel des points de contrôle ANSSI pour l'Active Directory.
    Pré-chargé en base au déploiement via un script de seed.
    Source : https://www.cert.ssi.gouv.fr/uploads/guide-ad.html
    """
    __tablename__ = "anssi_checkpoints"

    id = Column(Integer, primary_key=True, index=True)

    # Identifiant ANSSI unique — ex: "vuln1_permissions_naming_context"
    vuln_id = Column(String(100), unique=True, nullable=False, index=True)

    # Niveau de sécurité ANSSI (1=critique, 2=lacunes, 3=basique, 4=bon, 5=état de l'art)
    level = Column(Integer, nullable=False, index=True)

    # Titre lisible — ex: "Chemins de contrôle dangereux vers la racine des naming contexts"
    title_fr = Column(String(500), nullable=False)
    title_en = Column(String(500), nullable=True)

    # Description de la vulnérabilité
    description = Column(Text, nullable=False)

    # Recommandation ANSSI
    recommendation = Column(Text, nullable=False)

    # Catégorie pour regroupement dans le dashboard
    category = Column(String(100), nullable=False)
    # Valeurs : "permissions", "delegation", "kerberos", "password_policy",
    #           "certificates", "dns", "trusts", "accounts", "replication",
    #           "configuration", "rodc"

    # Attributs LDAP nécessaires pour vérifier ce point de contrôle
    # Permet au parser de savoir quels fichiers TSV / colonnes exploiter
    required_attributes = Column(JSON, nullable=False)
    # Ex: ["userAccountControl", "memberOf", "pwdLastSet", "servicePrincipalName"]

    # Objets AD concernés
    target_object_types = Column(JSON, nullable=False)
    # Ex: ["user", "computer", "group"]

    # Ce point est-il vérifiable automatiquement à partir des données ORADAD ?
    # Certains points nécessitent une analyse des ACL (nTSecurityDescriptor) qui
    # est complexe mais faisable ; d'autres nécessitent un accès réseau direct.
    auto_checkable = Column(Boolean, nullable=False, default=True)

    # Sévérité pour le scoring interne (0-100)
    severity_score = Column(Integer, nullable=False)

    # Référence vers la documentation ANSSI
    reference_url = Column(String(500), nullable=True)
```

### 16.4 Données de seed — Points de contrôle ANSSI

```python
# backend/scripts/seed_anssi_checkpoints.py

"""
Charge le référentiel ANSSI en base de données.
Source : https://www.cert.ssi.gouv.fr/uploads/guide-ad.html
Exécuter une fois au déploiement, puis lors des mises à jour du référentiel.
"""

ANSSI_CHECKPOINTS = [
    # ═══ NIVEAU 1 — Critique ═══

    # Permissions
    {
        "vuln_id": "vuln1_permissions_naming_context",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers la racine des naming contexts",
        "description": "Des chemins de contrôle dangereux existent vers les racines LDAP de l'AD (naming contexts). Un attaquant peut prendre le contrôle complet de l'Active Directory.",
        "recommendation": "Enlever les permissions dangereuses sur les naming contexts. Correction via ADSI Edit ou ldp. Vérifier les permissions Exchange et Azure ADConnect.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor", "distinguishedName"],
        "target_object_types": ["domain_root", "configuration", "schema"],
        "auto_checkable": True,
        "severity_score": 100,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_naming_context",
    },
    {
        "vuln_id": "vuln1_permissions_adminsdholder",
        "level": 1,
        "title_fr": "Permissions dangereuses sur l'objet adminSDHolder",
        "description": "Des permissions dangereuses sur adminSDHolder permettent de prendre le contrôle complet de l'AD. Cassent l'étanchéité du Tier 0.",
        "recommendation": "Revenir aux permissions par défaut sur adminSDHolder via ADSI Edit ou ldp.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["adminsdholder"],
        "auto_checkable": True,
        "severity_score": 100,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_adminsdholder",
    },
    {
        "vuln_id": "vuln1_permissions_dc",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les contrôleurs de domaine",
        "description": "Des chemins de contrôle permettent de prendre le contrôle des DC, répliquant ainsi les secrets de tous les comptes.",
        "recommendation": "Les comptes avec permissions sur les DC doivent être protégés par adminSDHolder. Appartenir aux groupes Administrateurs de l'entreprise ou du domaine.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor", "userAccountControl"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 100,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_dc",
    },
    {
        "vuln_id": "vuln1_permissions_dpapi",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les clés DPAPI",
        "description": "Un attaquant ayant la clé DPAPI du domaine peut déchiffrer tous les secrets protégés par DPAPI.",
        "recommendation": "Ne pas modifier les permissions par défaut des clés DPAPI. Correction via ADSI Edit.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["dpapi_key"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_dpapi",
    },
    {
        "vuln_id": "vuln1_permissions_gmsa_keys",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les clés gMSA",
        "description": "Un attaquant peut récupérer le mot de passe des gMSA en contrôlant leurs clés KDS.",
        "recommendation": "Revenir aux permissions par défaut avec Dsacls <DN> /S /T.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["gmsa"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_gmsa_keys",
    },
    {
        "vuln_id": "vuln1_permissions_dfsr_sysvol",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les paramètres DFSR du SYSVOL",
        "description": "Un attaquant peut modifier le SYSVOL et faire exécuter des GPO malveillantes sur les DC.",
        "recommendation": "Revenir aux permissions par défaut sur les paramètres DFSR.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["dfsr"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_dfsr_sysvol",
    },
    {
        "vuln_id": "vuln1_permissions_schema",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les objets du schéma",
        "description": "Le contrôle du schéma permet de prendre le contrôle complet de l'AD.",
        "recommendation": "Revenir aux permissions par défaut avec Dsacls <DN> /S /T.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["schema"],
        "auto_checkable": True,
        "severity_score": 100,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_schema",
    },
    {
        "vuln_id": "vuln1_permissions_msdns",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les serveurs MicrosoftDNS",
        "description": "Écriture sur CN=MicrosoftDNS,CN=System permet d'exécuter du code arbitraire sur le service DNS (hébergé par un DC).",
        "recommendation": "Retirer la permission d'écriture. Créer une délégation manuelle via ldp.",
        "category": "dns",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["dns_container"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_msdns",
    },
    {
        "vuln_id": "vuln1_permissions_gpo_priv",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les GPO des groupes privilégiés",
        "description": "Un attaquant contrôlant ces GPO peut exécuter du code sur les machines des admins et élever ses privilèges.",
        "recommendation": "Revoir les permissions sur les objets GPO via ADSI Edit ou ldp.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor", "gPCFileSysPath"],
        "target_object_types": ["gpo"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#permissions_gpo_priv",
    },

    # Membres privilégiés
    {
        "vuln_id": "vuln1_privileged_members",
        "level": 1,
        "title_fr": "Nombre important de membres des groupes privilégiés",
        "description": "La forêt contient plus de 50 comptes privilégiés, empêchant un contrôle efficace.",
        "recommendation": "Mettre en place un modèle de délégation. Groupes opératifs : vides. Groupes forêt : peuplés temporairement.",
        "category": "accounts",
        "required_attributes": ["memberOf", "adminCount", "objectSid", "primaryGroupID"],
        "target_object_types": ["user", "group"],
        "auto_checkable": True,
        "severity_score": 80,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#privileged_members",
    },
    {
        "vuln_id": "vuln1_privileged_members_perm",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers des membres de groupes privilégiés",
        "description": "Des droits permettent à des utilisateurs non privilégiés de contrôler des comptes privilégiés.",
        "recommendation": "Enlever les permissions dangereuses. Corriger via ADSI Edit ou ldp.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor", "adminCount", "memberOf"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#privileged_members_perm",
    },

    # Délégation Kerberos
    {
        "vuln_id": "vuln1_delegation_a2d2",
        "level": 1,
        "title_fr": "Délégation contrainte vers un service d'un contrôleur de domaine",
        "description": "Permet au compte d'élever ses privilèges auprès du DC.",
        "recommendation": "Supprimer dans msDS-AllowedToDelegateTo tous les SPN référençant des DC.",
        "category": "delegation",
        "required_attributes": ["msDS-AllowedToDelegateTo", "userAccountControl"],
        "target_object_types": ["user", "computer"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#delegation_a2d2",
    },
    {
        "vuln_id": "vuln1_delegation_t2a4d",
        "level": 1,
        "title_fr": "Délégation contrainte avec transition de protocole vers un DC",
        "description": "Permet de s'authentifier auprès d'un DC avec l'identité d'un autre utilisateur sans pré-auth.",
        "recommendation": "Supprimer dans msDS-AllowedToDelegateTo tous les SPN référençant des DC.",
        "category": "delegation",
        "required_attributes": ["msDS-AllowedToDelegateTo", "userAccountControl"],
        "target_object_types": ["user", "computer"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#delegation_t2a4d",
    },
    {
        "vuln_id": "vuln1_delegation_sourcedeleg",
        "level": 1,
        "title_fr": "Délégation contrainte basée sur les ressources sur des DC",
        "description": "Resource-based constrained delegation configurée sur des DC, accorde une délégation complète.",
        "recommendation": "Supprimer l'attribut msDS-AllowedToActOnBehalfOfOtherIdentity sur les DC.",
        "category": "delegation",
        "required_attributes": ["msDS-AllowedToActOnBehalfOfOtherIdentity"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#delegation_sourcedeleg",
    },

    # Kerberos et mots de passe
    {
        "vuln_id": "vuln1_kerberos_properties_preauth_priv",
        "level": 1,
        "title_fr": "Comptes privilégiés sans pré-authentification Kerberos",
        "description": "Permet d'obtenir un ticket chiffré et de lancer une attaque brute force sur le mot de passe.",
        "recommendation": "Supprimer DONT_REQUIRE_PREAUTH et changer le mot de passe.",
        "category": "kerberos",
        "required_attributes": ["userAccountControl", "adminCount"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#kerberos_properties_preauth_priv",
    },
    {
        "vuln_id": "vuln1_spn_priv",
        "level": 1,
        "title_fr": "Comptes privilégiés avec SPN",
        "description": "Un SPN sur un compte privilégié permet le Kerberoasting — attaque brute force sur le ticket.",
        "recommendation": "Supprimer le SPN des comptes privilégiés et changer leur mot de passe. Ou utiliser des gMSA.",
        "category": "kerberos",
        "required_attributes": ["servicePrincipalName", "adminCount", "memberOf"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#spn_priv",
    },
    {
        "vuln_id": "vuln1_dont_expire_priv",
        "level": 1,
        "title_fr": "Comptes privilégiés dont le mot de passe n'expire jamais",
        "description": "La récupération d'un tel compte permet de conserver les droits sur le long terme.",
        "recommendation": "Supprimer DONT_EXPIRE et renouveler le mot de passe (max tous les 3 ans).",
        "category": "password_policy",
        "required_attributes": ["userAccountControl", "adminCount"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 85,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#dont_expire_priv",
    },
    {
        "vuln_id": "vuln1_password_change_priv",
        "level": 1,
        "title_fr": "Comptes privilégiés dont le mot de passe est inchangé depuis plus de 3 ans",
        "description": "Un mot de passe inchangé depuis 3 ans augmente le risque de compromission à long terme.",
        "recommendation": "Mettre en œuvre une politique de renouvellement < 3 ans pour les comptes privilégiés.",
        "category": "password_policy",
        "required_attributes": ["pwdLastSet", "adminCount"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 85,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#password_change_priv",
    },
    {
        "vuln_id": "vuln1_password_change_dc_no_change",
        "level": 1,
        "title_fr": "DC dont le mot de passe de compte d'ordinateur est inchangé depuis plus de 45 jours",
        "description": "Les DC doivent changer automatiquement leur mot de passe tous les 30 jours. Un défaut indique un dysfonctionnement.",
        "recommendation": "Vérifier les registres DisablePasswordChange et MaximumPasswordAge. S'assurer qu'aucune GPO ne les modifie.",
        "category": "password_policy",
        "required_attributes": ["pwdLastSet", "userAccountControl"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 85,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#password_change_dc_no_change",
    },
    {
        "vuln_id": "vuln1_password_change_inactive_dc",
        "level": 1,
        "title_fr": "Contrôleurs de domaine inactifs",
        "description": "Des DC ne se sont pas authentifiés depuis plus de 45 jours, signe de désynchronisation.",
        "recommendation": "Réinstaller ou supprimer les DC désynchronisés. Utiliser Djoin pour la jonction hors connexion.",
        "category": "configuration",
        "required_attributes": ["lastLogonTimestamp", "userAccountControl"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 80,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#password_change_inactive_dc",
    },
    {
        "vuln_id": "vuln1_dc_inconsistent_uac",
        "level": 1,
        "title_fr": "Contrôleurs de domaine incohérents",
        "description": "Attributs dans un état incohérent, symptomatique d'erreur de config ou de malveillance.",
        "recommendation": "Vérifier userAccountControl (SERVER_TRUST_ACCOUNT|TRUSTED_FOR_DELEGATION = 0x82000).",
        "category": "configuration",
        "required_attributes": ["userAccountControl", "serverReferenceBL"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 85,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#dc_inconsistent_uac",
    },

    # Certificats et ADCS
    {
        "vuln_id": "vuln1_adcs_control",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les conteneurs de certificats",
        "description": "Permet d'ajouter une CA malveillante et d'usurper des utilisateurs.",
        "recommendation": "Revenir aux permissions par défaut sur les conteneurs de certificats.",
        "category": "certificates",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["pki_container"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#adcs_control",
    },
    {
        "vuln_id": "vuln1_adcs_template_control",
        "level": 1,
        "title_fr": "Chemins de contrôle dangereux vers les modèles de certificats",
        "description": "Permet de faire générer un certificat arbitraire par la CA pour usurper n'importe quel utilisateur.",
        "recommendation": "Revenir aux permissions par défaut sur les templates via adsiedit.msc ou pkiview.msc.",
        "category": "certificates",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["cert_template"],
        "auto_checkable": True,
        "severity_score": 95,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#adcs_template_control",
    },
    {
        "vuln_id": "vuln1_certificates_vuln",
        "level": 1,
        "title_fr": "Certificats faibles ou vulnérables (critique)",
        "description": "Utilisation de DSA, clé RSA < 1024 bits, ou clé vulnérable à ROCA.",
        "recommendation": "Révoquer et regénérer avec RSA ≥ 2048 bits et algorithme SHA-2/SHA-3.",
        "category": "certificates",
        "required_attributes": ["cACertificate", "userCertificate"],
        "target_object_types": ["pki_container", "user", "computer"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#certificates_vuln",
    },

    # DNS, dSHeuristics, trusts
    {
        "vuln_id": "vuln1_dnsadmins",
        "level": 1,
        "title_fr": "Comptes membres du groupe DnsAdmins",
        "description": "Les membres de DnsAdmins peuvent exécuter du code arbitraire sur le service DNS hébergé par un DC.",
        "recommendation": "Vider le groupe DnsAdmins. Créer une délégation manuelle via ldp.",
        "category": "dns",
        "required_attributes": ["memberOf", "objectSid"],
        "target_object_types": ["user", "group"],
        "auto_checkable": True,
        "severity_score": 85,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#dnsadmins",
    },
    {
        "vuln_id": "vuln1_dnszone_bad_prop",
        "level": 1,
        "title_fr": "Zones DNS mal configurées (critique)",
        "description": "ZONE_UPDATE_UNSECURE permet la mise à jour DNS sans authentification.",
        "recommendation": "Reconfigurer pour mises à jour sécurisées uniquement : dnscmd /Config <zone> /AllowUpdate 2.",
        "category": "dns",
        "required_attributes": ["dNSProperty"],
        "target_object_types": ["dns_zone"],
        "auto_checkable": True,
        "severity_score": 80,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#dnszone_bad_prop",
    },
    {
        "vuln_id": "vuln1_dsheuristics_bad",
        "level": 1,
        "title_fr": "Paramètres dSHeuristics dangereux (critique)",
        "description": "fAllowAnonNSPI ≠ 0 ou dwAdminSDExMask ≠ 0 affaiblit la sécurité de l'AD.",
        "recommendation": "Remettre fAllowAnonNSPI et dwAdminSDExMask à 0 via ADSI Edit.",
        "category": "configuration",
        "required_attributes": ["dSHeuristics"],
        "target_object_types": ["directory_service"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#dsheuristics_bad",
    },
    {
        "vuln_id": "vuln1_trusts_domain_notfiltered",
        "level": 1,
        "title_fr": "Relations d'approbation sortante non filtrées",
        "description": "Un attaquant ayant compromis le domaine externe peut usurper n'importe quel utilisateur du domaine.",
        "recommendation": "Activer la quarantaine : netdom trust <domaine> /domain:<externe> /Quarantine:yes.",
        "category": "trusts",
        "required_attributes": ["trustDirection", "trustType", "trustAttributes"],
        "target_object_types": ["trust"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#trusts_domain_notfiltered",
    },
    {
        "vuln_id": "vuln1_trusts_forest_sidhistory",
        "level": 1,
        "title_fr": "Relations d'approbation forêt avec sID History activé",
        "description": "Filtrage affaibli permettant l'usurpation d'identité depuis la forêt externe.",
        "recommendation": "Réactiver le filtrage : netdom trust <forêt> /domain:<externe> /EnableSIDHistory:no.",
        "category": "trusts",
        "required_attributes": ["trustDirection", "trustType", "trustAttributes"],
        "target_object_types": ["trust"],
        "auto_checkable": True,
        "severity_score": 90,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#trusts_forest_sidhistory",
    },
    {
        "vuln_id": "vuln1_user_accounts_dormant",
        "level": 1,
        "title_fr": "Nombre important de comptes actifs inutilisés",
        "description": "Plus de 25% de comptes dormants (non authentifiés depuis > 1 an). Risque de comptes obsolètes exploitables.",
        "recommendation": "Neutraliser les comptes obsolètes : désactiver, retirer des groupes, randomiser le mot de passe.",
        "category": "accounts",
        "required_attributes": ["lastLogonTimestamp", "pwdLastSet", "userAccountControl"],
        "target_object_types": ["user", "computer"],
        "auto_checkable": True,
        "severity_score": 70,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#user_accounts_dormant",
    },
    {
        "vuln_id": "vuln1_primary_group_id_1000",
        "level": 1,
        "title_fr": "Comptes avec un PrimaryGroupID inférieur à 1000",
        "description": "Les PrimaryGroupID < 1000 sont souvent privilégiés. Permet de dissimuler l'appartenance à un groupe admin.",
        "recommendation": "Repositionner les primaryGroupId aux valeurs par défaut (513, 515, 516, 521).",
        "category": "accounts",
        "required_attributes": ["primaryGroupID"],
        "target_object_types": ["user", "computer"],
        "auto_checkable": True,
        "severity_score": 80,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#primary_group_id_1000",
    },

    # ═══ NIVEAU 2 — Lacunes ═══

    {
        "vuln_id": "vuln2_privileged_members_password",
        "level": 2,
        "title_fr": "Comptes privilégiés avec une mauvaise politique de mot de passe",
        "description": "Politique de mot de passe faible imposée aux comptes privilégiés.",
        "recommendation": "Renouvellement max 3 ans, longueur min 8 caractères. Ne pas forcer un renouvellement trop fréquent.",
        "category": "password_policy",
        "required_attributes": ["pwdLastSet", "adminCount", "msDS-ResultantPSO"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 70,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#privileged_members_password",
    },
    {
        "vuln_id": "vuln2_delegation_t4d",
        "level": 2,
        "title_fr": "Délégation d'authentification non contrainte",
        "description": "Permet d'usurper l'identité de tout utilisateur s'authentifiant auprès de ces comptes.",
        "recommendation": "Supprimer TRUSTED_FOR_DELEGATION. Utiliser la délégation contrainte si nécessaire.",
        "category": "delegation",
        "required_attributes": ["userAccountControl"],
        "target_object_types": ["user", "computer"],
        "auto_checkable": True,
        "severity_score": 75,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#delegation_t4d",
    },
    {
        "vuln_id": "vuln2_kerberos_properties_preauth",
        "level": 2,
        "title_fr": "Comptes sans pré-authentification Kerberos",
        "description": "Permet le AS-REP Roasting sur des comptes non privilégiés.",
        "recommendation": "Supprimer DONT_REQUIRE_PREAUTH et changer le mot de passe.",
        "category": "kerberos",
        "required_attributes": ["userAccountControl"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 65,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#kerberos_properties_preauth",
    },
    {
        "vuln_id": "vuln2_kerberos_properties_deskey",
        "level": 2,
        "title_fr": "Comptes utilisateurs avec chiffrement Kerberos DES",
        "description": "USE_DES_KEY_ONLY autorise un chiffrement obsolète, facilitant le brute force.",
        "recommendation": "Retirer USE_DES_KEY_ONLY de l'attribut userAccountControl.",
        "category": "kerberos",
        "required_attributes": ["userAccountControl"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 65,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#kerberos_properties_deskey",
    },
    {
        "vuln_id": "vuln2_dont_expire",
        "level": 2,
        "title_fr": "Comptes dont le mot de passe n'expire jamais",
        "description": "La récupération d'un tel compte permet de conserver les droits sur le long terme.",
        "recommendation": "Supprimer DONT_EXPIRE. Documenter les comptes de service et leurs procédures de rotation.",
        "category": "password_policy",
        "required_attributes": ["userAccountControl"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 60,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#dont_expire",
    },
    {
        "vuln_id": "vuln2_password_change_server_no_change_90",
        "level": 2,
        "title_fr": "Serveurs dont le mot de passe est inchangé depuis plus de 90 jours",
        "description": "Les serveurs doivent changer automatiquement leur mot de passe tous les 30 jours.",
        "recommendation": "Vérifier les registres DisablePasswordChange et MaximumPasswordAge.",
        "category": "password_policy",
        "required_attributes": ["pwdLastSet", "userAccountControl", "operatingSystem"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 60,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#password_change_server_no_change_90",
    },
    {
        "vuln_id": "vuln2_sysvol_ntfrs",
        "level": 2,
        "title_fr": "Utilisation de NTFRS pour la réplication du SYSVOL",
        "description": "NTFRS est obsolète et n'est plus supporté par les dernières versions de Windows Server.",
        "recommendation": "Migrer vers DFSR. Voir documentation Microsoft sur la migration NTFRS → DFSR.",
        "category": "replication",
        "required_attributes": ["fRSMemberReferenceBL"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 55,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#sysvol_ntfrs",
    },
    {
        "vuln_id": "vuln2_adupdate_bad",
        "level": 2,
        "title_fr": "Mauvaises versions de l'Active Directory",
        "description": "Schéma en révision 15 créant des ACE trop permissives pour Key Admins et Enterprise Key Admins.",
        "recommendation": "Mettre à jour le schéma avec adprep /ForestPrep puis adprep /DomainPrep.",
        "category": "configuration",
        "required_attributes": ["objectVersion"],
        "target_object_types": ["schema"],
        "auto_checkable": True,
        "severity_score": 60,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#adupdate_bad",
    },
    {
        "vuln_id": "vuln2_compatible_2000_anonymous",
        "level": 2,
        "title_fr": "Pre-Windows 2000 Compatible Access contient Anonymous",
        "description": "Permet une énumération anonyme d'éléments sur les DC.",
        "recommendation": "Le groupe ne doit contenir que Utilisateurs authentifiés (S-1-5-11).",
        "category": "configuration",
        "required_attributes": ["member", "objectSid"],
        "target_object_types": ["group"],
        "auto_checkable": True,
        "severity_score": 60,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#compatible_2000_anonymous",
    },
    {
        "vuln_id": "vuln2_krbtgt",
        "level": 2,
        "title_fr": "Mot de passe du compte krbtgt inchangé depuis plus d'un an",
        "description": "Compromission du krbtgt permet de forger des golden tickets et s'authentifier partout.",
        "recommendation": "Changer le mot de passe krbtgt annuellement (2 fois, avec délai entre les deux).",
        "category": "password_policy",
        "required_attributes": ["pwdLastSet", "sAMAccountName"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 75,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#krbtgt",
    },
    {
        "vuln_id": "vuln2_rodc_priv_revealed",
        "level": 2,
        "title_fr": "Comptes privilégiés dans les attributs de révélation des RODC",
        "description": "Des comptes privilégiés ont leurs secrets révélés (cachés) sur des RODC.",
        "recommendation": "Retirer les comptes privilégiés des listes de révélation RODC.",
        "category": "rodc",
        "required_attributes": ["msDS-RevealedUsers", "msDS-NeverRevealGroup", "msDS-RevealOnDemandGroup"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 70,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#rodc_priv_revealed",
    },
    {
        "vuln_id": "vuln2_sidhistory_dangerous",
        "level": 2,
        "title_fr": "Comptes avec historique de SID d'apparence non conforme",
        "description": "sIDHistory contenant des SID de groupes privilégiés permet une élévation de privilèges furtive.",
        "recommendation": "Supprimer les sIDHistory non conformes des comptes concernés.",
        "category": "accounts",
        "required_attributes": ["sIDHistory", "objectSid"],
        "target_object_types": ["user", "group"],
        "auto_checkable": True,
        "severity_score": 70,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#sidhistory_dangerous",
    },
    {
        "vuln_id": "vuln2_trusts_accounts",
        "level": 2,
        "title_fr": "Comptes de trust dont le mot de passe est inchangé depuis plus d'un an",
        "description": "Les comptes de trust doivent être renouvelés régulièrement.",
        "recommendation": "Renouveler les mots de passe des comptes de trust.",
        "category": "trusts",
        "required_attributes": ["pwdLastSet", "trustDirection"],
        "target_object_types": ["trust"],
        "auto_checkable": True,
        "severity_score": 60,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#trusts_accounts",
    },

    # ═══ NIVEAU 3 — Basique ═══

    {
        "vuln_id": "vuln3_password_change_server_no_change_45",
        "level": 3,
        "title_fr": "Serveurs dont le mot de passe est inchangé depuis plus de 45 jours",
        "description": "Les serveurs doivent changer automatiquement leur mot de passe (30 jours par défaut).",
        "recommendation": "Vérifier les registres DisablePasswordChange et MaximumPasswordAge.",
        "category": "password_policy",
        "required_attributes": ["pwdLastSet", "userAccountControl", "operatingSystem"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 45,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#password_change_server_no_change_45",
    },
    {
        "vuln_id": "vuln3_password_change_inactive_servers",
        "level": 3,
        "title_fr": "Serveurs inactifs",
        "description": "Des serveurs ne se sont pas authentifiés depuis plus de 45 jours.",
        "recommendation": "Réinstaller ou supprimer les serveurs désynchronisés.",
        "category": "configuration",
        "required_attributes": ["lastLogonTimestamp", "userAccountControl", "operatingSystem"],
        "target_object_types": ["computer"],
        "auto_checkable": True,
        "severity_score": 40,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#password_change_inactive_servers",
    },
    {
        "vuln_id": "vuln3_protected_users",
        "level": 3,
        "title_fr": "Comptes privilégiés non membres du groupe Protected Users",
        "description": "Le groupe Protected Users applique des protections supplémentaires (pas de NTLM, pas de délégation).",
        "recommendation": "Ajouter les comptes privilégiés au groupe Protected Users.",
        "category": "accounts",
        "required_attributes": ["memberOf", "adminCount"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 45,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#protected_users",
    },
    {
        "vuln_id": "vuln3_reversible_password",
        "level": 3,
        "title_fr": "Comptes ayant leur mot de passe stocké de manière réversible",
        "description": "Permet la récupération du mot de passe en clair depuis la base AD.",
        "recommendation": "Supprimer le flag ENCRYPTED_TEXT_PASSWORD_ALLOWED et changer le mot de passe.",
        "category": "password_policy",
        "required_attributes": ["userAccountControl"],
        "target_object_types": ["user"],
        "auto_checkable": True,
        "severity_score": 50,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#reversible_password",
    },
    {
        "vuln_id": "vuln3_owner",
        "level": 3,
        "title_fr": "Objets ayant un propriétaire inadapté",
        "description": "Des propriétaires non privilégiés sur des objets sensibles permettent de modifier les ACL.",
        "recommendation": "Corriger les propriétaires des objets sensibles.",
        "category": "permissions",
        "required_attributes": ["nTSecurityDescriptor"],
        "target_object_types": ["user", "computer", "group", "gpo"],
        "auto_checkable": True,
        "severity_score": 45,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#owner",
    },
    {
        "vuln_id": "vuln3_sidhistory_present",
        "level": 3,
        "title_fr": "Comptes ou groupes ayant un historique de SID",
        "description": "sIDHistory doit être nettoyé après les migrations.",
        "recommendation": "Supprimer les sIDHistory des comptes/groupes concernés.",
        "category": "accounts",
        "required_attributes": ["sIDHistory"],
        "target_object_types": ["user", "group"],
        "auto_checkable": True,
        "severity_score": 35,
        "reference_url": "https://www.cert.ssi.gouv.fr/uploads/guide-ad.html#sidhistory_present",
    },
]
```

### 16.5 Checklist d'implémentation supplémentaire

- [ ] 21. Script de seed du référentiel ANSSI (`seed_anssi_checkpoints.py`)
- [ ] 22. Parser ORADAD : TSV → JSON structuré (`backend/app/services/oradad_parser.py`)
- [ ] 23. Moteur de vérification automatique (`backend/app/services/anssi_checker.py`) — itère sur les checkpoints `auto_checkable=True`, vérifie chacun contre les données parsées
- [ ] 24. Intégration LLM : pour les findings détectés, l'AI génère des recommandations contextualisées et un score global
- [ ] 25. Endpoint API : `GET /api/v1/audits/{id}/anssi-report` retourne le rapport structuré avec tous les findings par niveau
- [ ] 26. Dashboard frontend : affichage du niveau ANSSI (1-5) avec la liste des findings par catégorie
