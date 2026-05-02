
# ADR-003 — Backend FastAPI synchrone par défaut

<!-- SCOPE: Décision d'architecture sur le mode d'exécution du backend FastAPI (synchrone par défaut) — couvre les routes, services, ponts vers du code asynchrone, et les exceptions limitées aux WebSocket -->
<!-- DOC_KIND: record -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu envisages d'ajouter de l'async dans un service ou un router. -->
<!-- SKIP_WHEN: Tu cherches une procedure ops ou la spec d'un endpoint. -->
<!-- PRIMARY_SOURCES: backend/app/api/v1/, backend/app/services/, backend/app/core/event_loop.py -->

## Quick Navigation

- [Statut](#statut)
- [Contexte](#contexte)
- [Décision](#d-cision)
- [Conséquences](#cons-quences)
- [Maintenance](#maintenance)

## Agent Entry

Quand lire ce document : Tu envisages d'ajouter de l'async dans un service ou un router.

Quand l'ignorer : Tu cherches une procedure ops ou la spec d'un endpoint.

Sources primaires (auto-discovery) : `backend/app/api/v1/, backend/app/services/, backend/app/core/event_loop.py`

## Statut

Acceptée (2026-05-01)

## Contexte

FastAPI accepte indifféremment des handlers `def` (synchrones, exécutés dans un threadpool) et `async def` (coroutines exécutées sur la boucle d'événements). Le projet AssistantAudit doit trancher cette question structurante car elle conditionne le style de tous les services, l'écriture des tests, et l'intégration avec SQLAlchemy.

Les caractéristiques de la charge applicative orientent le choix :

- La grande majorité des endpoints sont **DB-bound** (SQLAlchemy 2.0 en mode synchrone, drivers `psycopg2-binary` et `sqlite3` qui sont eux-mêmes bloquants).
- Quelques surfaces sont **réellement asynchrones** par nature : streaming WebSocket des sorties d'agents, push d'événements de collecte, heartbeat — ces flux long-vivants justifient `async def`.
- Les collectes externes (paramiko SSH, pywinrm, ldap3, exécutions PowerShell, WeasyPrint) sont **bloquantes** ou s'exécutent dans des sous-processus — déléguer au threadpool est plus simple que d'inventer des wrappers asynchrones.
- L'équipe est petite, et l'audit régulier (sécurité, tests) bénéficie d'un modèle de raisonnement uniforme : pas de `async`/`await` propagé, pas de risque d'appeler du code bloquant depuis une coroutine.

Trois options ont été pesées :

1. **Tout asynchrone** — cohérent avec la mode FastAPI, mais imposerait `asyncpg`, `httpx async`, des wrappers async pour tous les outils externes, et complexifierait `pytest` (pytest-asyncio sur l'ensemble).
2. **Mixte ad hoc** — laisser chaque endpoint choisir — c'est ce qui produit le plus de bugs (oubli de `await`, blocage de la boucle, fuites de transaction).
3. **Synchrone par défaut, async réservé aux flux nativement asynchrones (retenu)**.

## Décision

Le backend est **strictement synchrone** : routes (`api/v1/`), services (`services/`), accès SQLAlchemy, tests `pytest` n'utilisent **jamais** `async def`. Les seules exceptions autorisées sont les **handlers WebSocket** (et le `WebSocketManager`), où `async def` est imposé par FastAPI.

Pour ponter du code asynchrone tiers depuis le code synchrone, le projet utilise une boucle d'événements applicative dédiée (`core/event_loop.py`) et l'API `asyncio.run_coroutine_threadsafe(coro, app_loop)`. L'appel `asyncio.run(...)` est interdit depuis du code synchrone (il créerait une boucle ad hoc qui interfère avec celle de FastAPI).

L'état request-scoped passe par `contextvars.ContextVar` (compatible threadpool) et jamais par un dict de classe.

## Conséquences

**Positives :**

- Modèle de raisonnement uniforme : pas de question « cette fonction bloque-t-elle la boucle ? » — tout le code applicatif vit dans un thread.
- SQLAlchemy 2.0 en mode synchrone reste le mode le plus mûr et le mieux outillé (alembic, sessions classiques, factories de tests directes).
- Les outils bloquants (paramiko, WeasyPrint, sous-processus PowerShell) s'intègrent sans wrappers : FastAPI exécute chaque requête synchrone dans un thread du pool.
- Tests `pytest` directs, sans `pytest-asyncio` sur la majorité des suites — réduit les sources de flakiness.

**Négatives / contraintes :**

- Capacité de concurrence bornée par la taille du threadpool ; sous très forte charge, il faudra dimensionner workers uvicorn et taille de pool plutôt que la boucle.
- Les contributeurs venant d'écosystèmes 100 % async doivent intérioriser la règle : pas de `async def` sur les services. Documenté dans `docs/principles.md` et `CLAUDE.md`.
- Le pont sync→async est explicite (`asyncio.run_coroutine_threadsafe`) — un peu plus verbeux qu'un `await`, mais sans ambiguïté sur la boucle ciblée.
- Le rate-limiter actuel (`core/rate_limit.py`) est in-memory et donc local au worker — non partagé entre processus uvicorn ; la contrainte est connue (cf. `TESTING_SUMMARY.ci_pitfalls_known`) et acceptée tant que le déploiement reste mono-réplica.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

- **Dernière mise à jour :** 2026-05-01
- **Déclencheurs de mise à jour :** passage à un déploiement multi-réplica nécessitant un store partagé, migration vers SQLAlchemy async, ajout d'un cas async hors WebSocket.
- **Vérification :** `ruff` ne signale pas d'`async def` dans `app/api/v1/*.py` et `app/services/*.py` (hors `websocket*`); `core/event_loop.py` reste l'unique point d'orchestration de la boucle applicative.
