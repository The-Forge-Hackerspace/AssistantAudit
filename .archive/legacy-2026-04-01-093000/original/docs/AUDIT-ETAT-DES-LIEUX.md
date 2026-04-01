# Audit état des lieux — AssistantAudit Server (post-Sprint 1)

**Date** : 2026-03-31
**Commit** : branche `main`, post steps-01 à steps-29
**Tests** : 688 passed, 0 failures, 56 warnings
**Backend** : 131 fichiers Python, ~23 700 lignes (`backend/app/`)
**Frontend** : 87 fichiers TS/TSX, ~27 300 lignes (`frontend/src/`)

---

## Résumé exécutif

**Score global : 7.5/10** — Projet solide après un sprint intensif de remédiation sécurité. La base est saine, les failles critiques ont été corrigées, mais il reste de la dette technique structurelle.

### Top 3 forces

1. **Sécurité bien durcie** — 21 failles corrigées, encryption at rest (AES-256-GCM), mTLS agents, rate limiting, security headers, enrollment protégé
2. **Architecture service-layer propre** — Séparation routes/services/modèles respectée, ownership check systématique, 688 tests verts
3. **Monitoring opérationnel** — Prometheus metrics, Sentry integration, structured JSON logging, health/ready/liveness endpoints

### Top 3 faiblesses

1. **Fichiers géants non refactorisés** — `ssh_collector.py` (1 451 lignes), `collect_service.py` (1 317 lignes), `network-map/page.tsx` (2 044 lignes)
2. **Couverture de tests asymétrique** — 51 fichiers de test pour 131 modules source ; ~30 services/API sans test dédié
3. **WebSocket handler monolithique** — `websocket.py` mélange routing, persistance, ownership checks et notifications dans un seul fichier (252 lignes, 7 `SessionLocal()` manuels)

---

## Sécurité

### Findings actuels

| Sévérité | Finding | Fichier | Statut |
|----------|---------|---------|--------|
| **MOYEN** | `dangerouslySetInnerHTML` dans `chart.tsx` | `frontend/src/components/ui/chart.tsx:83` | Risque XSS — provient de shadcn/ui, contenu contrôlé (CSS injection de thème). Acceptable mais à surveiller. |
| **MOYEN** | CSP `connect-src 'self'` bloque WS en dev (ports différents 3000 vs 8000) | `backend/app/main.py:116` | Tech-debt #45 — le frontend dev ne peut pas ouvrir de WebSocket sans contourner la CSP |
| **MOYEN** | WinRM SSL cert validation désactivée (`cert_validation = "ignore"`) | `tools/collectors/winrm_collector.py:204` | TODO en commentaire — risque MITM sur réseau interne, acceptable en audit interne, pas en prod externe |
| **BAS** | `ssl.CERT_NONE` dans ssl_checker (11 occurrences) | `tools/ssl_checker/checker.py` | **Attendu** — l'outil d'audit SSL doit pouvoir se connecter à des certificats invalides pour les analyser |
| **BAS** | Rate limiting WebSocket absent | `api/v1/websocket.py` | Tech-debt #23 — un client peut ouvrir des connexions WS illimitées |
| **BAS** | Pas de nettoyage automatique des buffers WS pour users inactifs | `core/websocket_manager.py` | Tech-debt #24 — fuite mémoire lente possible |
| **INFO** | `sentry_sdk.push_scope()` deprecated (4 occurrences) | `core/sentry_integration.py` | Migration vers nouveau API Sentry recommandée |

### Findings corrigés depuis le dernier audit

| # | Description | Résolu dans |
|---|-------------|-------------|
| 1-21 | Voir `backlog/tech-debt.md` section "Résolue" — 21 failles (8 critiques + 13 élevées) | Sprint 1 (2026-03-28 à 2026-03-31) |
| C1 | IDOR scan hosts | step-22 |
| C2 | WS task_status sans vérif agent_id | step-21 |
| C3 | get_db() ne commit pas | step-25 |
| I1 | Routes agent async (violation sync-first) | step-27 |
| I2 | Entreprise sans owner_id | step-28 |

