# Documentation de référence

<!-- SCOPE: Hub des references AssistantAudit : ADRs, guides, manuels, recherches. -->
<!-- DOC_KIND: index -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu cherches une decision architecturale (ADR), un guide ou un manuel d'utilisation interne. -->
<!-- SKIP_WHEN: Tu cherches la documentation projet primaire (docs/project/). -->
<!-- PRIMARY_SOURCES: docs/reference/adrs/, docs/reference/guides/, docs/reference/manuals/ -->

## Quick Navigation

- [Structure](#structure)
- [Format ADR](#format-adr)
- [Maintenance](#maintenance)

Ce répertoire contient les documents de référence du projet : décisions architecturales (ADRs), guides techniques, manuels et recherches.

## Agent Entry

Quand lire ce document : Tu cherches une decision architecturale (ADR), un guide ou un manuel d'utilisation interne.

Quand l'ignorer : Tu cherches la documentation projet primaire (docs/project/).

Sources primaires (auto-discovery) : `docs/reference/adrs/, docs/reference/guides/, docs/reference/manuals/`

## Structure

| Répertoire | Contenu | Quand créer |
|------------|---------|-------------|
| adrs/ | Architecture Decision Records | Lors d'une décision technique structurante |
| guides/ | Guides techniques | Pour documenter une procédure complexe |
| manuals/ | Manuels utilisateur | Pour documenter l'utilisation d'une fonctionnalité |
| research/ | Notes de recherche | Pour consigner une investigation technique |

## Format ADR

Les ADRs suivent la convention de nommage `ADR-NNN-titre.md` et contiennent les sections suivantes :

- **Contexte** : situation et problème qui motivent la décision
- **Décision** : choix retenu et justification
- **Conséquences** : impacts positifs et négatifs du choix
- **Statut** : Proposée / Acceptée / Dépréciée / Remplacée (avec date)

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

Mettre à jour ce README quand un nouveau document est ajouté dans l'un des sous-répertoires.
