# Exigences fonctionnelles — AssistantAudit

**Vision** : Outil interne Ops pour industrialiser les audits de découverte IT — collecte automatisée, analyse de sécurité, conformité, visualisation réseau, suivi de remédiation et génération de rapports détaillés (20–80+ pages).

---

## Module 1 — Gestion des audits

| ID | Exigence |
|----|----------|
| AUD-01 | Créer un audit avec fiche d'intervention : contact client, niveau d'accès, périmètre, type |
| AUD-02 | Supporter les audits récurrents avec comparaison entre sessions |
| AUD-03 | Coordonner des audits multi-sites au sein d'une même campagne |
| AUD-04 | Associer des tags polymorphes à un audit (critical, legacy, quick-win, etc.) |

---

## Module 2 — Checklists terrain

| ID | Checklist | Items |
|----|-----------|-------|
| CHK-01 | LAN (9 sections) | 45 items |
| CHK-02 | Salle serveurs | 38 items |
| CHK-03 | Documentation | 22 items |
| CHK-04 | Protocole de départ | 18 items |

Chaque item supporte les statuts **OK / NOK / NA**, une note libre et la pièce jointe d'une preuve.

---

## Module 3 — Collecte automatisée (agents)

| ID | Domaine collecté |
|----|-----------------|
| COL-01 | Inventaire infrastructure générale |
| COL-02 | Équipements réseau (SNMP / SSH) |
| COL-03 | NAS |
| COL-04 | Cartographie réseau |
| COL-05 | Audit Active Directory (ORADAD) |
| COL-06 | Wi-Fi |
| COL-07 | VPN |
| COL-08 | Règles pare-feu |
| COL-09 | Bande passante |
| COL-10 | Microsoft 365 (Monkey365) |
| COL-11 | Sauvegardes |
| COL-12 | Antivirus / EDR |
| COL-13 | Postes de travail |
| COL-14 | Shadow IT |
| COL-15 | Performances système |
| COL-16 | Audit physique |
| COL-17 | Détection de vulnérabilités (Nmap, SSL checker) |

---

## Module 4 — Référentiels de conformité

| ID | Exigence |
|----|----------|
| REF-01 | Charger 15 référentiels YAML (363 contrôles) au démarrage |
| REF-02 | Vérifier l'intégrité des fichiers par SHA-256 avant synchronisation |
| REF-03 | Versionner chaque référentiel via `ref_id` + `version` |
| REF-04 | Supporter trois moteurs d'évaluation : `manual`, `monkey365`, `collect_ssh` |

---

## Module 5 — Évaluation et scoring

| ID | Exigence |
|----|----------|
| EVA-01 | Organiser les évaluations en campagnes |
| EVA-02 | Enregistrer le résultat de chaque contrôle : `compliant` / `non_compliant` / `partial` / `not_applicable` |
| EVA-03 | Calculer automatiquement le score de conformité pondéré par sévérité |
| EVA-04 | Produire une matrice de risques exportable |

---

## Module 6 — Outils intégrés

| Outil | Usage |
|-------|-------|
| Nmap | Scan réseau et détection de services |
| SSL Checker | Vérification des certificats |
| SSH / WinRM Collector | Collecte de configuration système |
| AD Auditor | Analyse des objets Active Directory |
| Monkey365 | Audit Microsoft 365 / Azure |
| Config Parser | Analyse de fichiers de configuration |
| ORADAD | Collecte AD hors ligne |

---

## Module 7 — Génération de rapports

| ID | Exigence |
|----|----------|
| RAP-01 | Générer un PDF de 20 à 80+ pages structuré en 25 sections |
| RAP-02 | Utiliser Jinja2 comme moteur de templates |
| RAP-03 | Produire le PDF via WeasyPrint |
| RAP-04 | Inclure : page de garde, sections numérotées, matrice de risques, recommandations |

---

## Module 8 — Tags

Système de tagging polymorphe applicable à tout objet (audit, contrôle, équipement) :

`critical` · `legacy` · `quick-win` · `shadow-it` · `unmanaged` · `to-verify` · `compliant` · `non-compliant`

---

## Module 9 — Interface web

| ID | Exigence |
|----|----------|
| IHM-01 | Tableau de bord avec statistiques globales de conformité |
| IHM-02 | Pages CRUD pour audits, checklists, équipements, contrôles |
| IHM-03 | Vue cartographie réseau interactive |
| IHM-04 | Vue baie de serveurs (rack view) |
| IHM-05 | Page d'évaluation des contrôles |
| IHM-06 | Mode sombre |

---

## Module 10 — Agents distants

| ID | Exigence |
|----|----------|
| AGT-01 | Communication temps réel via WebSocket |
| AGT-02 | Flux d'enrôlement des agents (enrollment flow) |
| AGT-03 | Dispatch de tâches vers les agents |
| AGT-04 | Upload d'artefacts de collecte vers le serveur |
| AGT-05 | mTLS pour sécuriser la communication agent ↔ serveur |

---

## Module 11 — Authentification et autorisations

| ID | Exigence |
|----|----------|
| AUTH-01 | Authentification par JWT |
| AUTH-02 | RBAC sur trois niveaux : `admin` > `auditeur` > `lecteur` |
| AUTH-03 | mTLS pour les agents distants |
