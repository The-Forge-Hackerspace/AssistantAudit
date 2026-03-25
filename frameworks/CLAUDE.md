# Frameworks — Structure et conventions

## Vue d'ensemble

Le dossier `frameworks/` contient 14 fichiers YAML définissant les référentiels d'audit.
Chaque fichier est auto-importé au démarrage du serveur via `framework_service.py` (sync SHA-256).

---

## Inventaire des référentiels

| ref_id | Nom | Engine | Catégories | Contrôles | Actif |
|--------|-----|--------|-----------|-----------|-------|
| `ANSSI-GUIDE-SECURITE-AD` | Guide de sécurité Active Directory (ANSSI) | `manual` | 9 | 29 | ✓ |
| `ANSSI-PA-022` | Recommandations de sécurité relatives à l'AD (ANSSI PA-022) | `manual` | 5 | 18 | ✓ |
| `CIS-AZURE-V3` | CIS Microsoft Azure Foundations Benchmark v3 | `manual` | 6 | 29 | ✓ |
| `CIS-ENTRA-ID-V2` | CIS Microsoft Entra ID Benchmark v2 | `manual` | 5 | 12 | ✓ |
| `CIS-LINUX-V3` | CIS Linux Benchmark v3 | `collect_ssh` | 5 | 27 | ✓ |
| `CIS-M365-V3` | CIS Microsoft 365 Foundations Benchmark v3 | `monkey365` | 12 | 52 | ✓ |
| `CIS-M365-V5` | CIS Microsoft 365 Foundations Benchmark v5 | `monkey365` | 11 | 130 | ✓ |
| `CIS-WINDOWS-SERVER-2022` | CIS Windows Server 2022 Benchmark | `manual` | 7 | 23 | ✓ |
| `DORA` | Digital Operational Resilience Act (DORA) | `manual` | 5 | 14 | ✓ |
| `HADS` | Hébergement de Données de Santé (HADS) | `manual` | 6 | 18 | ✓ |
| `ISO-27001-2022` | ISO/IEC 27001:2022 | `manual` | 4 | 23 | ✓ |
| `NIS2` | Directive NIS2 | `manual` | 6 | 16 | ✓ |
| `PASSI` | Prestataires d'Audit de la Sécurité des SI (PASSI) | `manual` | 4 | 8 | ✓ |
| `SOC2-TYPE2` | SOC 2 Type II | `manual` | 5 | 20 | ✓ |
| `TEST-FRAMEWORK` | Framework de test | `manual` | 2 | 4 | ✓ |

**Total : 363 contrôles, 14 référentiels actifs + 1 framework de test**

---

## Schema YAML complet

### Niveau framework (racine du fichier)

```yaml
ref_id: "CIS-M365-V3"          # Identifiant unique — correspond à l'ID en base
name: "CIS Microsoft 365 ..."  # Nom affiché dans l'UI
version: "3.0.0"               # Version sémantique du référentiel
description: "..."             # Description longue (optionnelle)
engine: "monkey365"            # Voir section Engines ci-dessous
source: ""                     # Sur quel rérentiel on c'est basé pour le framework (CIS, ANSSI,...)
author: ""                     # Créateur du Framework
categories:                    # Liste ordonnée des catégories
  - ...
```

### Niveau catégorie

```yaml
categories:
  - id: "account-management"   # Slug unique dans le framework (pas en base, usage YAML uniquement)
    name: "Gestion des comptes" # Nom affiché
    description: "..."          # Optionnel
    controls:
      - ...
```

### Niveau contrôle — tous les champs

```yaml
controls:
  # Champs TOUJOURS présents (233/233)
  - id: "ctrl-001"                    # Identifiant unique dans le framework
    title: "Titre du contrôle"        # Libellé court affiché
    description: "..."                # Explication détaillée de ce qu'on vérifie
    severity: "high"                  # Voir enum Sévérités
    check_type: "configuration"       # Voir enum Types de contrôle
    remediation: "..."                # Action corrective recommandée

  # Champs optionnels fréquents
    evidence_required: "..."          # 51/233 — description de la preuve à collecter
    cis_reference: "1.2.3"           # 37/233 — numéro CIS (surtout dans les benchmarks CIS)

  # Champs liés à l'automatisation
    auto_check: true                  # 22/233 — indique qu'une vérification auto est possible
    monkey365_rule: "rule-id"         # 17/233 — ID de règle Monkey365 (engine=monkey365 uniquement)
    engine_rule_id: "rule-id"         # Alias de monkey365_rule (même sens, nom alternatif trouvé)
```