### Points positifs sécurité

- Pas de `shell=True` dans les subprocess — toutes les exécutions utilisent des listes d'arguments
- Pas de hardcoded secrets dans le code — configuration via `.env` + Pydantic Settings
- `SECRET_KEY` auto-générée en dev, validation obligatoire en production
- `ENCRYPTION_KEY` et `FILE_ENCRYPTION_KEY` requis en production (raise ValueError sinon)
- Enrollment tokens : SHA-256 hash + `hmac.compare_digest` (anti timing attack)
- Agent JWT : `owner_id` embarqué dans le token, pas lu depuis le message client
- `.env` dans `.gitignore`, historique git nettoyé (git filter-repo)
- Swagger/ReDoc désactivés en production
- Security headers complets (CSP, HSTS, X-Frame-Options, etc.)

---

## Qualité du code

### Fichiers > 500 lignes (backend)

| Fichier | Lignes | Commentaire |
|---------|--------|-------------|
| `tools/collectors/ssh_collector.py` | 1 451 | God object — collecteur SSH pour 4 profils (linux, opnsense, stormshield, fortigate) |
| `services/collect_service.py` | 1 317 | Orchestration collecte + 2 mappings de contrôles (Windows + Linux, ~600 lignes de data) |
| `tools/ad_auditor/auditor.py` | 754 | Audit AD LDAP — complexité acceptable (audite 12+ contrôles) |
| `services/assessment_service.py` | 650 | Service d'évaluation — logique métier riche |
| `schemas/scan.py` | 560 | Schemas Pydantic pour scans — beaucoup de types différents |
| `services/framework_service.py` | 548 | Service référentiels YAML vers BDD — sync + CRUD |
| `services/oradad_analysis_service.py` | 508 | Analyse ORADAD ANSSI — beaucoup de règles |

### Fichiers > 500 lignes (frontend)

| Fichier | Lignes | Commentaire |
|---------|--------|-------------|
| `outils/network-map/page.tsx` | 2 044 | **Critique** — page monolithique avec React Flow, state management, toolbar, tout en un. Tech-debt #14 |
| `types/api.ts` | 1 073 | Types API — acceptable (centralisation des types) |
| `outils/scanner/page.tsx` | 1 067 | Page scanner — à découper en composants |
| `outils/monkey365/page.tsx` | 944 | Page Monkey365 — même pattern monolithique |
| `audits/evaluation/page.tsx` | 933 | Page évaluation — état complexe |
| `agents/page.tsx` | 893 | Page agents — WebSocket + CRUD |
| `outils/config-parser/page.tsx` | 885 | Page config parser — à découper |
| `entreprises/page.tsx` | 871 | Page entreprises — CRUD classique, trop gros |
| `frameworks/components/framework-editor.tsx` | 860 | Éditeur de référentiels — logique riche |
| `services/api.ts` | 854 | Client API centralisé — acceptable |

### Broad `except Exception` usage

60 occurrences de `except Exception` réparties dans 22 fichiers. La plupart sont justifiées (logging + re-raise ou cleanup), mais le `websocket.py` en a 7 avec `SessionLocal()` manuel sans contexte manager, ce qui est fragile.

### TODOs/FIXMEs en production

| Fichier | Commentaire |
|---------|-------------|
| `winrm_collector.py:199` | `TODO (production) : configurer un CA bundle + validation stricte` |
| `attachment.py:58` | `TODO: Migrer uploaded_by vers Integer FK users.id` |
| `agents.py:97` | `TODO: scheduled purge — delete agents where revoked_at < now() - 30 days` |

---

## Concurrence et async/sync

### Violations du pattern "sync first"

