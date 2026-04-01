# Sprint 1 — Review post-implémentation

**Date de review** : 2026-03-31
**Reviewer** : Claude (planificateur)
**Tests** : 688 passed, 0 failures, 55 warnings (pré-existants)

---

## Statut par tâche

| ID | Titre | Step | Statut | Notes |
|---|---|---|---|---|
| TD-022 | Fix `ScanReseau.owner_id` nullable | 21 | ✅ Complète | `Mapped[int]` + `nullable=False`, migration backfill |
| TD-023 | Authentifier `/metrics` | 21 | ✅ Complète | `Depends(get_current_admin)`, sync `def`, 4 tests auth |
| TD-009 | Backfill `owner_id` nullable (AD audit) | 21 | ✅ Complète | Même migration, NOT NULL enforced |
| TD-020 | Frontend refresh token avant 401 | 22 | ✅ Complète | Pattern mutex + queue, `authApi.refresh()`, `npm run build` OK |
| TD-002 | Implémenter `rotate_kek.py` | 23 | ✅ Complète | CLI argparse, dry-run/--apply, 3 tests crypto |
| TAG-001 | Modèle Tag + TagAssociation | 24 | ✅ Complète | Polymorphe, contraintes unicité, index partiel NULL, 12 tests |
| TAG-002 | Service tags (CRUD, association, filtrage) | 24 | ✅ Complète | 7 méthodes, isolation owner_id via audit |
| TAG-003 | Routes API tags | 25 | ✅ Complète | 7 routes, auth requise, pagination, 9 tests API |
| TAG-004 | Seed tags prédéfinis | 25 | ✅ Complète | 8 tags du brief §5, script idempotent |
| CK-001 | Modèles checklist | 26 | ✅ Complète | 5 tables, contraintes, migration, index partiel NULL, 8 tests |
| CK-002 | Service checklist | 27 | ✅ Complète | 10 méthodes, upsert, progression, isolation audit, 7 tests |
| CK-003 | Routes API checklists | 28 | ✅ Complète | 9 routes, auth, isolation 404, 7 tests API |
| CK-004 | Seed checklist LAN | 28 | ✅ Complète | 9 sections, 45 items (brief §4.2), idempotent |
| TD-025 | Dockerfile + docker-compose | 29 | ✅ Complète | Multi-stage, pwsh/Monkey365, 3 services, entrypoint intelligent |

**Bilan : 14/14 tâches complètes, 0 incomplète, 0 avec écart bloquant.**

---

## Conformité architecture §1.5

| Décision | Respectée | Détail |
|---|---|---|
| Sync first | ✅ | Toutes les routes et services sont `def` (pas `async def`) |
| Colonnes préservées | ✅ | Aucune colonne existante renommée |
| 3 rôles | ✅ | admin/auditeur/lecteur dans les tests |
| ORADAD (pas PingCastle) | ✅ | Aucune référence PingCastle |
| Envelope encryption | ✅ | `rotate_kek.py` utilise `EnvelopeEncryption.rotate_kek()` |
| 404 pas 403 | ✅ | Services checklist et tags retournent 404 si accès refusé |
| owner_id filtré | ✅ | Tags via audit.owner_id, checklists via audit.owner_id |

---

## Critères de succès Sprint 1

| Critère | Statut | Détail |
|---|---|---|
| Aucune faille P0/P1 ouverte | ✅ | TD-022, TD-023, TD-009 résolus. tech-debt #46, #47 fermés |
| API tags fonctionnelle | ✅ | CRUD + association + filtrage + pagination |
| API checklists fonctionnelle | ✅ | Templates + instances + réponses + progression + preuves |
| Checklist LAN prédéfinie | ✅ | 9 sections, 45 items (brief §4.2) |
| `docker-compose up` lance le serveur | ✅ | 3 services (db, backend, frontend), healthcheck, entrypoint intelligent |
| Tous les tests passent | ✅ | 688 passed, 0 failures |

---

## Bugs et écarts trouvés pendant le sprint

