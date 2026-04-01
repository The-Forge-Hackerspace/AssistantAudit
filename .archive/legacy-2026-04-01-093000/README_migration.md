# Migration Legacy Documentation — 2026-04-01

## Résumé

Migration des documents legacy vers la structure standardisée `docs/`.

## Fichiers migrés

| Original | Cible | Action |
|----------|-------|--------|
| `CONCEPT.md` | `docs/project/architecture.md`, `docs/project/requirements.md` | Contenu extrait puis fichier supprimé |
| `README.md` | `docs/project/tech_stack.md`, `docs/project/runbook.md` | Sections migrées remplacées par liens |
| `docs/PROJECT-BRIEF-v7-final.md` | `docs/project/requirements.md` | Contenu extrait puis fichier supprimé |
| `docs/BACKLOG.md` | `docs/tasks/README.md` | Contenu extrait puis fichier supprimé |
| `docs/SPRINT-PLAN.md` | `docs/tasks/README.md` | Contenu extrait puis fichier supprimé |
| `docs/SPRINT-1-REVIEW.md` | — | Archivé uniquement |
| `docs/SPRINT-2-REVIEW.md` | — | Archivé uniquement |
| `docs/AUDIT-ETAT-DES-LIEUX.md` | `docs/project/architecture.md` | Contenu extrait puis fichier supprimé |
| `docs/tech-debt.md` | `docs/tasks/README.md` | Contenu extrait puis fichier supprimé |

## Rollback

Pour restaurer les fichiers originaux :

```bash
cp .archive/legacy-2026-04-01-093000/original/CONCEPT.md ./
cp .archive/legacy-2026-04-01-093000/original/README.md ./
cp .archive/legacy-2026-04-01-093000/original/docs/* ./docs/
```