Le projet suit le principe `sync first` (pas d'`async def` sur routes/services, exception WebSocket). L'audit confirme que les `async def` sont **correctement limités à** :

- WebSocket handlers (`websocket.py`, `websocket_manager.py`) — **attendu**
- FastAPI lifespan, health checks, deps (`main.py`, `deps.py`) — **attendu** (framework)
- Exception handlers (`exception_handlers.py`) — **attendu** (framework)
- Middleware dispatch (`audit_logger.py`, `metrics_middleware.py`, `main.py`) — **attendu** (framework)
- `monkey365_streaming_executor.py` — **attendu** (subprocess streaming)
- `monkey365.py` route streaming — **attendu** (WebSocket-adjacent)

**Verdict** : Pas de violation. Les seuls `async` sont dans les couches framework et WebSocket.

### Race conditions WebSocket

Le `websocket.py` utilise `SessionLocal()` manuellement 7 fois dans la boucle principale (`ws_agent`). Chaque `try/except/finally` ouvre et ferme sa propre session. Risques identifiés :

1. **Session leak** — Si une exception non capturée survient entre `db = SessionLocal()` et `db.close()`, la session fuit. Le pattern `try/finally` est respecté mais pourrait être remplacé par un context manager.
2. **Pas de timeout sur les opérations DB** — Si la DB bloque, le handler WS bloque aussi, impactant le heartbeat.
3. **Single-threaded per connection** — Acceptable car chaque WS tourne dans sa propre coroutine asyncio.

### `ConnectionManager` thread safety

Le `ConnectionManager` (instance globale `ws_manager`) stocke les connexions dans des dicts Python simples. Avec uvicorn en mode single-worker asyncio, c'est safe. **En mode multi-worker (production), ces dicts ne sont pas partagés** — chaque worker a son propre `ws_manager`. Ceci est documenté et acceptable pour le MVP.

---

## Dette technique résiduelle

### Ouverte — Critique

Aucune dette critique ouverte. Toutes les failles critiques (#1 à #4, #31 à #33) sont résolues.

### Ouverte — Élevé

| # | Description | Impact |
|---|-------------|--------|
| 6 | 121 occurrences `if not X: raise 404` vers `get_or_404()` | Cohérence code, réduction boilerplate |
| 8 | Ownership check FK chain dupliqué 3 fois | Maintenance, risque de divergence |
| 9 | 15 opérations fichier sans try/except | Risque de crash sur I/O |
| 11 | ~20 schemas avec status/role en `str` au lieu de `Literal`/`Enum` | Validation partielle |
| 13 | Tests manquants : scan_service, collect_service, ad_audit_service, config_analysis_service | Couverture critique basse |
| 14 | `network-map/page.tsx` toujours ~2 044 lignes | Maintenabilité frontend |

### Ouverte — Moyen

| # | Description |
|---|-------------|
| 17 | `uploaded_by` sur Attachment est `String(200)` — devrait être FK `users.id` |
| 20 | CRUD copié-collé (25+ endpoints quasi-identiques) |
| 21 | Services retournent un mix de types |
| 22 | Messages d'erreur mix FR/EN dans tools/* |
| 23 | Rate limiting WebSocket absent |
| 24 | Buffers WS non nettoyés pour users inactifs |
| 26 | Pas de tests frontend (jest/vitest/playwright) |
| 27 | `max_length` manquant sur ~100 champs str schemas output |
| 29 | Import équipements depuis résultats scan pas implémenté |
| 41 | Deux routes de création user (`/auth/register` + `/users/`) |
| 42 | Contacts entreprise sans validation email/téléphone |
| 43 | Credentials en clair passés au task_runner |
| 45 | CSP `connect-src 'self'` bloque WS en dev |

---

## Couverture de tests

### Tests existants (51 fichiers, 688 tests)

Bien couverts :
- Auth/security : `test_auth_security_critical`, `test_password_validation`, `test_auth_refresh`
- RBAC/isolation : `test_rbac_isolation`, `test_rbac_entreprise_owner`, `test_rbac_scan_hosts`, `test_rbac_list_attachments`
- Encryption : `test_encryption`, `test_encrypted_json`, `test_file_encryption`, `test_rotate_kek`
- WebSocket : `test_websocket`, `test_websocket_orphan_tasks`, `test_websocket_task_isolation`, `test_ws_replay_buffer`
- Agents : `test_agents_api`, `test_agent_artifacts`, `test_agent_models`, `test_security_agent`
- API globale : `test_api` (tests d'intégration larges)

### Modules sans test dédié

| Catégorie | Modules non testés |
|-----------|-------------------|
| **Services** | `scan_service`, `collect_service`, `ad_audit_service`, `config_analysis_service`, `network_map_service`, `equipement_service`, `site_service`, `entreprise_service`, `auth_service`, `task_service`, `monkey365_service`, `monkey365_scan_service`, `oradad_analysis_service`, `oradad_config_service`, `framework_service` (partiellement couvert via `test_api`) |
| **API routes** | `scans`, `sites`, `entreprises`, `equipements`, `audits`, `assessments`, `network_map`, `frameworks`, `attachments`, `files`, `oradad` (partiellement couverts par `test_api` mais sans isolation) |
| **Tools** | `ssh_collector`, `winrm_collector`, `nmap_scanner`, `ssl_checker`, `config_parsers/*`, `monkey365_runner/*` |
| **Core** | `rate_limit`, `audit_logger`, `exception_handlers`, `storage`, `task_runner` |
| **Frontend** | **Aucun test** — 0 fichiers de test frontend |

**Note** : Beaucoup de ces modules sont couverts indirectement par `test_api.py` et les tests RBAC, mais sans tests unitaires dédiés, les régressions sont difficiles à isoler.

---

## Dépendances

### Backend (`requirements.txt`)

| Package | Version actuelle | Dernière version | Delta |
|---------|-----------------|-----------------|-------|
| fastapi | 0.135.1 | 0.135.2 | Patch |
| SQLAlchemy | 2.0.48 | 2.0.48 | A jour |
| pydantic | 2.12.5 | 2.12.5 | A jour |
| cryptography | 46.0.6 | 46.0.6 | A jour |
| sentry-sdk | 2.55.0 | 2.57.0 | Minor — **mise à jour recommandée** (corrige `push_scope` deprecation warnings) |
| python-jose | 3.5.0 | 3.5.0 | A jour — mais ce package est en maintenance minimale, envisager `PyJWT` à terme |
| pytest-asyncio | 1.3.0 | 1.3.0 | A jour |

### Frontend (`package.json`)

| Package | Version actuelle | Dernière minor | Delta |
|---------|-----------------|----------------|-------|
| react / react-dom | 19.2.3 | 19.2.4 | Patch |
| next | ^16.2.0 | 16.2.1 | Patch |
| lucide-react | ^0.563.0 | 0.577.0 | Minor — icons updates |
| @xyflow/react | ^12.9.2 | 12.10.2 | Minor |
| axios | ^1.13.5 | 1.14.0 | Minor |
| eslint-config-next | 16.1.6 | 16.2.1 | Minor |

**Verdict** : Dépendances globalement à jour. Aucune vulnérabilité connue dans les versions actuelles. Mise à jour `sentry-sdk` recommandée pour éliminer les 4 deprecation warnings.

---

## Warnings pytest (56 warnings)

| Type | Count | Source |
|------|-------|--------|
| `SAWarning: Flushing object with incompatible polymorphic identity` | ~10 | `test_rbac_scan_hosts.py` — tests créent des `Equipement` au lieu d'`EquipementServeur` |
| `DeprecationWarning: sentry_sdk.push_scope` | ~4 | `sentry_integration.py` — API Sentry v1 deprecated |
| `PytestReturnNotNoneWarning` | 1 | `test_sentry_integration.py` — test retourne `bool` au lieu de `None` |
| Divers SQLAlchemy/internal warnings | ~41 | Warnings standards (eager loading, column naming) |

---

## Recommandations prioritaires

### Top 5 actions (ordre de priorité)

1. **Écrire des tests pour les 4 services critiques** (tech-debt #13)
   - `scan_service.py` — 492 lignes, logique de dispatch nmap, aucun test unitaire
   - `collect_service.py` — 1 317 lignes, orchestre SSH/WinRM, aucun test unitaire
   - `config_analysis_service.py` — 337 lignes, parsing de configurations réseau
   - `ad_audit_service.py` — 333 lignes, audit Active Directory
   - **Impact** : Ces services manipulent des données sensibles (credentials, résultats d'audit) et n'ont pas de filet de sécurité

2. **Refactoriser `websocket.py`** — Extraire la persistance dans un service dédié `ws_persistence_service.py`, remplacer les 7 `SessionLocal()` manuels par un context manager, ajouter un rate limiter WS
   - **Impact** : Réduit le risque de session leak et améliore la maintenabilité

3. **Découper les fichiers géants**
   - `ssh_collector.py` (1 451 lignes) vers un fichier par profil (`ssh_linux.py`, `ssh_opnsense.py`, etc.)
   - `collect_service.py` (1 317 lignes) vers séparer les control mappings en fichiers YAML/JSON
   - `network-map/page.tsx` (2 044 lignes) vers composants React séparés
   - **Impact** : Maintenabilité, Claude Code perd le contexte au-delà de 500 lignes

4. **Migrer `sentry_sdk.push_scope`** vers la nouvelle API Sentry v2 + bumper `sentry-sdk` à 2.57.0
   - **Impact** : Élimine 4 deprecation warnings, prépare la migration forcée lors du prochain major bump

5. **Ajouter le rate limiting WebSocket** (tech-debt #23) — Limiter à N connexions simultanées par user_id et par IP, avec un cleanup périodique des buffers périmés (tech-debt #24)
   - **Impact** : Protection contre le DoS via ouverture massive de WebSocket

### Actions quick-win (< 1 step chacune)

- Bump `fastapi` 0.135.1 vers 0.135.2 (patch)
- Bump `sentry-sdk` 2.55.0 vers 2.57.0 (minor, corrige deprecation)
- Corriger `test_sentry_integration.py` qui retourne `bool` au lieu d'`assert`
- Corriger les tests `test_rbac_scan_hosts.py` qui créent des `Equipement` au lieu d'`EquipementServeur` (polymorphic identity warning)
- Fixer le endpoint `/ready` qui retourne `str(status)` au lieu de `JSONResponse` (`main.py:194`)

---

## Bug trouvé pendant l'audit

### `/ready` endpoint retourne `str(dict)` au lieu de JSON

**Fichier** : `backend/app/main.py:192-196`
```python
return Response(
    content=str(status),  # BUG: str(dict) -> "{'ready': True, ...}"
    status_code=status_code,
    media_type="application/json",
)
```
Le endpoint `/ready` déclare `media_type="application/json"` mais envoie `str(status)` qui produit une représentation Python du dict (guillemets simples, `True` au lieu de `true`), pas du JSON valide. Devrait utiliser `json.dumps(status)` ou `JSONResponse`.

---

## Annexe : compteurs

| Métrique | Valeur |
|----------|--------|
| Fichiers Python backend (`app/`) | 131 |
| Fichiers TS/TSX frontend (`src/`) | 87 |
| Fichiers de test | 51 |
| Tests passants | 688 |
| Warnings pytest | 56 |
| Lignes backend (`app/`) | ~23 700 |
| Lignes frontend (`src/`) | ~27 300 |
| Routes API (routers dans `router.py`) | 18 |
| Services (`services/*.py`) | 17 |
| Modèles (`models/*.py`) | 18 |
| Schemas (`schemas/*.py`) | 14 |
| Tech-debt ouverte critique | 0 |
| Tech-debt ouverte élevée | 6 |
| Tech-debt ouverte moyenne | 13 |
| `except Exception` occurrences | 60 (22 fichiers) |
| `async def` dans routes/services (hors WS/framework) | 0 (conforme) |
| `subprocess` sans `shell=True` | Toutes (conforme) |
| Hardcoded secrets | 0 |
