# Spécification API REST

**Base URL:** `/api/v1`  
**Auth:** JWT Bearer token — obtenu via `POST /api/v1/auth/login` (OAuth2 password form)  
**Rôles:** `admin` · `auditeur` · `lecteur`

---

## Endpoints par ressource

### Auth

| Méthode | Chemin | Description |
|---------|--------|-------------|
| POST | `/auth/login` | Connexion — retourne access_token + refresh_token |
| POST | `/auth/register` | Création de compte (admin uniquement) |
| POST | `/auth/refresh` | Renouvellement du token via refresh_token |
| PUT | `/auth/change-password` | Modification du mot de passe courant |
| GET | `/auth/profile` | Profil de l'utilisateur connecté |

### Users

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/users` | Liste des utilisateurs |
| POST | `/users` | Créer un utilisateur |
| GET | `/users/{id}` | Détail d'un utilisateur |
| PUT | `/users/{id}` | Modifier un utilisateur |
| DELETE | `/users/{id}` | Supprimer un utilisateur |

### Entreprises

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/entreprises` | Liste des entreprises |
| POST | `/entreprises` | Créer une entreprise |
| GET | `/entreprises/{id}` | Détail d'une entreprise |
| PUT | `/entreprises/{id}` | Modifier une entreprise |
| DELETE | `/entreprises/{id}` | Supprimer une entreprise |
| GET | `/entreprises/{id}/contacts` | Contacts d'une entreprise |
| POST | `/entreprises/{id}/contacts` | Ajouter un contact |

### Audits

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/audits` | Liste des audits |
| POST | `/audits` | Créer un audit |
| GET | `/audits/{id}` | Détail d'un audit |
| PUT | `/audits/{id}` | Modifier un audit (complet) |
| PATCH | `/audits/{id}` | Modifier un audit (partiel) |
| DELETE | `/audits/{id}` | Supprimer un audit |

### Sites

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/sites` | Liste des sites |
| POST | `/sites` | Créer un site |
| GET | `/sites/{id}` | Détail d'un site |
| PUT | `/sites/{id}` | Modifier un site |
| DELETE | `/sites/{id}` | Supprimer un site |

### Equipements

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/equipements` | Liste des équipements |
| POST | `/equipements` | Créer un équipement |
| GET | `/equipements/{id}` | Détail d'un équipement |
| PUT | `/equipements/{id}` | Modifier un équipement |
| DELETE | `/equipements/{id}` | Supprimer un équipement |
| GET | `/equipements/{id}/network-links` | Liens réseau d'un équipement |

### Frameworks

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/frameworks` | Liste des référentiels |
| POST | `/frameworks` | Créer un référentiel |
| GET | `/frameworks/{id}` | Détail d'un référentiel |
| PUT | `/frameworks/{id}` | Modifier un référentiel |
| DELETE | `/frameworks/{id}` | Supprimer un référentiel |
| POST | `/frameworks/load-yaml` | Charger un référentiel depuis YAML |
| GET | `/frameworks/{id}/versions` | Historique des versions |

### Campaigns

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/campaigns` | Liste des campagnes |
| POST | `/campaigns` | Créer une campagne |
| GET | `/campaigns/{id}` | Détail d'une campagne |
| PUT | `/campaigns/{id}` | Modifier une campagne |
| DELETE | `/campaigns/{id}` | Supprimer une campagne |
| POST | `/campaigns/{id}/start` | Démarrer une campagne |
| GET | `/campaigns/{id}/scoring` | Score de conformité |

### Assessments

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/assessments` | Liste des évaluations |
| POST | `/assessments` | Créer une évaluation |
| GET | `/assessments/{id}` | Détail d'une évaluation |
| PUT | `/assessments/{id}` | Modifier une évaluation |
| GET | `/assessments/{id}/results` | Résultats détaillés |
| POST | `/assessments/{id}/m365/simulate` | Simuler un scan M365 |

### Scans

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/scans` | Liste des scans réseau |
| POST | `/scans` | Créer un scan |
| GET | `/scans/{id}` | Détail d'un scan |
| PUT | `/scans/{id}` | Modifier un scan |
| DELETE | `/scans/{id}` | Supprimer un scan |
| POST | `/scans/{id}/nmap` | Lancer un scan Nmap |
| GET | `/scans/{id}/hosts` | Hôtes découverts |
| POST | `/scans/{id}/export` | Exporter les résultats |

### Network Map

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/network-map/{audit_id}` | Carte réseau d'un audit |
| PUT | `/network-map/{audit_id}/layout` | Sauvegarder la disposition |
| GET | `/network-map/{audit_id}/connections` | Connexions inter-sites |
| POST | `/network-map/{audit_id}/connections` | Ajouter une connexion |

### Attachments

| Méthode | Chemin | Description |
|---------|--------|-------------|
| POST | `/attachments` | Uploader un fichier |
| GET | `/attachments/{id}/download` | Télécharger un fichier |
| DELETE | `/attachments/{id}` | Supprimer un fichier |

### Tags

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/tags` | Liste des tags |
| POST | `/tags` | Créer un tag |
| PUT | `/tags/{id}` | Modifier un tag |
| DELETE | `/tags/{id}` | Supprimer un tag |
| POST | `/tags/associate` | Associer/dissocier un tag |

### Checklists

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/checklists/templates` | Templates de checklists |
| POST | `/checklists/instances` | Créer une instance |
| GET | `/checklists/instances/{id}` | Détail d'une instance |
| PUT | `/checklists/instances/{id}/responses` | Enregistrer les réponses |
| DELETE | `/checklists/instances/{id}` | Supprimer une instance |

### Reports

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/reports` | Liste des rapports |
| POST | `/reports/generate` | Générer un rapport PDF |
| GET | `/reports/{id}/download` | Télécharger un rapport |
| DELETE | `/reports/{id}` | Supprimer un rapport |

### Agents

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/agents` | Liste des agents |
| POST | `/agents` | Enregistrer un agent |
| GET | `/agents/{id}` | Détail d'un agent |
| PUT | `/agents/{id}` | Modifier un agent |
| DELETE | `/agents/{id}` | Supprimer un agent |
| POST | `/agents/enroll` | Enrôlement initial d'un agent |
| POST | `/agents/{id}/heartbeat` | Heartbeat de l'agent |
| GET | `/agents/{id}/tasks` | Tâches en attente |
| POST | `/agents/{id}/tasks` | Créer une tâche |
| GET | `/agents/tasks/{task_id}` | Détail d'une tâche |
| PUT | `/agents/tasks/{task_id}` | Mettre à jour une tâche |
| POST | `/agents/tasks/{task_id}/artifacts` | Soumettre un artefact |

### WebSocket

| Chemin | Description |
|--------|-------------|
| `/ws/agent` | Canal temps réel agent ↔ serveur (tâches, résultats) |

### Monitoring

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/health` | État de l'application |
| GET | `/ready` | Readiness check |
| GET | `/liveness` | Liveness check |
| GET | `/metrics` | Métriques (admin uniquement) |
