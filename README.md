# AssistantAudit

Plateforme d'audit de sécurité IT destinée aux équipes Red Team, auditeurs de conformité et consultants en cybersécurité.

AssistantAudit centralise l'ensemble du cycle d'audit : collecte automatique de données, évaluation de conformité sur des référentiels standards (CIS, ANSSI, ISO 27001, NIS2…), gestion des preuves et reporting — le tout depuis une interface web unique.

---

## Démarrage rapide

```bash
# Cloner et configurer
git clone https://github.com/The-Forge-Hackerspace/AssistantAudit
cd AssistantAudit
cp .env.example .env   # Éditer .env : au minimum définir SECRET_KEY

# Docker (recommandé)
docker compose up -d

# OU démarrage local (Windows)
.\start.ps1 --dev
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

Les identifiants admin sont affichés dans le terminal au premier démarrage.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/project/architecture.md) | Architecture technique, composants, décisions |
| [Stack technique](docs/project/tech_stack.md) | Technologies, versions, dépendances |
| [Exigences](docs/project/requirements.md) | Exigences fonctionnelles et vision produit |
| [Infrastructure](docs/project/infrastructure.md) | Déploiement, Docker, environnements |
| [API](docs/project/api_spec.md) | Spécification API REST |
| [Base de données](docs/project/database_schema.md) | Schéma et modèle de données |
| [Runbook](docs/project/runbook.md) | Guide d'exploitation et installation |
| [Principes](docs/principles.md) | Principes de développement |
| [Tâches](docs/tasks/README.md) | Backlog et gestion des tâches |

---

## Licence

Propriétaire — tous droits réservés.

**Mainteneur :** T0SAGA97
**Dépôt :** https://github.com/The-Forge-Hackerspace/AssistantAudit
