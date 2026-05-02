# Standards de documentation — AssistantAudit

<!-- SCOPE: Standards de documentation : structure SCOPE/Maintenance, NO_CODE rule, formats prioritaires (tables/ASCII/links), liens internes. -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu rediges ou revises un document du depot. -->
<!-- SKIP_WHEN: Tu cherches une procedure ou un schema applicatif. -->
<!-- PRIMARY_SOURCES: AGENTS.md, docs/principles.md -->

## Quick Navigation

- [1. Langue](#1-langue)
- [2. Format](#2-format)
- [3. Structure](#3-structure)
- [4. Nommage des fichiers](#4-nommage-des-fichiers)
- [5. Liens](#5-liens)
- [6. Maintenance](#6-maintenance)
- [7. Messages de commit](#7-messages-de-commit)

**Scope:** Tous les fichiers `.md` du projet

---

## Agent Entry

Quand lire ce document : Tu rediges ou revises un document du depot.

Quand l'ignorer : Tu cherches une procedure ou un schema applicatif.

Sources primaires (auto-discovery) : `AGENTS.md, docs/principles.md`

## 1. Langue

- Documentation rédigée en français
- Termes techniques (noms de fonctions, routes API, types, etc.) conservés en anglais

## 2. Format

- Markdown uniquement
- Tables pour les données structurées (mappings, conventions, références)
- Pas de blocs de code dépassant 5 lignes — pointer vers le fichier source à la place

## 3. Structure

Chaque document doit contenir :

| Section | Contenu |
|---|---|
| Titre | Nom descriptif du document |
| Scope | Périmètre couvert (ex: `backend`, `frontend`, `global`) |
| Sections de contenu | Corps du document |
| Maintenance | Déclencheurs de mise à jour |

## 4. Nommage des fichiers

- Format : `snake_case.md`
- Titre descriptif, pas d'abréviations ambiguës
- Exemples : `documentation_standards.md`, `api_conventions.md`

## 5. Liens

- Liens relatifs entre documents (`../docs/autre_doc.md`)
- Source canonique unique — pas de duplication de contenu
- Si une information existe ailleurs, lier plutôt que copier

## 6. Maintenance

Chaque document précise ses déclencheurs de mise à jour, par exemple :

- Ajout ou suppression d'une convention
- Changement d'architecture ou de stack
- Nouveau type de fichier introduit dans le projet

## 7. Messages de commit

Format : `type(scope): description`

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `test` | Ajout ou modification de tests |
| `refactor` | Refactorisation sans changement de comportement |
| `security` | Correctif de sécurité |
| `chore` | Tâche de maintenance (dépendances, config) |
| `docs` | Documentation uniquement |

---

**Maintenance :** Mettre à jour lors de l'introduction d'un nouveau type de document, d'un changement de convention de nommage, ou d'une modification du workflow de commit.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.

**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.

**Last Updated** : 2026-05-01
