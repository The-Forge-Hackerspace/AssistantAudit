
# Tests — AssistantAudit

<!-- SCOPE: Strategie de test, structure des suites, commandes d'execution et seuils de couverture pour AssistantAudit. -->
<!-- DOC_KIND: index -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu rediges un test ou tu prepares un cycle CI. -->
<!-- SKIP_WHEN: Tu cherches l'API ou les exigences. -->
<!-- PRIMARY_SOURCES: backend/tests/, tests/e2e/, tests/manual/ -->

## Quick Navigation

- [Pyramide de test](#pyramide-de-test)
- [Story-Level Test Task Pattern](#story-level-test-task-pattern)
- [Suites backend](#suites-backend)
- [Suites E2E Playwright](#suites-e2e-playwright)
- [Tests manuels](#tests-manuels)
- [Couverture](#couverture)
- [Pieges connus](#pieges-connus)
- [Commandes](#commandes)
- [Conventions](#conventions)
- [Maintenance](#maintenance)

> **SCOPE :** Strategie de test, structure des suites, commandes d'execution et seuils de couverture pour AssistantAudit.

## Agent Entry

Quand lire ce document : Tu rediges un test ou tu prepares un cycle CI.

Quand l'ignorer : Tu cherches l'API ou les exigences.

Sources primaires (auto-discovery) : `backend/tests/, tests/e2e/, tests/manual/`

## Pyramide de test

| Niveau | Outil | Cible |
|---|---|---|
| E2E | Playwright (`@playwright/test 1.58`) | Parcours utilisateur complets via l'UI Next.js (auth, RBAC, navigation, formulaires critiques). Repertoire `tests/e2e/`. |
| Integration backend | pytest 9 + pytest-mock + pytest-cov | Routes FastAPI, services, persistence SQLAlchemy, WebSocket, chiffrement. Repertoire `backend/tests/`. |
| Manuel | Bash + jq + curl | Verifications hors automation : durcissement Docker, sante des conteneurs, scenarios reseau. Repertoire `tests/manual/`. |
| Unit frontend | Vitest (cible) | Composants React et hooks isoles. **Non implemente** — chantier a ouvrir (objectif : couvrir `frontend/src/components/` et `frontend/src/hooks/`). |

## Story-Level Test Task Pattern

Pour chaque Story Linear (TOS-XX), prevoir une tache `tests` dediee qui derive 3 a 5 scenarios prioritaires selon le **Risk-Based Testing** :

1. **Critical Path** — chemin principal de la fonctionnalite.
2. **Money / Security / Data integrity** — toute logique touchant aux secrets, RBAC, chiffrement, isolation multi-tenant.
3. **Edge cases** — limites, erreurs, concurrence, valeurs invalides.

Les tests sont planifies par `agile-workflow:ln-523-auto-test-planner` puis executes par `agile-workflow:ln-404-test-executor`. Les scenarios prioritaires (Priority >= 15) sont obligatoires ; les autres sont ajoutes selon la valeur (Impact x Probabilite).

## Suites backend

Echantillon representatif des 72 modules de `backend/tests/` (couverture 688+ cas).

| Fichier | Couverture | Notes |
|---|---|---|
| `test_auth_security_critical.py` | Login, JWT, refresh, brute-force | Priorite **Security** |
| `test_auth_refresh.py` | Rotation des tokens | |
| `test_password_validation.py` | Politique de mot de passe | |
| `test_encryption.py` | AES-256-GCM (colonnes chiffrees) | |
| `test_encrypted_json.py` | `TypeDecorator EncryptedJSON` (KEK+DEK) | |
| `test_file_encryption.py` | Enveloppe chiffrement fichiers | |
| `test_rotate_kek.py` | Rotation de la cle KEK | |
| `test_websocket.py` | Communication WebSocket agents | |
| `test_websocket_orphan_tasks.py` | Nettoyage des taches orphelines | |
| `test_websocket_task_isolation.py` | Isolation des taches par agent | |
| `test_ws_replay_buffer.py` | Buffer de relecture WebSocket | |
| `test_agent_artifacts.py` | Stockage des artefacts agents | |
| `test_agent_reconnect.py` | Reconnexion agent + heartbeat | |
| `test_rbac_isolation.py` | Cloisonnement multi-tenant | |
| `test_rbac_entreprise_owner.py` | Roles owner d'entreprise | |
| `test_rbac_list_attachments.py` | Filtrage RBAC pieces jointes | |
| `test_monkey365_executor.py` | Executeur PowerShell Monkey365 | |
| `test_monkey365_streaming.py` | Streaming sortie PS vers WebSocket | |
| `test_oradad_anssi.py` | Mappage ORADAD vers ANSSI | |
| `test_oradad_password_leak.py` | Detection fuites de mots de passe AD | |
| `test_finding_service.py` | Service de gestion des findings | |
| `test_recommendations.py` | Generation des recommandations PDF | |
| `test_remediation_plan.py` | Plan de remediation | |
| `test_executive_summary.py` | Synthese executive | |
| `test_report_template.py` | Templates Jinja2 + WeasyPrint | |
| `test_health_check.py` | `/health`, `/ready`, `/live` | |
| `test_security_hardening.py` | Headers HTTP + securite middleware | |
| `test_docker_hardening.py` | Verification image production | |

Liste complete : `backend/tests/test_*.py` (voir `ls backend/tests/`).

## Suites E2E Playwright

| Spec | Couverture |
|---|---|
| `tests/e2e/smoke-public.spec.ts` | Pages publiques accessibles sans session |
| `tests/e2e/smoke-auth.spec.ts` | Smoke connecte (login + navigation) |
| `tests/e2e/auth.spec.ts` | Authentification, refresh, logout |
| `tests/e2e/rbac.spec.ts` | Isolation multi-tenant + roles |
| `tests/e2e/audits.spec.ts` | CRUD audits + assessments |
| `tests/e2e/agents.spec.ts` | Cycle de vie des agents Windows |
| `tests/e2e/entreprises.spec.ts` | Gestion entreprises |
| `tests/e2e/sites.spec.ts` | Gestion sites |
| `tests/e2e/equipements.spec.ts` | Gestion equipements |
| `tests/e2e/utilisateurs.spec.ts` | Gestion utilisateurs |
| `tests/e2e/frameworks.spec.ts` | Synchronisation frameworks YAML |
| `tests/e2e/network-map.spec.ts` | Editeur de carte reseau (`@xyflow/react`) |
| `tests/e2e/responsive.spec.ts` | Responsivite mobile / desktop |
| `tests/e2e/sidebar-breakpoint.spec.ts` | Comportement de la sidebar |

Helpers partages : `tests/e2e/helpers.ts`, `tests/e2e/global-setup.ts`.

## Tests manuels

Scripts bash pour les scenarios non automatisables (verification d'image Docker, durcissement, etc.). Voir [`tests/manual/README.md`](manual/README.md) pour la liste des suites disponibles, les prerequis (`jq`, `curl`, `docker compose`) et la convention `{NN}-{sujet}/test-{slug}.sh`. Lancer toutes les suites : `cd tests/manual && ./test-all.sh`.

## Couverture

| Domaine | Couverture |
|---|---|
| Auth / securite / RBAC / isolation multi-tenant | Bien couvert |
| Chiffrement (AES-256-GCM, enveloppe KEK+DEK, rotation) | Bien couvert |
| WebSocket et cycle de vie des agents | Bien couvert |
| API endpoints principaux (audits, entreprises, agents, findings, reports) | Bien couvert |
| ~30 services sans test dedie (`scan_service`, `collect_service`, `ad_audit_service`, ...) | Lacune |
| Outils (`ssh_collector`, `ssl_checker`, parsers de configs Fortinet/OPNsense) | Lacune |
| Tests unitaires frontend (Vitest sur `components/` et `hooks/`) | Non implemente |

**Cibles :** couverture backend `>80%` ; **0 echec** en CI (`ci.yml` + `playwright.yml`).

## Pieges connus

| Piege | Effet observe | Mitigation |
|---|---|---|
| Redirect 307 leak hostname Docker | Une redirection FastAPI peut exposer le hostname interne du conteneur quand `FORWARDED_ALLOW_IPS` n'est pas configure. | Definir `FORWARDED_ALLOW_IPS=*` dans la CI Playwright et tester le `Location` final, pas la chaine de redirection. |
| Rate-limiter in-memory non partage entre processus | Avec `--workers > 1`, les compteurs `RATE_LIMIT_*_MAX` sont par worker -> tests E2E flaky. | Forcer `--workers 1` en test ou assouplir `RATE_LIMIT_AUTH_MAX` / `RATE_LIMIT_API_MAX` dans le workflow CI. |
| `EmailStr` refuse les TLD reserves | Pydantic 2.12 rejette `.test`, `.example`, `.invalid` -> tests d'inscription en echec. | Utiliser `factories.py` avec un domaine reel non resolvable (ex. `example.org`). |

## Commandes

| Commande | Description |
|---|---|
| `cd backend && pytest -q` | Suite backend complete (mode silencieux) |
| `cd backend && pytest -v` | Suite backend verbeuse |
| `cd backend && pytest tests/test_<module>.py -v` | Un seul fichier de test |
| `cd backend && pytest --cov=app --cov-report=html` | Rapport de couverture HTML (`htmlcov/`) |
| `npx playwright test` | Suite E2E Playwright (depuis la racine du repo) |
| `npx playwright test tests/e2e/auth.spec.ts` | Une seule spec Playwright |
| `npx playwright test --ui` | Mode interactif Playwright |
| `cd tests/manual && ./test-all.sh` | Toutes les suites manuelles bash |

## Conventions

- Fixtures pytest centralisees dans `backend/tests/conftest.py`.
- `monkeypatch` pour stubber les dependances externes (SSH, WinRM, LDAP, HTTP, Sentry).
- Repertoires temporaires (`tmp_path`, `tmp_path_factory`) pour les tests de fichiers et de chiffrement.
- **Aucun `async def` sur les services backend** : la couche de service est strictement synchrone (sauf handlers WebSocket dans `api/v1/websocket.py`).
- Donnees de test factorisees dans `backend/tests/factories.py` (utilisateurs, entreprises, agents, audits).
- Tests d'isolation tenant : toujours creer 2 entreprises distinctes et verifier qu'aucune fuite croisee n'est possible.
- Helpers WebSocket : `backend/tests/ws_helpers.py`.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

**Derniere mise a jour :** 2026-05-01

**Declencheurs de mise a jour :**
- Ajout ou retrait d'un module de test backend (`backend/tests/test_*.py`) ou E2E (`tests/e2e/*.spec.ts`).
- Changement de framework de test (pytest, Playwright, Vitest).
- Modification du seuil de couverture cible.
- Ouverture du chantier Vitest frontend.
- Nouveau piege CI documente (workflow `playwright.yml` ou `ci.yml`).

**Verification :**
- [ ] La table "Suites backend" reflete les fichiers presents dans `backend/tests/`.
- [ ] La table "Suites E2E" reflete les specs presentes dans `tests/e2e/`.
- [ ] Les commandes `pytest`, `playwright`, `test-all.sh` s'executent sans erreur.
- [ ] La cible de couverture `>80%` est verifiee via `pytest --cov`.
- [ ] Les pieges connus restent pertinents (sinon, archiver dans la PR de mise a jour).
