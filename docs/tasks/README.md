# Gestion des tâches — AssistantAudit

Consolide le contenu de BACKLOG.md, SPRINT-PLAN.md et tech-debt.md (archivés).

---

## Backlog (100 tâches)

| Priorité | Nb | Thèmes principaux |
|---|---|---|
| **P0 — Bloquant** | 0 | — |
| **P1 — Fondation** | ~17 | Checklists, tags, scripts AD, génération rapport, rotation clés, correctifs sécurité |
| **P2 — Fonctionnalité clé** | ~52 | Collecteurs infra, analyse firewall, évaluation M365, RBAC Phase 2, workflow remédiation, mode terrain, IA |
| **P3 — Amélioration** | ~31 | Outils agent, collecteurs, vue rack, pipeline commercial, audits récurrents |

---

## Épiques

| Épique | Plage d'IDs |
|---|---|
| Dette technique | TD-001 → 026 |
| Checklists | CK-001 → 009 |
| Tags | TAG-001 → 005 |
| Inventaire infra | INV-001 → 006 |
| Active Directory | AD-001 → 005 |
| Outils agent | AGT-001 → 005 |
| Firewall | FW-001 → 004 |
| M365 | M365-001 → 003 |
| Rapports | RPT-001 → 013 |
| Synoptiques réseau | NET-001 → 003 |
| Vue rack | RACK-001 → 005 |
| Pipeline commercial | PIP-001 → 003 |
| Audits récurrents | REC-001 → 004 |
| Remédiation | REM-001 → 003 |
| IA hybride | AI-001 → 005 |
| Mode terrain | MOB-001 → 004 |
| RBAC Phase 2 | RBAC-001 → 004 |
| Collecteurs | COL-001 → 008 |

---

## Sprint actuel — Sprint 3

Post Sprint 2 review. Objectifs :
- Rapport PDF sections 5–16
- Script AD complet

---

## Dette technique ouverte

### Critique
- **BUG-S2-001** — Dépendances WeasyPrint manquantes dans le Dockerfile *(résolu sur la branche courante)*

### Élevé
- Migration vers `get_or_404` sur tous les endpoints
- Chaîne FK ownership non vérifiée côté service
- Opérations fichiers sans bloc `try/except`
- Schémas Pydantic : champs `str` à convertir en `Enum`
- Tests manquants sur plusieurs routes P1
- Composant `network-map` bloqué sur équipements 2900L

### Moyen
- CRUD dupliqué (copier-coller entre services)
- Mélange messages FR/EN dans les réponses API
- Pas de rate limiting sur le WebSocket
- Couverture de tests frontend : 0 %

---

## Estimation effort

| Priorité | Effort estimé |
|---|---|
| P1 | ~25 jours |
| P2 | ~115 jours |
| P3 | ~75 jours |
| **Total** | **~215 jours** |

---

## Maintenance

Mettre à jour ce fichier après chaque sprint review.
