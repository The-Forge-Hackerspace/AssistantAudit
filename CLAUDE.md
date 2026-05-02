
# CLAUDE.md — Stub d'import pour Claude Code

<!-- SCOPE: Stub harness Claude Code qui délègue à `AGENTS.md` (SSOT canonique) ; ne couvre que les particularités de l'agent Claude Code, pas les conventions projet. -->
<!-- DOC_KIND: index -->
<!-- DOC_ROLE: derived -->
<!-- READ_WHEN: Demarrage d'une session Claude Code dans ce depot. -->
<!-- SKIP_WHEN: Tu cherches la doc canonique des conventions — voir AGENTS.md. -->
<!-- PRIMARY_SOURCES: AGENTS.md -->

## Quick Navigation

- [Claude Code](#claude-code)
- [Maintenance](#maintenance)

> **SCOPE :** Stub harness Claude Code qui délègue à `AGENTS.md` (SSOT canonique) ; ne couvre que les particularités de l'agent Claude Code, pas les conventions projet.

@AGENTS.md

Ce fichier est un *stub* dérivé : il importe automatiquement `AGENTS.md` (la source unique de vérité pour les conventions, l'architecture et les anti-patterns du projet `AssistantAudit`). Toute modification des règles projet doit être faite dans `AGENTS.md`, **jamais ici**.

## Agent Entry

Quand lire ce document : Demarrage d'une session Claude Code dans ce depot.

Quand l'ignorer : Tu cherches la doc canonique des conventions — voir AGENTS.md.

Sources primaires (auto-discovery) : `AGENTS.md`

## Claude Code

Particularités du harness Claude Code (à ne pas dupliquer ailleurs) :

- Commandes session utiles : `/compact` (compaction), `/memory show` (mémoire courante), `/clear`.
- Mémoire utilisateur persistante : `~/.claude/projects/-home-tosaga-DEV-AssistantAudit/memory/`.
- Règles à charger à la demande : `.claude/rules/*.md` avec entête `paths:` (frontmatter) — utile pour des règles spécifiques à un sous-dossier.
- Pour les hooks, permissions et MCP, se référer à `.claude/settings.json` (ou settings utilisateur) — ne pas modifier sans validation.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

Mettre à jour ce fichier uniquement lors de :

- l'introduction d'une fonctionnalité spécifique au harness Claude Code (nouvelle commande slash, nouveau hook, nouveau format de mémoire) ;
- la modification du chemin de mémoire projet ;
- l'ajout d'un répertoire `.claude/rules/` distinct.

Vérification : ce fichier doit rester ≤ 50 lignes et contenir exactement une ligne `@AGENTS.md`. Toute règle projet ajoutée ici par erreur doit être déplacée vers `AGENTS.md`.
