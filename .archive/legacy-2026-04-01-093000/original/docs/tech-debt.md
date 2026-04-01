# Tech Debt Tracker

Dernière mise à jour : 2026-03-31 (review Sprint 2)

## Ouverte

### Critique (avant mise en production)

| # | Description | Repo | Fichier | Issue |
|---|-------------|------|---------|-------|
| 48 | **BUG-S2-001** — Dockerfile manque libs système WeasyPrint (libgobject, libcairo, libpango, libgdk-pixbuf) → backend KO en Docker | serveur | `Dockerfile:18` | `bugs/open/BUG-S2-001-dockerfile-weasyprint-deps.md` |
| ~~1~~ | ~~`.env` dans l'historique git~~ — **RÉSOLU** git filter-repo exécuté manuellement (2026-03-29) | serveur | historique git | |
| ~~2~~ | ~~`agent_tasks.parameters` credentials AD en clair~~ — **RÉSOLU** EncryptedJSON implémenté (2026-03-29, steps-01) | serveur | `models/agent_task.py:43` | |
| ~~3~~ | ~~30+ endpoints sans isolation par owner_id~~ — **RÉSOLU** RBAC Phase 1 owner_id propagation (2026-03-29, steps 12-19) — 32 tests d'isolation. Phase 2 ResourcePermission reportée | serveur | `api/v1/*.py` | |
| ~~4~~ | ~~Endpoint `/auth/refresh` manquant~~ — **RÉSOLU** POST /auth/refresh implémenté (2026-03-29, steps-02) | serveur | `api/v1/auth.py` | |
| ~~31~~ | ~~**IDOR scan hosts**~~ — **RÉSOLU** ownership via host→scan→owner_id + 9 tests isolation (2026-03-30, step-22) | serveur | `api/v1/scans.py` | `bugs/closed/c1-scan-host-idor.md` |
| ~~32~~ | ~~**WS task_status sans vérif agent**~~ — **RÉSOLU** filtre `agent_id` ajouté + 6 tests isolation (2026-03-30, step-21) | serveur | `api/v1/websocket.py` | `bugs/open/c2-ws-task-status-idor.md` |
| ~~33~~ | ~~**get_db() ne commit pas**~~ — **RÉSOLU** auto-commit/rollback ajouté + 3 tests (2026-03-30, step-25) | serveur | `core/database.py` | `bugs/closed/c3-get-db-no-commit.md` |

### Élevé (à traiter rapidement)

