# Kanban Board — AssistantAudit

<!-- SCOPE: Tableau Kanban et integration Linear (workspace TOSAGA, Team `TOS`, Epics + User Stories). Ne couvre PAS le workflow de developpement (cf. README.md). -->
<!-- DOC_KIND: how-to -->
<!-- DOC_ROLE: working -->
<!-- READ_WHEN: Tu utilises le board Linear ou tu mets a jour un statut de ticket. -->
<!-- SKIP_WHEN: Tu cherches la spec API ou le schema DB. -->
<!-- PRIMARY_SOURCES: docs/tasks/README.md -->

## Quick Navigation

- [Configuration Linear](#configuration-linear)
- [Statuts](#statuts)
- [Labels](#labels)
- [Projets (Epics)](#projets-epics)
- [User Stories](#user-stories)
- [Maintenance](#maintenance)

Configuration de l'intégration Linear pour le suivi des tâches du projet.

---

## Agent Entry

Quand lire ce document : Tu utilises le board Linear ou tu mets a jour un statut de ticket.

Quand l'ignorer : Tu cherches la spec API ou le schema DB.

Sources primaires (auto-discovery) : `docs/tasks/README.md`

## Configuration Linear

| Paramètre | Valeur |
|-----------|--------|
| Workspace | TOSAGA |
| Team Key | `TOS` (visible dans chaque ID de ticket `TOS-XX`) |
| Team UUID | résolu dynamiquement via Linear MCP `list_teams` (filter `key:TOS`) |
| Prochain numéro Epic | 9 |
| Prochain numéro User Story | US056 |

> **Note** : le Team UUID n'est volontairement pas hardcodé. Tout agent IA connecté à Linear MCP peut le résoudre à la volée à partir du `Team Key`. Cela évite de versionner un identifiant interne tout en gardant le board exploitable par n'importe quel contributeur ayant accès au workspace.

## Statuts

Les UUIDs ci-dessous sont des identifiants techniques Linear (workflow states). Ils sont stables tant que la configuration du workflow ne change pas. Tout agent peut aussi les résoudre via `list_issue_statuses(team:TOS)`.

| Statut | Type | UUID (résolvable via MCP) |
|--------|------|---------------------------|
| Backlog | backlog | `e628c70b-ebac-43f0-84eb-64680b96c635` |
| Todo | unstarted | `8ed7b5cf-ff72-4ff5-adb7-1febcc2084ee` |
| In Progress | started | `1e6fd661-fa30-46ba-b352-f01a212ea21b` |
| In Review | started | `daa6a0b7-82a7-441a-8b43-3303ce4764d5` |
| Done | completed | `7312e891-e2ae-463b-bdcd-d5f51460d41a` |
| Canceled | canceled | `1ad7071e-526e-4c89-b9af-e2e61eed325c` |
| Duplicate | canceled | `747f4896-151b-4d03-8e59-0bce290e340f` |

## Labels

| Label | Couleur | UUID (résolvable via MCP) |
|-------|---------|---------------------------|
| Bug | 🔴 #EB5757 | `f7526e7d-cdb7-4ec8-ad05-a533c1088623` |
| Feature | 🟣 #BB87FC | `8b0d6fd7-0d77-48e1-9105-6afd3bd473bd` |
| Improvement | 🔵 #4EA7FC | `dec4f1d5-45c2-4b3f-a72b-59e1bf0c9a0e` |

## Projets (Epics)

| # | Titre | Statut | Linear |
|---|-------|--------|--------|
| 1 | Infrastructure & DevOps | Planned | [Lien](https://linear.app/tosaga/project/epic-1-infrastructure-and-devops-40e7168b9f4a) |
| 2 | Collecte automatisée & Agents | Planned | [Lien](https://linear.app/tosaga/project/epic-2-collecte-automatisee-and-agents-58055188629d) |
| 3 | Référentiels & Évaluation | Planned | [Lien](https://linear.app/tosaga/project/epic-3-referentiels-and-evaluation-634a705572c4) |
| 4 | Rapports & Livrables | Planned | [Lien](https://linear.app/tosaga/project/epic-4-rapports-and-livrables-0c202869967d) |
| 5 | Interface web & Visualisation | Planned | [Lien](https://linear.app/tosaga/project/epic-5-interface-web-and-visualisation-570bd7e1b3ca) |
| 6 | Remédiation & Suivi | Planned | [Lien](https://linear.app/tosaga/project/epic-6-remediation-and-suivi-02c8f957f243) |
| 7 | IA & Automatisation avancée | Planned | [Lien](https://linear.app/tosaga/project/epic-7-ia-and-automatisation-avancee-7bd4a5bcac86) |
| 8 | Code Quality Upgrade — Audit Remediation | Planned | [Lien](https://linear.app/tosaga/project/epic-8-code-quality-upgrade-audit-remediation-3128fca3696f) |

## User Stories

### Epic 1: Infrastructure & DevOps

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US001 | Pipeline CI/CD complète | P0 Urgent | 13 | Done | [TOS-5](https://linear.app/tosaga/issue/TOS-5/us001-pipeline-cicd-complete) |
| US002 | Durcissement Docker production | P0 Urgent | 8 | Todo | [TOS-6](https://linear.app/tosaga/issue/TOS-6/us002-durcissement-docker-production) |
|       | T001 — Optimiser Dockerfile et .dockerignore | P0 Urgent | — | Todo | [TOS-56](https://linear.app/tosaga/issue/TOS-56/t001-optimiser-dockerfile-et-dockerignore) |
|       | T002 — Ajouter health checks dans docker-compose.yml | P0 Urgent | — | Todo | [TOS-57](https://linear.app/tosaga/issue/TOS-57/t002-ajouter-health-checks-dans-docker-composeyml) |
|       | T003 — Configurer limites CPU/RAM dans docker-compose.yml | P0 Urgent | — | To Review | [TOS-58](https://linear.app/tosaga/issue/TOS-58/t003-configurer-limites-cpuram-dans-docker-composeyml) |
|       | T004 — Intégrer scan Trivy dans workflow CI | P0 Urgent | — | Todo | [TOS-59](https://linear.app/tosaga/issue/TOS-59/t004-integrer-scan-trivy-dans-workflow-ci) |
| US003 | Logging structuré & monitoring | P1 High | 13 | Todo | [TOS-7](https://linear.app/tosaga/issue/TOS-7/us003-logging-structure-and-monitoring) |
| US004 | Gestion centralisée des secrets | P0 Urgent | 8 | Todo | [TOS-8](https://linear.app/tosaga/issue/TOS-8/us004-gestion-centralisee-des-secrets) |
|       | T001 — Hardening validation secrets dans config.py | P0 Urgent | — | Todo | [TOS-61](https://linear.app/tosaga/issue/TOS-61/t001-hardening-validation-secrets-dans-configpy) |
|       | T002 — Script rotation transactionnelle des clés de chiffrement | P0 Urgent | — | Todo | [TOS-62](https://linear.app/tosaga/issue/TOS-62/t002-script-rotation-transactionnelle-des-cles-de-chiffrement) |
|       | T003 — Documentation complète .env.example et secrets | P1 High | — | Todo | [TOS-63](https://linear.app/tosaga/issue/TOS-63/t003-documentation-complete-envexample-et-secrets) |
|       | T004 — Scan secrets dans CI via trufflehog | P1 High | — | Todo | [TOS-64](https://linear.app/tosaga/issue/TOS-64/t004-scan-secrets-dans-ci-via-trufflehog) |
| US005 | Stratégie migration SQLite → PostgreSQL | P2 Medium | 13 | Todo | [TOS-9](https://linear.app/tosaga/issue/TOS-9/us005-strategie-migration-sqlite-vers-postgresql) |
| US006 | Gestion certificats mTLS agents | P3 Low | 13 | Todo | [TOS-10](https://linear.app/tosaga/issue/TOS-10/us006-gestion-certificats-mtls-agents) |
| US007 | Hardening sécurité & rate limiting | P0 Urgent | 8 | Todo | [TOS-11](https://linear.app/tosaga/issue/TOS-11/us007-hardening-securite-and-rate-limiting) |

### Epic 2: Collecte automatisée & Agents

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US008 | Fiabilisation WebSocket agents | P1 High | 13 | Todo | [TOS-12](https://linear.app/tosaga/issue/TOS-12/us008-fiabilisation-websocket-agents) |
| US009 | Pipeline de collecte multi-étapes | P1 High | 13 | Todo | [TOS-13](https://linear.app/tosaga/issue/TOS-13/us009-pipeline-de-collecte-multi-etapes) |
| US010 | Retry et scheduling des tâches agents | P2 Medium | 8 | Todo | [TOS-14](https://linear.app/tosaga/issue/TOS-14/us010-retry-et-scheduling-des-taches-agents) |
| US011 | Auto-prefill évaluation depuis Nmap | P1 High | 8 | Todo | [TOS-15](https://linear.app/tosaga/issue/TOS-15/us011-auto-prefill-evaluation-depuis-nmap) |
| US012 | Sécurisation WinRM et validation certificats | P1 High | 8 | Todo | [TOS-16](https://linear.app/tosaga/issue/TOS-16/us012-securisation-winrm-et-validation-certificats) |
| US013 | Administration agents depuis l'interface | P2 Medium | 13 | Todo | [TOS-17](https://linear.app/tosaga/issue/TOS-17/us013-administration-agents-depuis-linterface) |
| US014 | Intégration Monkey365 bout-en-bout | P2 Medium | 8 | Todo | [TOS-18](https://linear.app/tosaga/issue/TOS-18/us014-integration-monkey365-bout-en-bout) |

### Epic 3: Référentiels & Évaluation

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US015 | Moteur d'évaluation automatique | P1 High | 13 | Todo | [TOS-19](https://linear.app/tosaga/issue/TOS-19/us015-moteur-devaluation-automatique) |
| US016 | Éditeur de référentiels web avancé | P2 Medium | 13 | Todo | [TOS-20](https://linear.app/tosaga/issue/TOS-20/us016-editeur-de-referentiels-web-avance) |
| US017 | Scoring de conformité multi-niveaux | P1 High | 8 | Todo | [TOS-21](https://linear.app/tosaga/issue/TOS-21/us017-scoring-de-conformite-multi-niveaux) |
| US018 | Cohérence YAML-DB bidirectionnelle | P2 Medium | 8 | Todo | [TOS-22](https://linear.app/tosaga/issue/TOS-22/us018-coherence-yaml-db-bidirectionnelle) |
| US019 | Import/export de campagnes d'évaluation | P2 Medium | 8 | Todo | [TOS-23](https://linear.app/tosaga/issue/TOS-23/us019-importexport-de-campagnes-devaluation) |
| US020 | Checklists personnalisées depuis l'interface | P2 Medium | 8 | Todo | [TOS-24](https://linear.app/tosaga/issue/TOS-24/us020-checklists-personnalisees-depuis-linterface) |

### Epic 4: Rapports & Livrables

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US021 | Génération PDF sections 5-8 | P0 Urgent | 13 | Todo | [TOS-25](https://linear.app/tosaga/issue/TOS-25/us021-generation-pdf-sections-5-8) |
| US022 | Matrice de conformité visuelle | P1 High | 8 | Todo | [TOS-26](https://linear.app/tosaga/issue/TOS-26/us022-matrice-de-conformite-visuelle) |
| US023 | Export multi-format des données d'audit | P2 Medium | 8 | Todo | [TOS-27](https://linear.app/tosaga/issue/TOS-27/us023-export-multi-format-des-donnees-daudit) |
| US024 | Personnalisation des rapports PDF | P3 Low | 8 | Todo | [TOS-28](https://linear.app/tosaga/issue/TOS-28/us024-personnalisation-des-rapports-pdf) |
| US025 | Synthèse exécutive automatique | P0 Urgent | 8 | Todo | [TOS-29](https://linear.app/tosaga/issue/TOS-29/us025-synthese-executive-automatique) |

### Epic 5: Interface web & Visualisation

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US026 | Dashboard interactif & drill-down | P1 High | 13 | Todo | [TOS-30](https://linear.app/tosaga/issue/TOS-30/us026-dashboard-interactif-and-drill-down) |
| US027 | Centre de notifications temps réel | P2 Medium | 13 | Todo | [TOS-31](https://linear.app/tosaga/issue/TOS-31/us027-centre-de-notifications-temps-reel) |
| US028 | Recherche globale & filtres avancés | P1 High | 8 | Todo | [TOS-32](https://linear.app/tosaga/issue/TOS-32/us028-recherche-globale-and-filtres-avances) |
| US029 | Accessibilité RGAA & UX mobile | P1 High | 8 | Todo | [TOS-33](https://linear.app/tosaga/issue/TOS-33/us029-accessibilite-rgaa-and-ux-mobile) |
| US030 | Export visualisations & rapports interactifs | P2 Medium | 8 | Todo | [TOS-34](https://linear.app/tosaga/issue/TOS-34/us030-export-visualisations-and-rapports-interactifs) |

### Epic 6: Remédiation & Suivi

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US031 | Modèle Finding & cycle de vie | P0 Urgent | 13 | Done | [TOS-35](https://linear.app/tosaga/issue/TOS-35/us031-modele-finding-and-cycle-de-vie) |
| US032 | Plans de remédiation & actions correctives | P1 High | 13 | Todo | [TOS-36](https://linear.app/tosaga/issue/TOS-36/us032-plans-de-remediation-and-actions-correctives) |
| US033 | Registre des risques & matrice | P1 High | 8 | Todo | [TOS-37](https://linear.app/tosaga/issue/TOS-37/us033-registre-des-risques-and-matrice) |
| US034 | Suivi de conformité & tendances | P1 High | 8 | Todo | [TOS-38](https://linear.app/tosaga/issue/TOS-38/us034-suivi-de-conformite-and-tendances) |
| US035 | Re-audit & comparaison inter-itérations | P2 Medium | 13 | Todo | [TOS-39](https://linear.app/tosaga/issue/TOS-39/us035-re-audit-and-comparaison-inter-iterations) |

### Epic 7: IA & Automatisation avancée

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US036 | Intégration LLM & service IA central | P1 High | 13 | Todo | [TOS-40](https://linear.app/tosaga/issue/TOS-40/us036-integration-llm-and-service-ia-central) |
| US037 | Mapping sémantique des contrôles | P1 High | 13 | Todo | [TOS-41](https://linear.app/tosaga/issue/TOS-41/us037-mapping-semantique-des-controles) |
| US038 | Génération narrative automatique des rapports | P1 High | 8 | Todo | [TOS-42](https://linear.app/tosaga/issue/TOS-42/us038-generation-narrative-automatique-des-rapports) |
| US039 | Guidance de remédiation intelligente | P2 Medium | 8 | Todo | [TOS-43](https://linear.app/tosaga/issue/TOS-43/us039-guidance-de-remediation-intelligente) |
| US040 | Agrégation multi-sources & priorisation des findings | P2 Medium | 13 | Todo | [TOS-44](https://linear.app/tosaga/issue/TOS-44/us040-agregation-multi-sources-and-priorisation-des-findings) |

### Epic 8: Code Quality Upgrade — Audit Remediation

_15 Stories US041..US055 dérivées du rapport ln-620 du 2026-04-30 (créées via `/agile-workflow:ln-220-story-coordinator`)._

| US | Titre | Priorité | Points | Statut | Linear |
|----|-------|----------|--------|--------|--------|
| US041 | Combler la BOLA sur l'upload d'attachments legacy | P0 Urgent | 3 | Backlog | [TOS-74](https://linear.app/tosaga/issue/TOS-74) |
| US042 | Durcir la prévisualisation d'attachments contre le stored XSS | P0 Urgent | 5 | Backlog | [TOS-75](https://linear.app/tosaga/issue/TOS-75) |
| US043 | Sanitiser le filename et le Content-Disposition au téléchargement | P0 Urgent | 3 | Backlog | [TOS-76](https://linear.app/tosaga/issue/TOS-76) |
| US044 | Rate limiter compatible déploiement multi-worker | P0 Urgent | 5 | Backlog | [TOS-77](https://linear.app/tosaga/issue/TOS-77) |
| US045 | Bumper next/postcss pour clore le CVE GHSA-qx2v-qp2m-jg93 | P0 Urgent | 1 | Backlog | [TOS-78](https://linear.app/tosaga/issue/TOS-78) |
| US046 | Graceful shutdown du LocalTaskRunner et du WebSocket manager | P1 High | 8 | Backlog | [TOS-79](https://linear.app/tosaga/issue/TOS-79) |
| US047 | Tracker et annuler les asyncio tasks orphelines | P1 High | 3 | Backlog | [TOS-80](https://linear.app/tosaga/issue/TOS-80) |
| US048 | Découper la session DB long-vie du pipeline en sessions courtes | P1 High | 8 | Backlog | [TOS-81](https://linear.app/tosaga/issue/TOS-81) |
| US049 | Logs auth structurés + scrub PII + reset ContextVar request_id | P1 High | 5 | Backlog | [TOS-82](https://linear.app/tosaga/issue/TOS-82) |
| US050 | Réparer la collection pytest + pyproject.toml [tool.pytest.ini_options] | P1 High | 3 | Backlog | [TOS-83](https://linear.app/tosaga/issue/TOS-83) |
| US051 | Splitter agent_service.py (805 L) en modules Style B | P1 High | 13 | Backlog | [TOS-84](https://linear.app/tosaga/issue/TOS-84) |
| US052 | Splitter pipeline_service.py (795 L) en sous-package pipeline/ | P1 High | 13 | Backlog | [TOS-85](https://linear.app/tosaga/issue/TOS-85) |
| US053 | Migrer ValueError → AppError dans services + nettoyer try/except routers | P2 Medium | 8 | Backlog | [TOS-86](https://linear.app/tosaga/issue/TOS-86) |
| US054 | Centraliser le helper RBAC dans core/deps.py | P2 Medium | 5 | Backlog | [TOS-87](https://linear.app/tosaga/issue/TOS-87) |
| US055 | Cluster MEDIUM: auth hardening + log rotation + Sentry scrub + deps split + dead-code | P3 Low | 13 | Backlog | [TOS-102](https://linear.app/tosaga/issue/TOS-102) |

---

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.

**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.

**Last Updated** : 2026-05-02

Mettre à jour ce fichier :
- Après chaque création d'Epic (projet Linear)
- Après chaque création de User Story (issue Linear)
- Après chaque changement de statut majeur
