# Architecture technique — AssistantAudit

## Vue d'ensemble

Plateforme d'audit de sécurité informatique organisée en 5 couches :

```
Frontend (Next.js 16)
    └── API REST (FastAPI)
          └── Services (logique métier)
                └── Models (SQLAlchemy 2)
                      └── Base de données (PostgreSQL / SQLite)
```

---

## Pattern architectural

```
Router (api/v1/)
  └── Service (services/)
        └── Model (models/) via Session SQLAlchemy
              └── Schema (schemas/) — sérialisation requête/réponse
```

- Les routes n'accèdent jamais directement à la base de données
- Tous les services sont synchrones — seuls les handlers WebSocket utilisent `async def`
- Logique métier isolée dans des méthodes statiques avec `Session` injectée

---

## Backend

### API — 19 routeurs, 100+ endpoints

| Domaine | Exemples |
|---------|---------|
| Audit | assessments, findings, checklists, reports |
| Infrastructure | equipment, network, vulnerabilities |
| Collecte | collect, scan, agent, monkey365 |
| Référentiels | frameworks, controls |
| Système | auth, users, health, metrics |

### Services — 24 modules

`assessment`, `framework`, `collect`, `scan`, `monkey365`, `agent`, `report`, `finding`, `checklist`, `equipment`, `network`, `vulnerability`, `user`, `auth`, `audit_log`, et al.

### Modèles — 23 modèles core + 14 sous-types équipement

Héritage polymorphique pour les équipements (serveur, switch, routeur, pare-feu, etc.).

### Outils — 6 catégories

| Catégorie | Rôle |
|-----------|------|
| `nmap` | Scan réseau et découverte de ports |
| `ssh_collector` | Collecte de configuration via SSH |
| `winrm_collector` | Collecte de configuration Windows |
| `ad_auditor` | Audit Active Directory |
| `monkey365` | Analyse cloud (Azure/M365) |
| `config_parsers` | Analyse de fichiers de configuration |

### Modules transversaux — 20 modules

`security`, `encryption`, `rate_limit`, `metrics`, `logging`, `health_check`, `middleware`, `websocket`, `scheduler`, `config`, et al.

---

## Frontend

- **Framework** : Next.js 16 App Router — 23+ pages
- **Données** : SWR pour le cache et la revalidation, Axios avec intercepteur JWT
- **UI** : shadcn/ui (composants), Recharts (graphiques), XYFlow (topologie réseau)
- **Auth** : `AuthContext` + `AuthGuard` — gestion des tokens access/refresh
- **Thème** : `ThemeProvider` — support mode clair/sombre

---

## Sécurité

| Mécanisme | Détail |
|-----------|--------|
| Chiffrement colonne | AES-256-GCM via `EncryptedText` et `EncryptedJSON` (TypeDecorators SQLAlchemy) |
| Authentification | JWT — access 15 min, refresh 7 j, agent 30 j |
| Mots de passe | Hachage bcrypt |
| Agents | Enrôlement mTLS |
| Transport | En-têtes de sécurité HTTP (middleware), rate limiting par IP |

---

## Communication temps réel

WebSocket dédié à la communication avec les agents :
- Dispatch de tâches (scan, collecte, analyse)
- Heartbeat et supervision de connexion
- Mises à jour de statut en temps réel

---

## État du code

| Indicateur | Valeur |
|-----------|--------|
| Score qualité | 7,5 / 10 |
| Tests | 688+ tests, 0 échec |
| Fichiers backend | 131 fichiers Python |
| Fichiers frontend | 87 fichiers TS/TSX |
| Fichiers volumineux | `ssh_collector.py` (1 451 L), `collect_service.py` (1 317 L), `network-map/page.tsx` (2 044 L) |
