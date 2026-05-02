# Pipeline Quality Trend

Cross-run quality tracker mis à jour par Phase 6 de chaque exécution `ln-1000-pipeline-orchestrator`.

| Date | Story / Epic | Score | Rework | Infra issues | Notes |
|------|--------------|------:|-------:|--------------:|-------|
| 2026-04-01 | TOS-35 (US031 Finding model) | n/a | — | — | Pre-Epic 8 |
| 2026-04-02 | TOS-8 (US004 secrets) | n/a | — | — | Pre-Epic 8 |
| 2026-05-02 | TOS-83 (US050 pytest fix) | manual | n/a | quota subagent (×1) | Manual completion ; smoke 49 passed |
| 2026-05-02 | TOS-74 (US041 BOLA) | 95/100 | 0 | — | PASS fast-track |
| 2026-05-02 | TOS-76 (US043 RFC 5987) | 95/100 | 0 | — | PASS fast-track |
| 2026-05-02 | TOS-77 (US044 rate-limiter) | 92/100 | 0 | — | — |
| 2026-05-02 | TOS-75 (US042 stored XSS) | 88/100 | 0 | — | — |
| 2026-05-02 | TOS-80 (US047 asyncio orphans) | manual | n/a | quota subagent (×1) | Manual finalization + mock fix |
| 2026-05-02 | TOS-79 (US046 graceful shutdown) | 92/100 | 0 | — | — |
| 2026-05-02 | TOS-81 (US048 DB session) | manual | n/a | quota subagent (×1) | Manual finalization, 4 new tests |
| 2026-05-02 | TOS-82 (US049 auth logs) | 88/100 | 0 | — | — |
| 2026-05-02 | TOS-86 (US053 ValueError) | 85/100 | **1** | — | 22 files, 58 migrations ; rework sur 404 contract |
| 2026-05-02 | TOS-87 (US054 RBAC) | 85/100 | 0 | — | ~50 callsites |
| 2026-05-02 | TOS-84 (US051 split agent_service) | 90/100 | **1** | quota subagent (×1, retry OK) | Settings patch scoping ; `_settings()` lazy |
| 2026-05-02 | TOS-85 (US052 split pipeline_service) | 90/100 | 0 | — | `_pkg.get()` late-binding |
| 2026-05-02 | TOS-102 (US055 cluster MEDIUM) | 90/100 | 0 | vulture install KO | 4 sub-commits |

## Trend (Epic 8 batch, 14 stories)

- **Score moyen mesuré** : ~89/100 (sur 11 stories scorées par ln-500 ; 3 stories complétées manuellement non-scorées)
- **Rework cycles** : 2/14 (14%) — toutes recovered en 1 cycle (max 2 autorisés)
- **Infra issues** : 4/14 (29%) — toutes liées au quota Anthropic, pas à l'infra projet
- **Direction** : **stable** sur les stories scorées (85-95/100), pas de dégradation cumulative malgré la branche partagée et les régressions inter-stories possibles

## Observations cross-run

- Les **fast-track PASS** (95/100) sont clusters sur les stories courtes P0 sécurité (TOS-74/76/77/75) où les AC sont précises et les surfaces de fichier petites.
- Les **scores 85-88** sont sur les stories larges (TOS-86 ValueError 22 files, TOS-87 RBAC ~50 callsites, TOS-82 auth logs 7 files) où le scope élargi rend le QA plus prudent.
- Les **refactors god-class** (TOS-84/85) maintiennent 90/100 : la rigueur mécanique du split + tests verts à chaque commit boundary compense la taille (805L+ déplacés).
