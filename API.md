# AssistantAudit — Documentation API v1

> **Base URL** : `http://localhost:8000/api/v1`
> **Swagger UI** : `http://localhost:8000/docs`
> **ReDoc** : `http://localhost:8000/redoc`

---

## Authentification

L'API utilise des **tokens JWT Bearer**. Tous les endpoints (sauf `/health` et `/auth/login`) nécessitent un header :

```
Authorization: Bearer <access_token>
```

### Obtenir un token

| Méthode | Endpoint | Content-Type |
|---------|----------|-------------|
| `POST` | `/auth/login` | `application/x-www-form-urlencoded` (OAuth2) |
| `POST` | `/auth/login/json` | `application/json` |

**Formulaire OAuth2** (utilisé par Swagger Authorize) :
```
username=admin&password=Admin@2026!
```

**JSON** :
```json
{
  "username": "admin",
  "password": "Admin@2026!"
}
```

**Réponse** (`TokenResponse`) :
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

Les tokens expirent après **60 minutes** (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`).

### Rôles

| Rôle | Description |
|------|------------|
| `admin` | Accès complet, gestion des utilisateurs, import des référentiels |
| `auditeur` | Opérations d'audit, évaluations, scans |
| `lecteur` | Consultation uniquement |

---

## Pagination

Les endpoints de liste retournent une réponse paginée :

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

| Paramètre | Type | Défaut | Min | Max |
|-----------|------|--------|-----|-----|
| `page` | `int` | `1` | `1` | — |
| `page_size` | `int` | `20` | `1` | `100` |

---

## Endpoints

### Health

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| `GET` | `/health` | Non | Vérifie que l'API est opérationnelle |

**Réponse** :
```json
{
  "status": "healthy",
  "service": "AssistantAudit API",
  "version": "2.0.0"
}
```

---

### Authentification (`/auth`)

| Méthode | Endpoint | Auth | Description | Status |
|---------|----------|------|-------------|--------|
| `POST` | `/auth/login` | Non | Login OAuth2 form → JWT | 200 |
| `POST` | `/auth/login/json` | Non | Login JSON body → JWT | 200 |
| `POST` | `/auth/register` | Admin | Créer un utilisateur | 201 |
| `GET` | `/auth/me` | Oui | Profil de l'utilisateur courant | 200 |
| `POST` | `/auth/change-password` | Oui | Changer son mot de passe | 200 |

#### `POST /auth/register`

```json
{
  "username": "jean.dupont",
  "email": "jean@example.com",
  "password": "MotDePasse123!",
  "full_name": "Jean Dupont",
  "role": "auditeur"
}
```

#### `GET /auth/me` → `UserRead`

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@assistantaudit.fr",
  "full_name": "Administrateur",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-02-10T14:30:21",
  "last_login": "2026-02-10T15:24:41"
}
```

#### `POST /auth/change-password`

```json
{
  "current_password": "AncienMDP123!",
  "new_password": "NouveauMDP456!"
}
```

---

### Entreprises (`/entreprises`)

| Méthode | Endpoint | Auth | Description | Status |
|---------|----------|------|-------------|--------|
| `GET` | `/entreprises` | Oui | Lister (paginé) | 200 |
| `POST` | `/entreprises` | Oui | Créer avec contacts | 201 |
| `GET` | `/entreprises/{id}` | Oui | Détail | 200 |
| `PUT` | `/entreprises/{id}` | Oui | Modifier | 200 |
| `DELETE` | `/entreprises/{id}` | Oui | Supprimer | 200 |

#### `POST /entreprises`

```json
{
  "nom": "Acme Corp",
  "adresse": "123 rue de Paris",
  "secteur_activite": "Industrie",
  "siret": "12345678901234",
  "presentation_desc": "Entreprise industrielle",
  "contraintes_reglementaires": "ISO 27001",
  "contacts": [
    {
      "nom": "Marie Martin",
      "role": "RSSI",
      "email": "marie@acme.fr",
      "telephone": "0601020304",
      "is_main_contact": true
    }
  ]
}
```

#### `PUT /entreprises/{id}`

Tous les champs sont optionnels (mise à jour partielle) :

```json
{
  "adresse": "456 avenue de Lyon",
  "secteur_activite": "IT"
}
```

**Erreurs** : `404` introuvable, `409` doublon.

---

### Audits (`/audits`)

| Méthode | Endpoint | Auth | Description | Status |
|---------|----------|------|-------------|--------|
| `GET` | `/audits` | Oui | Lister (paginé, filtrable) | 200 |
| `POST` | `/audits` | Oui | Créer un projet d'audit | 201 |
| `GET` | `/audits/{id}` | Oui | Détail | 200 |
| `PUT` | `/audits/{id}` | Oui | Modifier | 200 |
| `DELETE` | `/audits/{id}` | Oui | Supprimer | 200 |

**Filtre** : `GET /audits?entreprise_id=1`

#### `POST /audits`

```json
{
  "nom_projet": "Audit Sécurité 2026",
  "entreprise_id": 1,
  "objectifs": "Évaluer la posture de sécurité",
  "limites": "Périmètre réseau interne uniquement",
  "hypotheses": "Accès VPN fourni",
  "risques_initiaux": "Aucun"
}
```

#### `PUT /audits/{id}`

```json
{
  "status": "EN_COURS",
  "objectifs": "Objectifs mis à jour"
}
```

**Statuts** : `NOUVEAU` → `EN_COURS` → `TERMINE` → `ARCHIVE`

---

### Référentiels (`/frameworks`)

| Méthode | Endpoint | Auth | Description | Status |
|---------|----------|------|-------------|--------|
| `GET` | `/frameworks` | Oui | Lister les référentiels (paginé) | 200 |
| `GET` | `/frameworks/{id}` | Oui | Détail avec catégories et contrôles | 200 |
| `POST` | `/frameworks/import` | Admin | Importer tous les YAML | 200 |
| `POST` | `/frameworks/import/{filename}` | Admin | Importer un YAML spécifique | 200 |

**Filtre** : `GET /frameworks?active_only=true` (défaut : `true`)

#### `GET /frameworks` → `PaginatedResponse[FrameworkSummary]`

```json
{
  "items": [
    {
      "id": 1,
      "ref_id": "FW",
      "name": "Audit Firewall",
      "version": "1.0",
      "engine": null,
      "is_active": true,
      "total_controls": 20
    }
  ],
  "total": 7,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

#### `GET /frameworks/{id}` → `FrameworkRead`

Retourne le référentiel complet avec ses catégories et contrôles imbriqués :

```json
{
  "id": 1,
  "ref_id": "FW",
  "name": "Audit Firewall",
  "categories": [
    {
      "id": 1,
      "name": "Configuration générale",
      "controls": [
        {
          "id": 1,
          "ref_id": "FW-CFG-01",
          "title": "Vérifier la version du firmware",
          "severity": "high",
          "check_type": "manual",
          "remediation": "Mettre à jour vers la dernière version stable"
        }
      ]
    }
  ],
  "total_controls": 20
}
```

#### Référentiels disponibles

| Fichier YAML | Nom | Contrôles | Engine |
|-------------|-----|-----------|--------|
| `firewall_audit.yaml` | Audit Firewall | 20 | — |
| `switch_audit.yaml` | Audit Switch / Infrastructure Réseau | 18 | — |
| `server_windows_audit.yaml` | Audit Serveur Windows | 15 | — |
| `server_linux_audit.yaml` | Audit Serveur Linux | 16 | — |
| `active_directory_audit.yaml` | Audit Active Directory | 17 | — |
| `m365_audit.yaml` | Audit Microsoft 365 | 18 | `monkey365` |
| `wifi_audit.yaml` | Audit Wi-Fi | 10 | — |

---

### Évaluations (`/assessments`)

#### Campagnes

| Méthode | Endpoint | Auth | Description | Status |
|---------|----------|------|-------------|--------|
| `GET` | `/assessments/campaigns` | Oui | Lister les campagnes (paginé) | 200 |
| `POST` | `/assessments/campaigns` | Oui | Créer une campagne | 201 |
| `GET` | `/assessments/campaigns/{id}` | Oui | Détail avec assessments | 200 |
| `POST` | `/assessments/campaigns/{id}/start` | Oui | Démarrer une campagne | 200 |
| `POST` | `/assessments/campaigns/{id}/complete` | Oui | Terminer une campagne | 200 |

**Filtre** : `GET /assessments/campaigns?audit_id=1`

**Statuts** : `draft` → `in_progress` → `review` → `completed` → `archived`

#### `POST /assessments/campaigns`

```json
{
  "name": "Campagne Q1 2026",
  "description": "Évaluation trimestrielle",
  "audit_id": 1
}
```

#### Assessments

| Méthode | Endpoint | Auth | Description | Status |
|---------|----------|------|-------------|--------|
| `POST` | `/assessments?campaign_id=1` | Oui | Créer un assessment | 201 |
| `GET` | `/assessments/{id}` | Oui | Détail avec résultats | 200 |

#### `POST /assessments?campaign_id=1`

Crée un assessment et génère automatiquement un `ControlResult` par contrôle du framework.

```json
{
  "equipement_id": 1,
  "framework_id": 1,
  "notes": "Firewall principal site Paris"
}
```

#### Résultats de contrôle

| Méthode | Endpoint | Auth | Description | Status |
|---------|----------|------|-------------|--------|
| `PUT` | `/assessments/results/{id}` | Oui | Mettre à jour un résultat | 200 |

#### `PUT /assessments/results/{id}`

```json
{
  "status": "compliant",
  "evidence": "Firmware v7.4.1 vérifié",
  "comment": "Conforme au référentiel",
  "remediation_note": null
}
```

**Statuts de conformité** :
| Valeur | Description |
|--------|------------|
| `not_assessed` | Non évalué (défaut) |
| `compliant` | Conforme |
| `non_compliant` | Non conforme |
| `partially_compliant` | Partiellement conforme |
| `not_applicable` | Non applicable |

---

## Codes d'erreur

| Code | Description |
|------|------------|
| `400` | Requête invalide / erreur métier |
| `401` | Non authentifié / token invalide |
| `403` | Droits insuffisants (admin requis) |
| `404` | Ressource introuvable |
| `409` | Conflit (doublon) |
| `422` | Erreur de validation des données |
| `500` | Erreur serveur |

Format d'erreur :
```json
{
  "detail": "Message d'erreur descriptif"
}
```

---

## Résumé

| Module | Endpoints | Auth requise |
|--------|-----------|-------------|
| Health | 1 | Non |
| Authentification | 5 | Mixte |
| Entreprises | 5 | Utilisateur |
| Audits | 5 | Utilisateur |
| Référentiels | 4 | Utilisateur / Admin (import) |
| Évaluations | 8 | Utilisateur |
| **Total** | **28** | |
