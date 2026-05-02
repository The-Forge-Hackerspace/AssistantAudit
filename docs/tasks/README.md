
# Gestion des taches — AssistantAudit

<!-- SCOPE: Workflow et regles de gestion des taches AssistantAudit (commits conventionnels, tests, diff, integration Linear TOS). Ne couvre PAS le contenu du backlog (cf. kanban_board.md). -->
<!-- DOC_KIND: index -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu demarres un cycle de taches Linear ou tu prepares un PR. -->
<!-- SKIP_WHEN: Tu cherches l'architecture ou le runbook. -->
<!-- PRIMARY_SOURCES: docs/tasks/kanban_board.md, docs/tasks/reports/ -->

## Quick Navigation

- [Workflow developpement](#workflow-developpement)
- [Integration Linear](#integration-linear)
- [Definition of Done par categorie](#definition-of-done-par-categorie)
- [Archive de pipeline](#archive-de-pipeline)
- [Maintenance](#maintenance)

Reference unique pour le workflow developpement, l'integration Linear (prefixe `TOS`) et la Definition of Done par categorie de tache. Le suivi operationnel des Epics et User Stories est dans `kanban_board.md`.

---

## Agent Entry

Quand lire ce document : Tu demarres un cycle de taches Linear ou tu prepares un PR.

Quand l'ignorer : Tu cherches l'architecture ou le runbook.

Sources primaires (auto-discovery) : `docs/tasks/kanban_board.md, docs/tasks/reports/`

## Workflow developpement

A appliquer apres chaque modification de code, configuration ou documentation.

| Etape | Action |
|-------|--------|
| 1. Plan | Lier la tache a une issue Linear `TOS-XX`. Verifier la presence d'un User Story parent ou d'un Epic dans `kanban_board.md`. |
| 2. Implementation | Editer le code. Respecter les regles de `docs/principles.md` (sync only, pas d'`async def` hors WebSocket, pas de `db.query` dans `api/v1/`). |
| 3. Tests | Lancer `pytest -q` cote backend. Verifier les tests Playwright si la story touche le frontend. Toute modification doit etre couverte ou justifiee. |
| 4. Lint et types | Backend : `ruff` ; frontend : `npm run lint`, `npm run type-check`. Aucun `as any`, aucun `@ts-ignore`. |
| 5. Diff summary | Presenter un resume du diff (fichiers, intentions, breaking changes) avant de passer a la prochaine etape. |
| 6. Commit | Format conventionnel : `feat`, `fix`, `test`, `refactor`, `security`, `chore`, `docs`. Inclure la reference Linear `TOS-XX` dans le message si la tache existe. |
| 7. Push et PR | Pousser sur une branche dediee, ouvrir une PR avec lien vers l'issue Linear et resume des tests executes. |

Regles de nommage commit (extrait `CLAUDE.md` racine) :
- `feat(scope): ...` pour une nouvelle capacite metier.
- `fix(scope): ...` pour un bug regression.
- `security(scope): ...` pour une remediation securite.
- `refactor(scope): ...` pour une restructuration sans changement de comportement.
- `test(scope): ...` pour ajout ou correctif de tests.
- `chore(scope): ...` pour outillage, deps, configs non fonctionnelles.
- `docs(scope): ...` pour documentation pure.

---

## Integration Linear

Le projet utilise Linear comme source de verite operationnelle. Le prefixe d'equipe est `TOS` et chaque issue est referencee sous la forme `TOS-XX`.

| Element | Valeur |
|---------|--------|
| Workspace Linear | TOSAGA |
| Prefixe d'equipe | `TOS` |
| Mapping fichier | `kanban_board.md` (Epics + User Stories) |
| Format de reference | `TOS-XX` (ex. `TOS-25`, `TOS-35`, `TOS-8`) |

Statuts utilises (definis dans `kanban_board.md`) :

| Statut Linear | Usage cote dev |
|---------------|----------------|
| Backlog | Idee triee mais pas encore prete a etre prise. |
| Todo | Tache prete a etre prise au prochain sprint. |
| In Progress | Code en cours d'ecriture sur la branche. |
| In Review | PR ouverte, en attente de relecture. |
| Done | PR mergee, tests passants en CI. |
| Canceled | Tache abandonnee (motiver dans Linear). |

Labels suggeres (a aligner avec la taxonomie Linear) :

| Label | Usage |
|-------|-------|
| `story` | User Story de niveau US, decomposable en taches. |
| `bug` | Defaut visible sur l'environnement courant. |
| `security` | Vulnerabilite, remediation cryptographique, RBAC, secrets. |
| `devops` | CI/CD, Docker, Alembic, scripts d'orchestration. |
| `infra` | Sujets reseau, agents Windows, environnements dev/pre-prod. |
| `tests` | Tache dont le livrable principal est une suite de tests. |

Note : si l'integration Linear MCP doit etre utilisee depuis Claude (`mcp__linear-server__*`), fournir l'URL du workspace, l'API key et le team UUID dans la configuration de l'agent. Les valeurs courantes sont consignees dans `kanban_board.md` (`Team ID`, `Team Key`).

---

## Definition of Done par categorie

Chaque tache doit cocher l'integralite des cases de sa categorie avant de passer en `Done`.

| Categorie | Definition of Done |
|-----------|--------------------|
| `feat` (fonctionnalite) | Code livre, schema Pydantic + service + endpoint cohrents, migration Alembic generee si DB, tests unitaires et integration verts, documentation utilisateur ou API mise a jour, diff summary partage en PR. |
| `fix` (bug) | Reproduction du bug ecrite en test (regression), correctif minimal, suite complete `pytest -q` verte, mention du symptome et de la cause racine en PR. |
| `security` | Modele de menace mis a jour si necessaire, secret scan vert, test couvrant le scenario d'attaque, revue par un binome, pas de regression sur les flux RBAC ni le chiffrement (KEK+DEK). |
| `refactor` | Comportement inchange (tests existants verts), aucun renommage de colonne DB, scope du refactor delimite dans la PR, complexite ou nombre de god classes diminue. |
| `test` | Tests deterministes, isoles (pas de partage d'etat global), s'inserent dans `backend/tests/` ou `tests/e2e/`, run cible documente dans la PR. |
| `chore` | Justifie en PR (outillage, deps, configs), build CI vert (`ci.yml`, `secret-scan.yml`, `playwright.yml` si touche au front), pas de churn cosmetique non motive. |
| `docs` | Markdown avec balise `SCOPE` en tete, section `Maintenance` en pied, liens internes valides, pas de duplication d'information existante. |

---

## Archive de pipeline

Les rapports d'execution de pipelines de stories sont archives dans `reports/` :
- `reports/pipeline-2026-04-01-TOS-35.md` — execution liee a `TOS-35` (Modele Finding et cycle de vie).
- `reports/pipeline-2026-04-02-TOS-8.md` — execution liee a `TOS-8` (Gestion centralisee des secrets).

Conserver ces rapports tels quels (audit trail). Ajouter un nouveau fichier par execution majeure.

---

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

A mettre a jour quand :
- le format des commits ou les regles de revue changent ;
- la taxonomie de labels Linear evolue ;
- la liste des statuts est modifiee dans Linear ;
- un nouveau type de tache (categorie) doit avoir une Definition of Done.

Derniere mise a jour : 2026-05-01.
