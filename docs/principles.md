# Principes de développement — AssistantAudit

<!-- SCOPE: Principes de developpement AssistantAudit : langage FR/EN, backend sync, layered architecture, anti-patterns NEVER. -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Avant de toucher au code (backend ou frontend) ou de proposer une architecture. -->
<!-- SKIP_WHEN: Tu cherches un endpoint API ou une procedure ops. -->
<!-- PRIMARY_SOURCES: AGENTS.md, docs/project/architecture.md -->

## Quick Navigation

- [1. Architecture](#1-architecture)
- [2. Sécurité](#2-s-curit)
- [3. Code](#3-code)
- [4. Frontend](#4-frontend)
- [5. Base de données](#5-base-de-donn-es)
- [6. Tests](#6-tests)
- [7. Workflow](#7-workflow)
- [8. Anti-patterns (NEVER)](#8-anti-patterns-never)
- [9 — Convention services](#9-convention-services)

Plateforme d'audit de sécurité informatique (FastAPI backend, Next.js 16 frontend).

---

## Agent Entry

Quand lire ce document : Avant de toucher au code (backend ou frontend) ou de proposer une architecture.

Quand l'ignorer : Tu cherches un endpoint API ou une procedure ops.

Sources primaires (auto-discovery) : `AGENTS.md, docs/project/architecture.md`

## 1. Architecture

Flux obligatoire : **Router → Service → Model**

- Les routes (`api/v1/`) reçoivent les requêtes et délèguent aux services.
- Les services (`services/`) contiennent toute la logique métier et sont la seule couche qui interroge la base de données.
- Les modèles (`models/`) définissent les entités SQLAlchemy.
- Les schémas (`schemas/`) gèrent la sérialisation Pydantic (entrée/sortie).
- Pas d'accès direct à la base de données dans les routes.

## 2. Sécurité

- **Authentification** : JWT (access + refresh tokens), RBAC à trois niveaux — `admin > auditeur > lecteur`.
- **Chiffrement au repos** : AES-256-GCM via TypeDecorators `EncryptedText` / `EncryptedJSON`.
- **Mots de passe** : bcrypt, jamais stockés en clair.
- **Agents** : mTLS pour l'authentification mutuelle, tokens d'enrollment validés via SHA-256 + `hmac.compare_digest`.
- **Subprocess** : jamais `shell=True`.
- **Secrets** : jamais hardcodés — toujours via variables d'environnement (`.env`).

## 3. Code

- **Langue** : textes UI, commentaires et docstrings en **français** ; identifiants, variables et noms de fonctions en **anglais**.
- **TypeScript** : interdit d'utiliser `as any` ou `@ts-ignore`.
- **Colonnes DB** : ne jamais renommer une colonne existante — ajouter une nouvelle colonne à la place.
- **Backend** : synchrone par défaut (`def`, pas `async def`) sauf handlers WebSocket.

## 4. Frontend

- **Stack** : Next.js 16 App Router, React 19, Tailwind CSS v4, shadcn/ui v4.
- **Données** : SWR pour le data fetching côté client.
- **HTTP** : Axios avec intercepteur JWT (refresh automatique).
- **Thème** : support du mode sombre obligatoire.

## 5. Base de données

- **ORM** : SQLAlchemy 2, sessions synchrones.
- **Migrations** : Alembic (`alembic revision --autogenerate`, `alembic upgrade head`).
- **Environnements** : PostgreSQL en production, SQLite en développement.
- **Données sensibles** : colonnes chiffrées via `EncryptedText` / `EncryptedJSON`.

## 6. Tests

- **Backend** : pytest (688+ tests). Lancer après chaque modification.
- **Frontend E2E** : Playwright.
- Commande : `cd backend && pytest -q`

## 7. Workflow

- Committer après chaque étape complète.
- Format des commits : `feat` / `fix` / `test` / `refactor` / `security` / `chore` / `docs`.
- Ordre préféré : backend → frontend.
- Toujours vérifier les tests avant de passer à l'étape suivante.

## 8. Anti-patterns (NEVER)

| Règle | Raison |
|-------|--------|
| Ne jamais committer `.env` | Fuite de secrets |
| Ne jamais utiliser `shell=True` | Injection de commandes |
| Ne jamais utiliser `async def` sur les routes/services | Architecture synchrone |
| Ne jamais renommer une colonne DB existante | Rupture de migration |
| Ne jamais utiliser `as any` ou `@ts-ignore` | Sécurité du typage TypeScript |
| Ne jamais hardcoder des secrets | Exposition dans le dépôt |

## 9 — Convention services

**Pattern retenu : fonctions module (Style B)**

Les services sont des modules Python avec des fonctions de premier niveau,
pas des classes avec méthodes statiques.

✅ Correct :
  # services/agent_service.py
  def get_agent(db, agent_id: int) -> Agent:
      ...

❌ Interdit :
  class AgentService:
      @staticmethod
      def get_agent(db, agent_id: int) -> Agent:
          ...

Raison : moins de boilerplate, plus pythonique, cohérent avec collect_service.py et pipeline_service.py.
La migration des services existants se fait progressivement lors des splits de god classe

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.

**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.

**Last Updated** : 2026-05-01
