# Schéma de base de données — AssistantAudit

<!-- SCOPE: Inventaire des tables PostgreSQL (et SQLite en dev) du backend AssistantAudit, leurs colonnes-clés, contraintes, relations et migrations majeures. Source de vérité : modèles SQLAlchemy sous `backend/app/models/` et migrations Alembic sous `backend/alembic/versions/`. -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu touches a un modele, une migration ou tu rediges une requete cross-table. -->
<!-- SKIP_WHEN: Tu cherches l'API publique ou la procedure d'exploitation. -->
<!-- PRIMARY_SOURCES: backend/app/models/*.py, backend/alembic/versions/*.py, backend/app/core/encryption.py -->
> **SCOPE :** Inventaire des tables PostgreSQL (et SQLite en dev) du backend AssistantAudit, leurs colonnes-clés, contraintes, relations et migrations majeures. Source de vérité : modèles SQLAlchemy sous `backend/app/models/` et migrations Alembic sous `backend/alembic/versions/`.

| DOC_KIND | DOC_ROLE | READ_WHEN | SKIP_WHEN | PRIMARY_SOURCES |
|----------|----------|-----------|-----------|------------------|
| reference | data-model | tu touches a un modele, une migration ou tu rediges une requete cross-table | tu cherches l'API publique ou la procedure d'exploitation | `backend/app/models/*.py`, `backend/alembic/versions/*.py`, `backend/app/core/encryption.py`, `backend/app/core/database.py` |

## Quick Navigation

- [Vue d'ensemble](#vue-densemble)
- [Conventions](#conventions)
- [Tables par groupe metier](#tables-par-groupe-metier)
- [Relations principales](#relations-principales)
- [Chiffrement des colonnes](#chiffrement-des-colonnes)
- [Migrations significatives](#migrations-significatives)
- [Auto-sync des frameworks YAML](#auto-sync-des-frameworks-yaml)
- [Maintenance](#maintenance)

## Agent Entry

Quand lire ce document : Tu touches a un modele, une migration ou tu rediges une requete cross-table.

Quand l'ignorer : Tu cherches l'API publique ou la procedure d'exploitation.

Sources primaires (auto-discovery) : `backend/app/models/*.py, backend/alembic/versions/*.py, backend/app/core/encryption.py`

## Vue d'ensemble

| Aspect | Choix |
|--------|-------|
| SGBD production | PostgreSQL 16 (`postgres:16-alpine`) |
| SGBD développement | SQLite (`DATABASE_URL=sqlite:///instance/assistantaudit.db` par défaut) |
| ORM | SQLAlchemy 2.0.48 (style `Mapped[...]`) |
| Migrations | Alembic 1.18.4 (`backend/alembic/versions/`) |
| Chiffrement colonnes | `EncryptedJSON` / `EncryptedText` (TypeDecorator) → AES-256-GCM enveloppe KEK + DEK (rotation via `scripts/rotate_kek.py`) |
| Isolation multi-tenant | Colonne `owner_id` (FK `users.id`) sur les ressources auditeur ; admin voit tout |
| Auto-sync | `frameworks/*.yaml` synchronisés vers la table `frameworks` au démarrage |
| Driver prod | `psycopg2-binary >= 2.9` |

## Conventions

| Règle | Détail |
|-------|--------|
| Casse | `snake_case` pour tables et colonnes |
| Clé primaire | `id Integer primary_key autoincrement` |
| Clés étrangères | `<entite>_id Integer ForeignKey('<table>.id')` ; index quand utilisée pour filtrer |
| Timestamps | `created_at DateTime(timezone=True)`, `updated_at DateTime(timezone=True)` (avec `onupdate`) |
| Énumérations | `Enum(PyEnum)` SQLAlchemy ; ex. `AuditStatus`, `FindingStatus` |
| Chiffrement | Champs sensibles → `EncryptedText` ou `EncryptedJSON` (KEK obligatoire en prod) |
| Soft-delete | Pas généralisé ; les agents ont une `revoked_at` (révocation logique) |
| Pas de renommage | Une colonne existante n'est jamais renommée ; on ajoute une nouvelle colonne |

## Tables par groupe métier

### Identité & RBAC

| Table | Colonnes clés | Notes |
|-------|---------------|-------|
| `users` | `id`, `username` (unique, indexé), `email` (unique, indexé), `password_hash`, `full_name`, `role` (admin\|auditeur\|lecteur), `is_active`, `created_at`, `last_login` | bcrypt 5.0 sur `password_hash` |
| `entreprises` | `id`, `nom`, `siret`, `secteur`, `taille`, `owner_id` (FK users) | propriétaire pour l'isolation multi-tenant |
| `sites` | `id`, `nom`, `adresse`, `entreprise_id` (FK), `owner_id` (FK users) | rattaché à une entreprise |
| `equipements` | `id`, `hostname`, `ip_address`, `type`, `os`, `site_id` (FK), `owner_id` (FK) | inventaire technique |

### Audit

| Table | Colonnes clés | Notes |
|-------|---------------|-------|
| `audits` | `id`, `nom_projet`, `status` (Enum `AuditStatus`: NOUVEAU\|EN_COURS\|TERMINE\|ARCHIVE), `date_debut`, `date_fin`, `entreprise_id` (FK), `owner_id` (FK), `lettre_mission_path`, `contrat_path`, `planning_path`, `objectifs/limites/hypotheses/risques_initiaux` (Text), `client_contact_*`, `access_level`, `intervention_window`, `intervention_constraints`, `scope_covered/excluded`, `audit_type` | projet d'audit racine |
| `assessment_campaigns` | `id`, `audit_id` (FK), `framework_id` (FK), `nom`, `status`, `created_at` | campagne d'évaluation = audit × référentiel |
| `assessments` | `id`, `campaign_id` (FK), `equipement_id` (FK), `created_at` | une évaluation par équipement et par campagne |
| `control_results` | `id`, `assessment_id` (FK), `control_id` (FK framework_controls), `score`, `evidence`, `note`, `evaluated_at` | réponse individuelle à un contrôle |
| `frameworks` | `id`, `code` (unique), `nom`, `version`, `source_author`, `auto_synced` | importés depuis `frameworks/*.yaml` au démarrage |
| `framework_chapters` | `id`, `framework_id` (FK), `code`, `titre`, `ordre` | hiérarchie des contrôles |
| `framework_controls` | `id`, `chapter_id` (FK), `ref_id`, `title`, `description`, `severity`, `effort_days` | contrôles unitaires |
| `findings` | `id`, `control_result_id` (FK), `assessment_id` (FK), `equipment_id` (FK), `title`, `description`, `severity` (critical\|high\|medium\|low\|info), `status` (Enum `FindingStatus`: open\|assigned\|in_progress\|remediated\|verified\|closed), `remediation_note` (`EncryptedText`), `assigned_to`, `duplicate_of_id` (FK self), `created_at`, `updated_at`, `created_by` (FK users) | non-conformité avec cycle de vie propre |
| `finding_status_history` | `id`, `finding_id` (FK), `old_status`, `new_status`, `changed_by` (FK users), `comment`, `created_at` | audit trail des transitions |
| `checklists` | `id`, `audit_id` (FK), `type`, `nom`, `status`, `progress_pct` | checklists ANSSI (départ, documentation, LAN, salle serveur) |
| `checklist_items` | `id`, `checklist_id` (FK), `section`, `item`, `response`, `evidence_path`, `comment` | items individuels |
| `anssi_checklist_checkpoints` | `id`, `checklist_id` (FK), `code`, `description`, `status` | points de contrôle ANSSI |
| `vlan_definitions` | `id`, `audit_id` (FK), `vlan_id`, `nom`, `subnet`, `description` | VLANs pour la cartographie |

### Agents & Collecte

| Table | Colonnes clés | Notes |
|-------|---------------|-------|
| `agents` | `id`, `agent_uuid` (unique), `name`, `user_id` (FK), `cert_fingerprint` (SHA-256 unique), `cert_serial`, `cert_expires_at`, `enrollment_token_hash` (SHA-256), `enrollment_token_expires`, `enrollment_used`, `status` (pending\|active\|revoked\|offline), `last_seen`, `last_ip`, `allowed_tools` (JSON), `os_info`, `agent_version`, `revoked_at`, `created_at`, `updated_at` | mTLS X.509 + JWT agent ; révocation logique via `revoked_at` |
| `agent_tasks` | `id`, `agent_id` (FK), `tool` (nmap\|oradad\|ad_collector\|ssh-collect\|winrm-collect\|...), `parameters` (`EncryptedJSON`), `status`, `dispatched_at`, `started_at`, `completed_at`, `error_message` | tâches dispatchées vers les agents |
| `task_artifacts` | `id`, `agent_task_id` (FK), `filename`, `content_type`, `size_bytes`, `storage_path`, `sha256`, `created_at` | binaires uploadés par les agents (≤ 100 MB) |
| `collect_pipelines` | `id`, `audit_id` (FK), `equipement_id` (FK), `protocol` (ssh\|winrm), `credentials` (`EncryptedJSON`), `status`, `created_at` | pipeline de collecte serveur ↔ équipement |
| `collect_results` | `id`, `pipeline_id` (FK), `data` (`EncryptedJSON`), `collected_at`, `agent_id` (FK nullable) | résultat brut + évalué (Linux/Windows/OPNsense evaluators) |
| `config_analyses` | `id`, `equipement_id` (FK), `vendor` (fortinet\|opnsense), `config_text` (`EncryptedText`), `findings` (JSON), `analyzed_at` | parsing des configs réseau |

### Outils spécialisés

| Table | Colonnes clés | Notes |
|-------|---------------|-------|
| `ad_audit_results` | `id`, `audit_id` (FK), `domain`, `findings` (`EncryptedJSON`), `collected_at` | audit AD via LDAP3 |
| `monkey365_scan_results` | `id`, `audit_id` (FK), `auth_method` (interactive\|service_principal\|managed_identity), `archive_path` (`EncryptedText`), `report_data` (`EncryptedJSON`), `started_at`, `completed_at`, `status` | scan M365 via PowerShell 7 |
| `oradad_configs` | `id`, `audit_id` (FK), `explicit_domains` (`EncryptedJSON`), `output_format`, `created_at` | configuration ORADAD (audit AD ANSSI) |

### Network Map & Reporting

| Table | Colonnes clés | Notes |
|-------|---------------|-------|
| `network_map_nodes` | `id`, `audit_id` (FK), `node_type` (site\|equipement), `ref_id`, `position_x`, `position_y`, `metadata` (JSON) | nœuds graphiques (xyflow) |
| `network_map_links` | `id`, `audit_id` (FK), `source_node_id`, `target_node_id`, `link_type`, `vlan_id`, `port_source`, `port_target`, `metadata` (JSON) | liens entre nœuds |
| `reports` | `id`, `audit_id` (FK), `format` (pdf\|docx), `template_version`, `storage_path`, `size_bytes`, `generated_at`, `generated_by` (FK users) | rapports générés (WeasyPrint / python-docx) |
| `attachments` | `id`, `parent_type`, `parent_id`, `filename`, `storage_path`, `content_type`, `size_bytes`, `sha256`, `uploaded_by` (FK users), `created_at` | pièces jointes liées à audits/findings/équipements |
| `tags` | `id`, `name` (unique), `color`, `description` | étiquettes transversales |
| `taggings` | `id`, `tag_id` (FK), `entity_type`, `entity_id` | jonction polymorphe |

## Relations principales

```
users
  └── owner_id ──> entreprises ──> sites ──> equipements
                       │
                       └─> audits ──> assessment_campaigns ──> assessments ──> control_results ──> findings
                                                │                                                     │
                                                └─> framework_id ──> framework_chapters ─> framework_controls
                                                                                                      │
                                                                                            finding_status_history

users ─> agents ─> agent_tasks ─> task_artifacts
                          └─> collect_pipelines ─> collect_results

audits ─> ad_audit_results
       ─> monkey365_scan_results
       ─> oradad_configs
       ─> reports ──> attachments
       ─> network_map_nodes ─┬─> network_map_links
                              └─> vlan_definitions
       ─> checklists ─> checklist_items
                     └─> anssi_checklist_checkpoints

tags <─ taggings ─> (polymorphe : audits, equipements, findings, ...)
```

## Chiffrement des colonnes

`EncryptedJSON` et `EncryptedText` (TypeDecorators dans [`backend/app/core/encryption.py`](../../backend/app/core/encryption.py)) chiffrent à l'écriture / déchiffrent à la lecture. La clé de chiffrement (`ENCRYPTION_KEY`, 32 bytes hex) est obligatoire en prod ; en dev avec valeur vide, le chiffrement est désactivé.

| Modèle | Champ | Type | Raison |
|--------|-------|------|--------|
| `Finding` | `remediation_note` | `EncryptedText` | Note privée auditeur, peut contenir des indicateurs sensibles |
| `AgentTask` | `parameters` | `EncryptedJSON` | Paramètres de tâche (cibles, credentials, options) |
| `CollectPipeline` | `credentials` | `EncryptedJSON` | Identifiants SSH / WinRM |
| `CollectResult` | `data` | `EncryptedJSON` | Inventaire complet d'un poste (services, users, network) |
| `ConfigAnalysis` | `config_text` | `EncryptedText` | Config brute Fortinet / OPNsense |
| `ADAuditResult` | `findings` | `EncryptedJSON` | Résultats AD bruts |
| `Monkey365ScanResult` | `archive_path`, `report_data` | `EncryptedText` / `EncryptedJSON` | Archive M365 + rapport ANSSI |
| `OradadConfig` | `explicit_domains` | `EncryptedJSON` | Domaines AD explicits (config sensible) |

Rotation KEK : voir `backend/scripts/rotate_kek.py` (réécriture des DEKs avec la nouvelle KEK).

## Migrations significatives

Liste indicative (extraite de `backend/alembic/versions/`) — la liste exhaustive est dans le répertoire :

| Migration | Description |
|-----------|-------------|
| `001_add_source_author_to_frameworks` | Provenance d'un référentiel YAML |
| `002_add_network_map_tables` | Cartographie réseau (nodes + links) |
| `006_add_vlan_definitions_table` | Définitions VLAN dans la cartographie |
| `007_add_monkey365_scan_results` | Résultats Monkey365 |
| `008_add_monkey365_archive_path` | Chemin d'archive scan M365 |
| `15396d7282e7_add_anssi_checkpoints_table` | Checklists ANSSI |
| `41f4dca76503_create_tag_tables` | Tags transversaux |
| `43d973779ca0_create_checklist_tables` | Checklists génériques |
| `5fe6333fd834_add_collect_pipeline` | Pipelines de collecte |
| `6e27188411e6_create_agents_and_agent_tasks_tables` | Agents Windows + tâches |
| `0dbf56cd8db3_add_cert_expires_at_to_agents` | Expiration certificat agent |
| `4d902ea37878_add_revoked_at_to_agents` | Révocation logique d'agent |
| `545ae2396390_add_auth_method_to_monkey365_scan_results` | Méthode auth M365 |
| `a11a330219bb_create_report_tables` | Rapports + pièces jointes |
| `add_finding_tables` | Findings + audit trail |
| `c3f7a1b92d04_encrypt_sensitive_json_columns` | Migration vers `EncryptedJSON` |
| `a7f3b2c41d58_oradad_config_encrypted_domains` | Chiffrement domaines ORADAD |
| `add_entreprise_owner_id` + `backfill_owner_id_not_null` | Isolation multi-tenant `owner_id` |
| `b8e4c3d91f02_drop_pingcastle_results_table` | Suppression PingCastle (remplacé par ORADAD) |
| `e9fac305c5bf_add_control_effort_days` | Effort estimé par contrôle |
| `fee3cc8b8c35_add_audit_intervention_fields` | Bloc « Intervention » sur audit |

## Auto-sync des frameworks YAML

Au démarrage du backend (`docker_entrypoint.py` → `init_db.py`), tous les fichiers `frameworks/*.yaml` sont parsés et synchronisés dans la table `frameworks` : nouveaux référentiels créés, contrôles existants mis à jour. Les checklists ANSSI sont seedées via `scripts/seed_anssi_checkpoints.py`.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

| Quand | Action |
|-------|--------|
| Ajout d'un modèle dans `backend/app/models/` | Créer une migration Alembic + ajouter une ligne dans la table du groupe métier concerné |
| Renommage envisagé d'une colonne | **Interdit** — créer une nouvelle colonne, copier les données via migration, déprécier l'ancienne |
| Ajout d'un champ chiffré | Utiliser `EncryptedText` ou `EncryptedJSON` ; documenter dans la table « Chiffrement des colonnes » |
| Modification d'une enum (`AuditStatus`, `FindingStatus`) | Migration explicite (PostgreSQL nécessite `ALTER TYPE ADD VALUE`) ; mettre à jour `VALID_TRANSITIONS` si applicable |
| Rotation de la KEK | Exécuter `python backend/scripts/rotate_kek.py` ; vérifier que toutes les colonnes chiffrées se relisent |

**Vérification :** la liste réelle des tables peut être confirmée via `docker compose exec db psql -U assistantaudit -c '\dt'` ; les migrations appliquées via `cd backend && alembic current`.
