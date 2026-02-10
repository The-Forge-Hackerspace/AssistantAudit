# AssistantAudit — Documentation API v1

> **Base URL** : `http://localhost:8000/api/v1`
> **Swagger UI** : `http://localhost:8000/docs`
> **ReDoc** : `http://localhost:8000/redoc`

---

## Authentification

L'API utilise des **tokens JWT Bearer**. Tous les endpoints (sauf `/health` et `/auth/login`) nécessitent un header :

```text
Authorization: Bearer <access_token>
```

### Obtenir un token

| Méthode | Endpoint | Content-Type |
| --------- | ---------- | ------------- |
| `POST` | `/auth/login` | `application/x-www-form-urlencoded` (OAuth2) |
| `POST` | `/auth/login/json` | `application/json` |

**Formulaire OAuth2** (utilisé par Swagger Authorize) :

```text
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
| -------- | ------------ |
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
| --------- | ------ | -------- | ----- | ----- |
| `page` | `int` | `1` | `1` | — |
| `page_size` | `int` | `20` | `1` | `100` |

---

## Endpoints

### Health

| Méthode | Endpoint | Auth | Description |
| --------- | ---------- | ------ | ------------- |
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
| --------- | ---------- | ------ | ------------- | -------- |
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
| --------- | ---------- | ------ | ------------- | -------- |
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
| --------- | ---------- | ------ | ------------- | -------- |
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

### Sites (`/sites`)

| Méthode | Endpoint | Auth | Description | Status |
| --------- | ---------- | ------ | ------------- | -------- |
| `GET` | `/sites` | Oui | Lister (paginé, filtrable) | 200 |
| `POST` | `/sites` | Oui | Créer un site | 201 |
| `GET` | `/sites/{id}` | Oui | Détail | 200 |
| `PUT` | `/sites/{id}` | Oui | Modifier | 200 |
| `DELETE` | `/sites/{id}` | Oui | Supprimer (cascade équipements) | 200 |

**Filtre** : `GET /sites?entreprise_id=1`

#### `POST /sites`

```json
{
  "nom": "Siège Paris",
  "adresse": "1 rue de Rivoli, 75001 Paris",
  "entreprise_id": 1
}
```

#### `GET /sites/{id}` → `SiteRead`

```json
{
  "id": 1,
  "nom": "Siège Paris",
  "adresse": "1 rue de Rivoli, 75001 Paris",
  "entreprise_id": 1,
  "equipement_count": 3
}
```

**Erreurs** : `404` introuvable, `409` doublon (nom + entreprise).

---

### Équipements (`/equipements`)

| Méthode | Endpoint | Auth | Description | Status |
| --------- | ---------- | ------ | ------------- | -------- |
| `GET` | `/equipements` | Oui | Lister (paginé, filtrable) | 200 |
| `POST` | `/equipements` | Oui | Créer un équipement | 201 |
| `GET` | `/equipements/{id}` | Oui | Détail complet | 200 |
| `PUT` | `/equipements/{id}` | Oui | Modifier | 200 |
| `DELETE` | `/equipements/{id}` | Oui | Supprimer (cascade assessments) | 200 |

**Filtres** : `GET /equipements?site_id=1&type_equipement=firewall&status_audit=A_AUDITER`

**Types** : `reseau`, `serveur`, `firewall`, `equipement`

#### `POST /equipements` (firewall)

```json
{
  "site_id": 1,
  "type_equipement": "firewall",
  "ip_address": "10.0.0.1",
  "hostname": "FW-PARIS-01",
  "fabricant": "Fortinet",
  "os_detected": "FortiOS 7.4.1",
  "license_status": "active",
  "rules_count": 245
}
```

#### `POST /equipements` (serveur)

```json
{
  "site_id": 1,
  "type_equipement": "serveur",
  "ip_address": "10.0.0.10",
  "hostname": "SRV-DC01",
  "fabricant": "Dell",
  "os_detected": "Windows Server 2022",
  "os_version_detail": "21H2 Build 20348.2527",
  "role_list": {"roles": ["AD DS", "DNS", "DHCP"]}
}
```

#### `POST /equipements` (réseau)

```json
{
  "site_id": 1,
  "type_equipement": "reseau",
  "ip_address": "10.0.0.254",
  "hostname": "SW-CORE-01",
  "fabricant": "Cisco",
  "firmware_version": "16.12.4"
}
```

#### `PUT /equipements/{id}`

```json
{
  "status_audit": "EN_COURS",
  "notes_audit": "Audit en cours",
  "hostname": "FW-PARIS-01-v2"
}
```

**Champs spécifiques par type** :

| Type | Champs supplémentaires |
| ------ | ---------------------- |
| `reseau` | `vlan_config`, `ports_status`, `firmware_version` |
| `serveur` | `os_version_detail`, `modele_materiel`, `role_list`, `cpu_ram_info` |
| `firewall` | `license_status`, `vpn_users_count`, `rules_count` |

**Statuts d'audit** : `A_AUDITER` → `EN_COURS` → `CONFORME` / `NON_CONFORME`

**Erreurs** : `404` site/équipement introuvable, `409` doublon IP sur le même site.

---

### Référentiels (`/frameworks`)

| Méthode | Endpoint | Auth | Description | Status |
| --------- | ---------- | ------ | ------------- | -------- |
| `GET` | `/frameworks` | Oui | Lister les référentiels (paginé) | 200 |
| `GET` | `/frameworks/{id}` | Oui | Détail avec catégories et contrôles | 200 |
| `GET` | `/frameworks/{id}/versions` | Oui | Lister toutes les versions d'un référentiel | 200 |
| `POST` | `/frameworks/{id}/clone` | Admin | Cloner en nouvelle version | 201 |
| `GET` | `/frameworks/{id}/export` | Oui | Exporter en fichier YAML | 200 |
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
      "engine_config": null,
      "is_active": true,
      "total_controls": 20,
      "parent_version_id": null
    }
  ],
  "total": 12,
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
| ------------- | ----- | ----------- | -------- |
| `firewall_audit.yaml` | Audit Firewall | 20 | — |
| `switch_audit.yaml` | Audit Switch / Infrastructure Réseau | 18 | — |
| `server_windows_audit.yaml` | Audit Serveur Windows | 15 | — |
| `server_linux_audit.yaml` | Audit Serveur Linux | 16 | — |
| `active_directory_audit.yaml` | Audit Active Directory | 17 | — |
| `m365_audit.yaml` | Audit Microsoft 365 | 18 | `monkey365` |
| `wifi_audit.yaml` | Audit Wi-Fi | 10 | — |
| `sauvegarde_audit.yaml` | Audit Sauvegarde | 18 | — |
| `vpn_audit.yaml` | Audit VPN | 15 | — |
| `dns_dhcp_audit.yaml` | Audit DNS & DHCP | 18 | — |
| `messagerie_audit.yaml` | Audit Messagerie | 17 | — |
| `peripheriques_audit.yaml` | Audit Périphériques | 15 | — |

#### Versioning

Les référentiels supportent le versioning. Cloner un référentiel crée une nouvelle version tout en désactivant l'ancienne.

#### `POST /frameworks/{id}/clone` (Admin)

```json
{
  "new_version": "1.1",
  "new_name": "Audit Firewall (personnalisé)"
}
```

**Réponse** : `FrameworkRead` (201) avec `parent_version_id` pointant vers l'original.

#### `GET /frameworks/{id}/versions`

Retourne la liste de toutes les versions du même `ref_id` (actives et inactives).

#### `GET /frameworks/{id}/export`

Retourne un fichier YAML téléchargeable (`Content-Type: application/x-yaml`).

---

### Évaluations (`/assessments`)

#### Campagnes

| Méthode | Endpoint | Auth | Description | Status |
| --------- | ---------- | ------ | ------------- | -------- |
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
| --------- | ---------- | ------ | ------------- | -------- |
| `POST` | `/assessments?campaign_id=1` | Oui | Créer un assessment | 201 |
| `GET` | `/assessments/{id}` | Oui | Détail avec résultats | 200 |
| `GET` | `/assessments/{id}/score` | Oui | Score de conformité | 200 |
| `GET` | `/assessments/campaigns/{id}/score` | Oui | Score agrégé d'une campagne | 200 |
| `POST` | `/assessments/{id}/scan/m365` | Auditeur | Lancer un scan Monkey365 | 200 |
| `POST` | `/assessments/{id}/scan/simulate` | Auditeur | Simuler un scan M365 (dev/test) | 200 |

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
| --------- | ---------- | ------ | ------------- | -------- |
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
| -------- | ------------ |
| `not_assessed` | Non évalué (défaut) |
| `compliant` | Conforme |
| `non_compliant` | Non conforme |
| `partially_compliant` | Partiellement conforme |
| `not_applicable` | Non applicable |

#### Scoring

##### `GET /assessments/{id}/score`

Retourne le score de conformité d'un assessment :

```json
{
  "assessment_id": 1,
  "total_controls": 20,
  "assessed_controls": 4,
  "compliant": 2,
  "non_compliant": 1,
  "partially_compliant": 1,
  "not_applicable": 0,
  "not_assessed": 16,
  "compliance_score": 62.5
}
```

Le score exclut les contrôles `not_assessed` et `not_applicable` du calcul.
Le `partially_compliant` compte pour 0.5 dans le score.

##### `GET /assessments/campaigns/{id}/score`

Score agrégé de tous les assessments d'une campagne.

#### Scan M365 (Monkey365)

##### `POST /assessments/{id}/scan/m365` (Auditeur)

Lance un scan Monkey365 réel sur un tenant Microsoft 365. L'assessment doit être associé à un framework ayant `engine=monkey365`.

```json
{
  "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_secret": "secret_value",
  "auth_method": "client_credentials",
  "provider": "Microsoft365",
  "plugins": ["sharepoint", "exchange", "teams"]
}
```

**Réponse** (`M365ScanResponse`) :

```json
{
  "scan_id": "uuid",
  "status": "completed",
  "findings_count": 18,
  "mapped_count": 15,
  "unmapped_count": 3,
  "mapping_details": [
    {
      "rule_id": "monkey365-xxx",
      "control_ref": "M365-ID-01",
      "status": "compliant"
    }
  ],
  "manual_controls": ["M365-GOV-01"]
}
```

##### `POST /assessments/{id}/scan/simulate` (Auditeur)

Injecte des résultats fictifs pour tester le mapping sans tenant réel :

```json
{
  "findings": [
    {
      "rule_id": "monkey365-aad-mfa",
      "status": "Fail",
      "description": "MFA non activée"
    }
  ]
}

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
| -------- | ----------- | ------------- |
| Health | 1 | Non |
| Authentification | 5 | Mixte |
| Entreprises | 5 | Utilisateur |
| Audits | 5 | Utilisateur |
| Sites | 5 | Utilisateur |
| Équipements | 5 | Utilisateur |
| Référentiels | 7 | Utilisateur / Admin (clone, import) |
| Évaluations | 12 | Utilisateur / Auditeur (scans) |
| **Total** | **45** | |