| # | Description | Repo | Fichier | Issue |
|---|-------------|------|---------|-------|
| ~~5~~ | ~~38 routes sans service layer~~ — **RÉSOLU** 7 services créés en 5 steps (2026-03-29, steps-07→11) | serveur | `api/v1/*.py` | |
| 6 | 121 occurrences `if not X: raise 404` — migrer vers `get_or_404()` (helper créé, appliqué sur audits.py comme démo) | serveur | `api/v1/*.py` | |
| ~~7~~ | ~~`rotate_kek.py` est un stub~~ — **RÉSOLU** script complet : CLI argparse, dry-run/--apply, 3 tests (2026-03-31, steps-23) | serveur | `scripts/rotate_kek.py` | |
| 8 | Ownership check FK chain dupliqué 3 fois — centraliser quand RBAC implémenté | serveur | `attachments.py`, `file_service.py` | |
| 9 | 15 opérations fichier sans try/except — créer helper `atomic_write()` | serveur | `executor.py`, `attachments.py`, `file_service.py`, `cert_manager.py` | |
| ~~10~~ | ~~`chmod 600` sur `ca.key`~~ — **RÉSOLU** chmod + WARNING implémentés (2026-03-29, steps-03) | serveur | `core/cert_manager.py:79` | |
| 11 | ~20 schemas avec champs status/role en `str` au lieu de `Literal`/`Enum` | serveur | `schemas/audit.py`, `assessment.py`, `user.py`, `equipement.py` | |
| ~~12~~ | ~~`test_api.py` fragile~~ — **RÉSOLU** rate limiter reset + migration conftest.py (2026-03-29, steps-06) | serveur | `tests/test_api.py` | |
| 13 | Tests manquants : scan_service, collect_service, ad_audit_service, config_analysis_service | serveur | `tests/` | |
| 14 | `network-map/page.tsx` toujours ~2900 lignes | serveur | `frontend/src/app/outils/network-map/page.tsx` | |
| ~~15~~ | ~~L'agent ne streame pas les logs en temps réel~~ — **RÉSOLU** throttle 5s + filtrage credentials (2026-03-29, steps-05) | agent + serveur | `task_runner.py`, `websocket.py` | |
| ~~16~~ | ~~Pas de détection des tâches orphelines~~ — **RÉSOLU** déjà implémenté, tests ajoutés (2026-03-29, steps-05) | serveur | `websocket_manager.py` | |
| ~~34~~ | ~~**3 routes agent async**~~ — **RÉSOLU** converties sync + background_tasks pour WS (2026-03-30, step-27) | serveur | `api/v1/agents.py` | `bugs/closed/i1-async-routes-agents.md` |
| ~~35~~ | ~~**Entreprise sans owner_id**~~ — **RÉSOLU** colonne owner_id NOT NULL + migration backfill + 6 tests (2026-03-30, step-28) | serveur | `models/entreprise.py` | `bugs/closed/i2-entreprise-no-owner.md` |
| ~~36~~ | ~~**DomainEntryResponse expose password**~~ — **RÉSOLU** champ password retiré du schema réponse + frontend adapté + 3 tests (2026-03-30, step-29) | serveur | `api/v1/oradad.py` | |
| ~~37~~ | ~~**Bug _replay_buffered_events**~~ — **RÉSOLU** enumerate() au lieu de list.index() + 3 tests (2026-03-30, step-30) | serveur | `core/websocket_manager.py` | |
| ~~38~~ | ~~**Enrollment O(n) + FOR UPDATE all**~~ — **RÉSOLU** query directe par hash, 1 seule ligne lockée (2026-03-30, step-31) | serveur | `agent_service.py` | `bugs/closed/i5-enrollment-on-lock.md` |
| ~~39~~ | ~~**launch_scan sans vérif ownership site**~~ — **RÉSOLU** ownership via site→entreprise + user_has_access + 3 tests (2026-03-30, step-23) | serveur | `api/v1/scans.py` | `bugs/closed/i6-launch-scan-no-site-ownership.md` |
| ~~40~~ | ~~**list_attachments sans ownership**~~ — **RÉSOLU** join chain ownership + 3 tests (2026-03-30, step-24, commit 52bc6f0) | serveur | `api/v1/attachments.py` | `bugs/closed/i7-list-attachments-no-ownership.md` |

### Moyen (amélioration continue)

| # | Description | Repo | Fichier | Issue |
|---|-------------|------|---------|-------|
| 17 | `uploaded_by` sur Attachment est `String(200)` — devrait être FK vers `users.id` | serveur | `models/attachment.py` | |
| ~~18~~ | ~~`owner_id` sur audits/scans/ad_audit_results est nullable~~ — **RÉSOLU** backfill + NOT NULL sur scans et ad_audit_results (2026-03-31, steps-21) | serveur | `models/` | |
| ~~19~~ | ~~JSON columns sensibles non chiffrés (dc_list, domain_admins)~~ — **RÉSOLU** EncryptedJSON (2026-03-29, steps-01) | serveur | `models/ad_audit_result.py` | |
| 20 | CRUD copié-collé dans entreprises/sites/equipements/audits (25+ endpoints quasi-identiques) | serveur | `api/v1/` | |
| 21 | Services retournent un mix de types (SQLAlchemy models, dicts, primitifs) | serveur | `services/*.py` | |
| 22 | Messages d'erreur mix FR/EN dans tools/* | serveur | `tools/*.py` | |
| 23 | Rate limiting WebSocket absent | serveur | `api/v1/websocket.py` | |
| 24 | Buffers WS non nettoyés pour users inactifs | serveur | `core/websocket_manager.py` | |
| ~~25~~ | ~~Pas de complexité mot de passe~~ — **RÉSOLU** min 12 chars + complexité (2026-03-29, steps-03) | serveur | `schemas/user.py` | |
| 26 | Pas de tests unitaires frontend (jest/vitest) — tests Playwright E2E créés dans Sprint 2 pour checklists/tags/reports/responsive | serveur | `frontend/` | |
| 49 | Templates rapport `\| safe` sans sanitisation HTML (objectives, scope, introduction) — risque XSS si compte auditeur compromis | serveur | `backend/app/templates/reports/sections/` | |
| 50 | `TagSelector` non intégré dans les pages de détail (équipements, findings) — seulement TagFilter sur liste équipements | serveur | `frontend/src/app/equipements/page.tsx` | |
| 51 | Interface frontend fiche intervention Audit (champs step 36) non créée | serveur | `frontend/src/app/audits/` | |
| 27 | `max_length` manquant sur ~100 champs str dans les schemas output | serveur | `schemas/*.py` | |
| 28 | AD collector PowerShell script est un placeholder | agent | `tools/ad_collector_tool.py` | |
| 29 | Import équipements depuis résultats scan pas encore implémenté | serveur | `api/v1/equipements.py` | |
| 30 | DPAPI non installé sur l'agent — JWT stocké en base64 (warning) | agent | `config.py` | |
| 41 | Deux routes de création user (`/auth/register` + `/users/`) — consolider | serveur | `api/v1/auth.py`, `api/v1/users.py` | |
| 42 | Contacts entreprise sans validation email/téléphone au niveau schema | serveur | `entreprise_service.py:83-91` | |
| 43 | Credentials en clair passés au task_runner (problème pour migration Celery) | serveur | `api/v1/tools/collect.py:55-64` | |
| ~~44~~ | ~~Frontend ne tente pas refresh token avant redirect 401~~ — **RÉSOLU** intercepteur mutex + queue + authApi.refresh() (2026-03-31, steps-22) | serveur | `frontend/src/lib/api-client.ts` | |
| 45 | CSP `connect-src 'self'` bloque WS en dev (ports différents) | serveur | `backend/app/main.py:116` | |
| ~~46~~ | ~~`ScanReseau.owner_id` nullable~~ — **RÉSOLU** NOT NULL + migration backfill (2026-03-31, steps-21) | serveur | `models/scan.py` | |
| ~~47~~ | ~~Endpoint `/metrics` non authentifié~~ — **RÉSOLU** `Depends(get_current_admin)` (2026-03-31, steps-21) | serveur | `backend/app/main.py` | |