---

## Engines (moteurs d'exécution)

| Engine | Frameworks | Comportement |
|--------|-----------|--------------|
| `manual` | 11 | Audit 100% humain — les contrôles sont évalués manuellement par l'auditeur |
| `monkey365` | 1 (`CIS-M365-V3`) | Les contrôles avec `monkey365_rule` sont évalués automatiquement via Monkey365 (PowerShell) |
| `collect_ssh` | 1 (`CIS-LINUX-V3`) | Collecte automatique via SSH sur les serveurs Linux cibles |

---

## Enums

### Sévérités (`severity`)
```
critical | high | medium | low | informational
```

### Types de contrôle (`check_type`)
```
configuration | access_control | audit_logging | patch_management
network_security | data_protection | identity | monitoring
incident_response | business_continuity | compliance | physical_security
```

---

## Pipeline de synchronisation (framework_service.py)

### Démarrage automatique
Au démarrage du serveur (lifespan FastAPI), `sync_from_directory()` est appelé :

1. Lit tous les `*.yaml` dans `frameworks/`
2. Calcule le SHA-256 de chaque fichier
3. Compare avec le hash stocké en base (`Framework.file_hash`)
4. **Si nouveau ou modifié** → `import_from_yaml()` : crée/met à jour le framework et ses contrôles
5. **Si inchangé** → skip (pas de requête SQL inutile)

### Import (`import_from_yaml`)
- Crée ou met à jour le `Framework` (upsert sur `ref_id`)
- Supprime les anciennes `Category` et `Control` liées
- Recrée categories et controls depuis le YAML
- Stocke le `file_hash` pour éviter les re-imports inutiles

### Export (`export_to_yaml`)
- Relit le framework depuis la base et régénère le YAML
- Utilisé quand un auditeur modifie un contrôle via l'UI

### Versioning (`clone_as_new_version`)
- Duplique un framework existant avec un nouveau `version` et un nouveau `ref_id`
- Le YAML cloné est écrit dans `frameworks/`

---

## Ajouter un nouveau référentiel

1. Créer `frameworks/{REF_ID}.yaml` en suivant le schema ci-dessus
2. Redémarrer le backend (ou attendre le prochain démarrage) — le sync est automatique
3. Le framework apparaît dans l'UI sans autre intervention

Contraintes :
- `ref_id` doit être unique et stable (c'est la clé de réconciliation)
- `engine` doit être l'une des trois valeurs connues
- Chaque `control.id` doit être unique au sein du framework
- Pour `engine: monkey365` : renseigner `monkey365_rule` sur les contrôles automatisables

---

## Lien avec les assessments

Les contrôles `engine: monkey365` avec `monkey365_rule` sont automatiquement évalués lors d'un scan Monkey365 :

```
Monkey365ScanResult.results (JSON)
  └─ règle Monkey365 (ex: "azure-storage-default-action-allow")
       └─ correspond à Control.monkey365_rule
            └─ alimente AssessmentControl.status (pass/fail/manual)
```

Pour `engine: manual`, le statut est saisi manuellement par l'auditeur dans l'UI d'assessment.

---

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `frameworks/*.yaml` | Source de vérité — éditer ici, le sync fait le reste |
| `backend/app/services/framework_service.py` | Sync YAML↔DB, CRUD, export, clone |
| `backend/app/models/framework.py` | ORM : `Framework`, `Category`, `Control` |
| `backend/app/schemas/framework.py` | Schémas Pydantic pour l'API |
| `backend/app/api/v1/frameworks.py` | Endpoints REST pour la gestion des frameworks |
