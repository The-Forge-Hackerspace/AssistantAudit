# Standards de documentation — AssistantAudit

**Scope:** Tous les fichiers `.md` du projet

---

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
