# Spécification API REST — AssistantAudit

<!-- SCOPE: Conventions, mécanismes d'authentification et liste des endpoints HTTP/WebSocket de l'API publique. Ce document n'enumère pas chaque route exhaustivement — la source de vérité interactive est Swagger sur `http://localhost:8000/docs`. -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu integres un client de l'API ou tu ajoutes un endpoint. -->
<!-- SKIP_WHEN: Tu cherches le schema de la DB ou un detail d'implementation. -->
<!-- PRIMARY_SOURCES: backend/app/api/v1/router.py, backend/app/api/v1/*.py, backend/app/core/errors.py -->
> **SCOPE :** Conventions, mécanismes d'authentification et liste des endpoints HTTP/WebSocket de l'API publique. Ce document n'enumère pas chaque route exhaustivement — la source de vérité interactive est Swagger sur `http://localhost:8000/docs`.

| DOC_KIND | DOC_ROLE | READ_WHEN | SKIP_WHEN | PRIMARY_SOURCES |
|----------|----------|-----------|-----------|------------------|
| reference | api-contract | tu integres un client de l'API ou tu ajoutes un endpoint | tu cherches le schema de la DB ou un detail d'implementation | `backend/app/api/v1/router.py`, `backend/app/api/v1/*.py`, `backend/app/core/errors.py`, `backend/app/core/exception_handlers.py`, `backend/app/core/rate_limit.py` |

## Quick Navigation

- [Conventions](#conventions)
- [Authentification](#authentification)
- [Endpoints par module](#endpoints-par-module)
- [Codes d'erreur](#codes-derreur)
- [WebSocket](#websocket)
- [Documentation interactive](#documentation-interactive)
- [Maintenance](#maintenance)

## Agent Entry

Quand lire ce document : Tu integres un client de l'API ou tu ajoutes un endpoint.

Quand l'ignorer : Tu cherches le schema de la DB ou un detail d'implementation.

Sources primaires (auto-discovery) : `backend/app/api/v1/router.py, backend/app/api/v1/*.py, backend/app/core/errors.py`

## Conventions

| Élément | Règle |
|---------|-------|
| Base path | `/api/v1` (préfixe défini dans `Settings.API_V1_PREFIX`) |
| Auth principale | Cookies httpOnly `aa_access_token` + `aa_refresh_token`, `SameSite=Strict`, `Secure` hors dev |
| Auth programmatique | `Authorization: Bearer <access_token>` (Swagger, agents, scripts) |
| Refresh path | `/api/v1/auth/refresh` (le cookie refresh est scopé sur ce path) |
| Schémas I/O | Pydantic v2 (validation `422` automatique sur erreur) |
| Pagination | `?page=1&page_size=20` ; max `MAX_PAGE_SIZE=100` ; réponse `PaginatedResponse{items, total, page, page_size, pages}` |
| Rate-limit (par IP, in-memory, par minute) | AUTH `RATE_LIMIT_AUTH_MAX=5`, API `RATE_LIMIT_API_MAX=30`, PUBLIC `RATE_LIMIT_PUBLIC_MAX=100` |
| CORS | Origines pilotées par `CORS_ORIGINS` (default `http://localhost:3000`, `http://frontend:3000`) |
| mTLS | Les agents Windows présentent un certificat client X.509 (CA = `CA_CERT_PATH`) lors de la connexion WebSocket |
| Reverse proxy | NPMPlus (prod) / Caddy (staging) ; `X-Forwarded-Proto/For` honoré si l'IP source ∈ `FORWARDED_ALLOW_IPS` |
| Format erreurs | `{ "detail": "..." }` ou `{ "detail": [{loc, msg, type}, ...] }` (validation Pydantic) |
| Domain exceptions | Levées par les services (`AppError`, `NotFoundError`, `ForbiddenError`, `ConflictError`, `ValidationError`, `BusinessRuleError`, `ServerError`) ; traduites en HTTPException par les routeurs |

## Authentification

Le module est défini dans [`backend/app/api/v1/auth.py`](../../backend/app/api/v1/auth.py).

| Méthode | Path | Description | Auth requise |
|---------|------|-------------|--------------|
| POST | `/api/v1/auth/login` | Login form-data (`username`, `password`) → cookies + body `TokenResponse` | non |
| POST | `/api/v1/auth/login/json` | Login JSON (`LoginRequest`) → cookies + body `TokenResponse` | non |
| POST | `/api/v1/auth/refresh` | Refresh access token via cookie ou body `RefreshRequest` | refresh token |
| POST | `/api/v1/auth/logout` | Invalide les cookies d'auth | access token |
| GET | `/api/v1/auth/me` | Profil utilisateur courant | access token |
| POST | `/api/v1/auth/change-password` | Changement de mot de passe (`PasswordChange`) | access token |
| POST | `/api/v1/auth/register` | Création de compte (admin uniquement) | admin |

Rôles RBAC : `admin`, `auditeur`, `lecteur`. Dépendances FastAPI : `get_current_user`, `get_current_auditeur`, `get_current_admin`, `get_current_agent` (mTLS pour les daemons).

Isolation multi-tenant : un `auditeur` ne voit que les ressources dont `owner_id == current_user.id` ; un `admin` voit tout.

## Endpoints par module

Chaque module est monté avec son préfixe dans [`router.py`](../../backend/app/api/v1/router.py). Pour chaque ressource, le pattern usuel CRUD s'applique : `GET /` (liste paginée), `POST /` (création), `GET /{id}` (détail), `PUT /{id}` (mise à jour), `DELETE /{id}` (suppression admin).

### Health

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/health` | Liveness probe (200 si l'app tourne) | non |
| GET | `/api/v1/health/ready` | Readiness probe (DB + dépendances) | non |
| GET | `/api/v1/metrics` | Export Prometheus (si exposé) | non |

### Entreprises, Sites, Équipements

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/entreprises` | Liste paginée (filtrée par `owner_id` si non-admin) | user |
| POST | `/api/v1/entreprises` | Création | auditeur |
| GET | `/api/v1/entreprises/{id}` | Détail | user |
| PUT | `/api/v1/entreprises/{id}` | Mise à jour | auditeur |
| DELETE | `/api/v1/entreprises/{id}` | Suppression | admin |
| GET/POST/PUT/DELETE | `/api/v1/sites/...` | Mêmes patterns ; FK `entreprise_id` | user/auditeur/admin |
| GET/POST/PUT/DELETE | `/api/v1/equipements/...` | Mêmes patterns ; FK `site_id` | user/auditeur/admin |

### Audits & Évaluations

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/audits` | Liste paginée (`?entreprise_id=`) | user |
| POST | `/api/v1/audits` | Création | auditeur |
| GET | `/api/v1/audits/{id}` | Détail (`AuditDetail`) | user |
| PUT | `/api/v1/audits/{id}` | Mise à jour | auditeur |
| DELETE | `/api/v1/audits/{id}` | Suppression | admin |
| GET | `/api/v1/audits/{id}/executive-summary` | Synthèse exécutive (KPIs, top non-conformités) | user |
| GET/POST | `/api/v1/assessments/...` | Campagnes d'évaluation (rattachées à un audit + un framework) | user/auditeur |
| GET/PUT | `/api/v1/assessments/{id}/control-results/{cr_id}` | Réponse à un contrôle individuel | auditeur |

### Référentiels (Frameworks)

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/frameworks` | Liste des référentiels (auto-sync depuis `frameworks/*.yaml` au démarrage) | user |
| GET | `/api/v1/frameworks/{id}` | Détail (chapitres + contrôles) | user |
| POST | `/api/v1/frameworks` | Import d'un YAML personnalisé | admin |
| GET | `/api/v1/frameworks/{id}/controls` | Liste des contrôles | user |

### Findings, Recommandations, Plan de remédiation

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/findings` | Liste paginée (`?audit_id`, `?severity`, `?status`) | user |
| GET | `/api/v1/findings/{id}` | Détail + historique de statut | user |
| PUT | `/api/v1/findings/{id}` | Mise à jour (transition d'état contrôlée par `VALID_TRANSITIONS`) | auditeur |
| POST | `/api/v1/findings/{id}/status` | Transition d'état + commentaire (audit trail) | auditeur |
| GET | `/api/v1/audits/{id}/recommendations` | Recommandations générées | user |
| GET | `/api/v1/audits/{id}/remediation-plan` | Plan de remédiation priorisé | user |

### Checklists ANSSI

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/checklists` | Liste (filtrable `?audit_id`, `?type`) | user |
| GET | `/api/v1/checklists/{id}` | Détail (sections + items) | user |
| PUT | `/api/v1/checklists/{id}/items/{item_id}` | Réponse à un item (statut, preuve, commentaire) | auditeur |

### Agents (mTLS)

Module défini dans [`agents.py`](../../backend/app/api/v1/agents.py). Préfixe `/api/v1/agents`.

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| POST | `/api/v1/agents/create` | Crée un agent + retourne un code d'enrollment (10 min) | auditeur |
| GET | `/api/v1/agents/` | Liste (filtrée par `user_id`, sauf admin) | auditeur |
| GET | `/api/v1/agents/supported-tools` | Outils disponibles (source de vérité backend) | auditeur |
| POST | `/api/v1/agents/enroll` | L'agent échange `code` + CSR contre cert mTLS et JWT agent | enrollment code |
| POST | `/api/v1/agents/heartbeat` | Heartbeat de l'agent (status, last_ip) | mTLS agent |
| POST | `/api/v1/agents/dispatch` | Dispatch d'une tâche vers un agent | auditeur |
| POST | `/api/v1/agents/tasks/{task_id}/result` | L'agent soumet le résultat (artefacts) | mTLS agent |
| POST | `/api/v1/agents/tasks/{task_id}/artifacts` | Upload binaire (≤ 100 MB) | mTLS agent |
| DELETE | `/api/v1/agents/{id}` | Révocation du certificat agent | auditeur/admin |

### Pipelines de collecte

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| POST | `/api/v1/pipelines/detect-profile` | Détecte le profil (Linux/Windows/firewall…) | auditeur |
| POST | `/api/v1/pipelines/prefill` | Pré-remplit la config à partir d'un échantillon | auditeur |
| POST | `/api/v1/pipelines` | Lance la collecte via SSH/WinRM | auditeur |
| GET | `/api/v1/pipelines/{id}/results` | Résultats d'une collecte | user |

### Outils intégrés

Préfixe `/api/v1/tools/` (sous-routeur agrégé dans `tools/__init__.py`).

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| POST | `/api/v1/tools/ad-audit/run` | Audit Active Directory (LDAP) | auditeur |
| POST | `/api/v1/tools/collect/dispatch` | Dispatch collecte SSH/WinRM | auditeur |
| POST | `/api/v1/tools/config-analysis/parse` | Parse Fortinet / OPNsense | auditeur |
| POST | `/api/v1/tools/monkey365/scan` | Scan M365 via PowerShell 7 (streaming WebSocket) | auditeur |
| POST | `/api/v1/tools/ssl-checker/check` | Vérification certificat / cipher suite | auditeur |

### ORADAD (audit AD ANSSI)

Préfixe `/api/v1/oradad/`. Endpoints CRUD pour `oradad_config` (domaines explicits chiffrés via `EncryptedJSON`) + lancement de collectes ORADAD.

### Network Map

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/network-map/{audit_id}` | Cartographie (sites + équipements + connexions + VLANs) | user |
| POST | `/api/v1/network-map/{audit_id}/connections` | Création/maj de connexions | auditeur |
| POST | `/api/v1/network-map/{audit_id}/vlans` | Définition de VLAN | auditeur |

### Fichiers chiffrés, pièces jointes, tags

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| POST | `/api/v1/files/upload` | Upload chiffré (envelope KEK + DEK) | auditeur |
| GET | `/api/v1/files/{id}` | Téléchargement déchiffré | user |
| GET/POST/DELETE | `/api/v1/attachments/...` | Pièces jointes (preuves) liées aux assessments/findings | user |
| GET/POST/DELETE | `/api/v1/tags/...` | Tags (auditeur, équipement, finding…) | user |

### Rapports (PDF/DOCX)

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| POST | `/api/v1/reports/generate` | Génère un rapport (Jinja2 + WeasyPrint PDF / python-docx) | auditeur |
| GET | `/api/v1/reports/{id}` | Métadonnées du rapport | user |
| GET | `/api/v1/reports/{id}/download` | Téléchargement | user |

### Utilisateurs

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| GET | `/api/v1/users` | Liste (admin) | admin |
| GET | `/api/v1/users/{id}` | Détail | admin / soi |
| PUT | `/api/v1/users/{id}` | Mise à jour | admin / soi (champs limités) |
| DELETE | `/api/v1/users/{id}` | Désactivation | admin |

## Codes d'erreur

| HTTP | Cause | Cas typique |
|------|-------|-------------|
| 400 | Mauvaise requête | Body manquant, transition de statut invalide |
| 401 | Non authentifié | Cookie/Bearer absent ou expiré, JWT signature invalide |
| 403 | Interdit | RBAC : isolation `owner_id`, rôle insuffisant, agent révoqué (`revoked_at`) |
| 404 | Introuvable | `NotFoundError` levée par le service |
| 409 | Conflit | `ConflictError` (ex. nom unique déjà utilisé) |
| 422 | Validation Pydantic | Schéma I/O invalide (champs manquants, types) |
| 429 | Rate-limit dépassé | Login (5/min), API (30/min), public (100/min) |
| 500 | Erreur serveur | `ServerError` (génération PDF, dépendance externe), bug |

Mapping `core/errors.py` → HTTP : `NotFoundError → 404`, `ForbiddenError → 403`, `ConflictError → 409`, `ValidationError/BusinessRuleError → 400`, `ServerError → 500`. La traduction est centralisée dans `core/exception_handlers.py`.

## WebSocket

Les routes WebSocket sont **montées sur l'app racine** (pas sous `/api/v1`) — voir [`websocket.py`](../../backend/app/api/v1/websocket.py).

| Endpoint | Description | Auth |
|----------|-------------|------|
| `WS /ws/user` | Notifications temps réel pour le frontend (pings, progress collectes) | Cookie `aa_access_token` (priorité) ou `?token=` |
| `WS /ws/agent` | Connexion daemon Windows : heartbeat, dispatch de tâches, streaming résultats | `?token=` (JWT agent émis à l'enrollment) + mTLS au TLS layer |

Limites : taille max d'un message entrant 4 MiB ; reconnect exponentiel côté agent ; manager `ws_manager` gère la concurrence par `user_id`/`agent_uuid`.

## Documentation interactive

| Surface | URL |
|---------|-----|
| Swagger UI (interactif) | http://localhost:8000/docs |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| ReDoc | http://localhost:8000/redoc |

La spec OpenAPI complète (incluant tous les endpoints exhaustivement, les schemas Pydantic et les `tags`) est générée automatiquement par FastAPI.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

| Quand | Action |
|-------|--------|
| Ajout d'un router dans `backend/app/api/v1/` | Ajouter une ligne dans la table « Endpoints par module » et dans `router.py` |
| Changement de format d'erreur ou de mapping `errors.py` | Mettre à jour la section « Codes d'erreur » |
| Évolution de la politique d'auth (cookies, mTLS, refresh) | Mettre à jour « Conventions » + « Authentification » |
| Modification des limites de pagination ou de rate-limit | Mettre à jour « Conventions » |
| Ajout d'un endpoint WebSocket | Mettre à jour la section WebSocket |

**Vérification :** la liste exhaustive des routes peut être confirmée via `curl http://localhost:8000/openapi.json | jq '.paths | keys'`.
