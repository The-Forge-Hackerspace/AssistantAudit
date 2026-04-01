# Schéma base de données

**Total:** 36+ tables · **Migrations Alembic:** 31

---

## Domaines

### Core

| Table | Description |
|-------|-------------|
| `users` | Comptes utilisateurs (rôles: admin, auditeur, lecteur) |
| `entreprises` | Organisations clientes |
| `contacts` | Contacts liés à une entreprise |

### Audit

| Table | Description |
|-------|-------------|
| `audits` | Missions d'audit (lié à une entreprise) |
| `sites` | Sites physiques d'une entreprise |
| `equipements` | Équipements réseau/système (table de base, polymorphique) |

**Sous-types d'équipements** (14, héritage polymorphique via `type` discriminator) :  
`serveurs`, `postes_travail`, `routeurs`, `switchs`, `firewalls`, `aps`,  
`imprimantes`, `cameras`, `nas`, `baies`, `onduleurs`, `phones`, `iot`, `autres`

### Compliance

| Table | Description |
|-------|-------------|
| `frameworks` | Référentiels de conformité (ISO 27001, NIS2, etc.) |
| `framework_categories` | Catégories/domaines d'un référentiel |
| `controls` | Contrôles individuels |
| `assessment_campaigns` | Campagnes d'évaluation liées à un audit |
| `assessments` | Évaluations d'une campagne |
| `control_results` | Résultat par contrôle (conforme / non-conforme / NA) |

### Network

| Table | Description |
|-------|-------------|
| `scans_reseau` | Sessions de scan réseau |
| `scan_hosts` | Hôtes découverts lors d'un scan |
| `scan_ports` | Ports ouverts par hôte |
| `network_links` | Liens réseau entre équipements |
| `network_map_layouts` | Disposition de la carte réseau (JSON) |
| `site_connections` | Connexions inter-sites (WAN, VPN, etc.) |
| `vlan_definitions` | Définitions VLAN |

### Tools

| Table | Description |
|-------|-------------|
| `collect_results` | Résultats de collecte système |
| `config_analysis` | Analyse de configuration |
| `ad_audit_results` | Résultats d'audit Active Directory |
| `monkey365_scan_results` | Résultats Monkey365 (Microsoft 365 / Azure) |
| `oradad_configs` | Configurations ORADAD |

### Agents

| Table | Description |
|-------|-------------|
| `agents` | Agents déployés (token, statut, heartbeat) |
| `agent_tasks` | Tâches assignées à un agent |
| `task_artifacts` | Artefacts soumis par un agent (fichiers, JSON) |

### Autres

| Table | Description |
|-------|-------------|
| `tags` | Étiquettes génériques |
| `tag_associations` | Association tag ↔ entité (polymorphique) |
| `attachments` | Fichiers joints chiffrés |
| `audit_reports` | Métadonnées de rapport PDF |
| `report_sections` | Sections d'un rapport |
| `checklist_templates` | Templates de checklist |
| `checklist_categories` | Catégories dans un template |
| `checklist_items` | Points de vérification |
| `checklist_instances` | Instance de checklist pour un audit |
| `checklist_responses` | Réponses par item |

---

## Relations clés

```
User → Entreprise → Site → Equipement
Audit → AssessmentCampaign → Assessment → ControlResult
Framework → FrameworkCategory → Control
Audit → ScanReseau → ScanHost → ScanPort
Agent → AgentTask → TaskArtifact
```

---

## Chiffrement

| Type | Colonnes concernées | Algorithme |
|------|---------------------|------------|
| `EncryptedText` | `raw_output`, `credentials` | AES-256-GCM |
| `EncryptedJSON` | `parameters`, `scan_data` | AES-256-GCM + JSON sérialisé |

Les clés de chiffrement sont injectées via variables d'environnement (`ENCRYPTION_KEY`, `FILE_ENCRYPTION_KEY`).
