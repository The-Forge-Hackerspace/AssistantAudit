# Principes de développement — AssistantAudit

Plateforme d'audit de sécurité informatique (FastAPI backend, Next.js 16 frontend).

---

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