## Résolue

| # | Description | Résolu dans | Date |
|---|-------------|-------------|------|
| 1 | 3 injections PowerShell (tenant_id, subscriptions, ruleset) | Audit sécu 2/8 | 2026-03-28 |
| 2 | 3 failles attachments (download/preview/delete sans ownership) | Audit sécu 4/8 | 2026-03-28 |
| 3 | Agent WS event injection (owner_id client-supplied) | Audit sécu 7/8 | 2026-03-28 |
| 4 | CVE cryptography 46.0.5 → 46.0.6 | Audit sécu 6/8 | 2026-03-28 |
| 5 | Swagger/ReDoc accessibles en production | Audit sécu 8/8 | 2026-03-28 |
| 6 | Stack trace dans réponses 500 | Audit sécu 8/8 | 2026-03-28 |
| 7 | Timing attack enrollment token (== → hmac.compare_digest) | Audit sécu 3/8 | 2026-03-28 |
| 8 | X-Forwarded-For spoofing rate limiter | Audit sécu 1/8 | 2026-03-28 |
| 9 | Injection XML ORADAD sysvol_filter | Audit sécu 2/8 | 2026-03-28 |
| 10 | ENCRYPTION_KEY vide en prod → passthrough silencieux | Audit sécu 3/8 + 5/8 | 2026-03-28 |
| 11 | WS message size illimité | Audit sécu 7/8 | 2026-03-28 |
| 12 | Header Server expose version uvicorn | Audit sécu 8/8 | 2026-03-28 |
| 13 | Race condition enrollment (double activate) | Audit dev 2/4 | 2026-03-28 |
| 14 | Subprocess async sans timeout (Monkey365 streaming) | Audit dev 2/4 | 2026-03-28 |
| 15 | Stale closure re-render sur 7 pages frontend | Audit frontend | 2026-03-28 |
| 16 | cursor-pointer manquant Tailwind v4 | Audit frontend | 2026-03-28 |
| 17 | WebSocket 403 — middleware BaseHTTPMiddleware | Intégration agent | 2026-03-28 |
| 18 | WebSocket 403 — route montée sous /api/v1 au lieu de / | Intégration agent | 2026-03-28 |
| 19 | Timezone heartbeat agent (UTC inconsistant) | Intégration agent | 2026-03-28 |
| 20 | query_optimizer.py mort (270 lignes) | Audit dev 4/4 | 2026-03-28 |
| 21 | Start-Transcript conflit fichier en mode device code | Fix Monkey365 | 2026-03-28 |
| 22 | Codes ANSI bruts dans les logs Monkey365 | Fix Monkey365 | 2026-03-28 |
| 23 | PingCastle — tout supprimé (jamais fonctionné) | Cleanup | 2026-03-28 |
