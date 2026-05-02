# Documentation — AssistantAudit

<!-- SCOPE: Hub central de la documentation AssistantAudit (DAG : projet, reference, taches, tests). -->
<!-- DOC_KIND: index -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu cherches a naviguer dans la documentation projet (DAG des sections). -->
<!-- SKIP_WHEN: Tu cherches une page concrete — utilise les liens directs. -->
<!-- PRIMARY_SOURCES: AGENTS.md, docs/project/architecture.md -->

## Quick Navigation

- [Carte de la documentation](#carte-de-la-documentation)
- [Standards](#standards)
- [Maintenance](#maintenance)

AssistantAudit est une plateforme d'audit de sécurité informatique construite sur FastAPI (backend) et Next.js 16 (frontend).
Ce hub centralise l'ensemble de la documentation du projet.

## Agent Entry

Quand lire ce document : Tu cherches a naviguer dans la documentation projet (DAG des sections).

Quand l'ignorer : Tu cherches une page concrete — utilise les liens directs.

Sources primaires (auto-discovery) : `AGENTS.md, docs/project/architecture.md`

## Carte de la documentation

| Fichier | Description |
|---------|-------------|
| [docs/project/requirements.md](project/requirements.md) | Exigences fonctionnelles |
| [docs/project/architecture.md](project/architecture.md) | Architecture technique |
| [docs/project/tech_stack.md](project/tech_stack.md) | Stack technique et dépendances |
| [docs/project/api_spec.md](project/api_spec.md) | Spécification API REST |
| [docs/project/database_schema.md](project/database_schema.md) | Schéma base de données |
| [docs/project/infrastructure.md](project/infrastructure.md) | Déploiement et Docker |
| [docs/project/runbook.md](project/runbook.md) | Guide d'exploitation |
| [docs/principles.md](principles.md) | Principes de développement |
| [docs/documentation_standards.md](documentation_standards.md) | Standards de documentation |
| [docs/tools_config.md](tools_config.md) | Configuration des outils |
| [docs/reference/](reference/) | ADRs, guides, manuels |
| [docs/tasks/README.md](tasks/README.md) | Backlog et gestion des tâches |

## Standards

Les règles de rédaction, de nommage et de mise à jour de la documentation sont définies dans [docs/documentation_standards.md](documentation_standards.md).
Tout nouveau document doit respecter ces standards avant d'être intégré.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

Mettre à jour ce fichier lors de :
- l'ajout ou la suppression d'un document dans `docs/`
- tout changement de nom ou de localisation d'un fichier référencé
- la création d'une nouvelle section documentaire (ex. nouveau sous-répertoire)