### Bugs pré-existants révélés par Docker (step 29)

1. **PRAGMA SQLite-only dans migration 001** — `PRAGMA table_info()` crashait sur PostgreSQL. Corrigé → `sa.inspect().get_columns()`
2. **CORS_ORIGINS format** — pydantic-settings attend `list[str]`, le docker-compose passait une string. Corrigé → format JSON array
3. **Pas de migration initiale** — le projet démarre avec `create_all()` en dev, les migrations sont incrémentales. Corrigé → `docker_entrypoint.py` avec stratégie 3 états

### Ajustements techniques notables

- **Index partiel pour NULL** (steps 24, 26) — SQLite et PostgreSQL traitent NULL différemment dans les contraintes UNIQUE multi-colonnes. Ajout d'index partiels `uix_global_tag_name` et `uix_checklist_instance_no_site` pour couvrir ce cas
- **PaginatedResponse.pages** (step 25) — le champ `pages` était requis par le schema existant mais manquait dans la première implémentation. Corrigé
- **Ordre des routes FastAPI** (step 25) — les routes statiques (`/associate`, `/entity/...`) doivent être déclarées avant la route dynamique `/{tag_id}` pour éviter les conflits de routage

### Aucun nouveau bug ouvert

Pas de fichier créé dans `bugs/open/`.

---

## Warnings pytest (pré-existants, hors sprint)

- **SAWarning polymorphic identity 'serveur'** sur Equipement — factories de test utilisent un type polymorphe non déclaré. Non bloquant, cosmétique
- **PytestReturnNotNoneWarning** sur `test_sentry_connection` — le test retourne un bool au lieu d'assert. Non bloquant
- **DeprecationWarning sentry_sdk.push_scope** — API deprecated dans sentry-sdk v2. Migration à planifier

---

## Dette technique mise à jour

### Éléments résolus par ce sprint

| # | Description | Résolu dans |
|---|---|---|
| 7 | `rotate_kek.py` est un stub | Step 23 |
| 18 | `owner_id` nullable sur scans/ad_audit | Step 21 |
| 44 | Frontend refresh token avant 401 | Step 22 |
| 46 | `ScanReseau.owner_id` nullable | Step 21 |
| 47 | `/metrics` non authentifié | Step 21 |

### Nouvelle dette identifiée

| Description | Priorité | Notes |
|---|---|---|
| Warnings polymorphic identity dans factories | Basse | Cosmétique, ne casse rien |
| `sentry_sdk.push_scope` deprecated | Basse | Migrer vers API v2 |
| 3 bugs Docker corrigés inline | — | Déjà résolus |

---

## Impact sur le Sprint 2

### Dépendances débloquées

- **RPT-001 à RPT-004** (rapport PDF) : le modèle Audit existe avec owner_id, les tags et checklists sont en place pour être intégrés dans le rapport
- **CK-005 à CK-007** (seeds checklists supplémentaires) : le système de templates/sections/items est fonctionnel, le pattern de seed est établi
- **CK-008** (frontend checklist) : l'API est complète et testée, le frontend peut consommer directement
- **TAG-005** (frontend tags) : l'API tags est fonctionnelle avec pagination et filtrage

### Ajustements nécessaires

1. **Docker validé mais non testé en CI** — le Sprint 2 pourra s'appuyer sur Docker pour les tests d'intégration, mais il n'y a pas encore de CI/CD (prévu Sprint 8)
2. **Le frontend build fonctionne** — confirmé par step 22 (`npm run build` OK), le Sprint 2 peut enchaîner sur les composants frontend
3. **Les 45 items de la checklist LAN** sont en base — le Sprint 2 peut les utiliser directement pour le frontend sans re-seed

### Aucun blocage identifié

---

## Recommandation

**Le Sprint 1 est complet. On peut passer au Sprint 2.**

Tous les critères de succès sont remplis, aucun bug ouvert, aucune régression, et les fondations (tags, checklists, Docker, sécurité) sont solides pour construire le rapport PDF et le frontend.
