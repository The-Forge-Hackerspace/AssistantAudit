# AssistantAudit — Vision Produit v7

## Le projet en une phrase

AssistantAudit est l'outil interne de l'équipe Ops pour industrialiser les audits de découverte : collecte automatisée, analyse de sécurité, conformité, visualisation réseau, suivi de remédiation, et génération de rapports détaillés (20-80+ pages) — du déploiement de l'agent jusqu'au suivi récurrent.

---

## 1. Pourquoi AssistantAudit ?

Aujourd'hui, un audit de découverte client c'est :
- Des heures à lancer des scripts manuellement sur chaque machine
- Des exports Excel copiés-collés dans un Word
- Des synoptiques réseau dessinés à la main sur Visio
- Un rapport de 20-80 pages qui prend plus de temps à rédiger qu'à collecter les données
- Vérifier les garanties et licences équipement par équipement sur les sites constructeurs
- Des captures d'écran à organiser manuellement dans le bon ordre
- Aucun suivi entre deux audits — on repart de zéro à chaque fois
- Des recommandations classées à la main dans une matrice de risques
- Pas de trace structurée de ce qui a été vérifié sur le terrain

AssistantAudit automatise tout ce qui peut l'être, structure ce qui ne peut pas l'être (checklist terrain, photos), rattache chaque preuve à son contexte, et produit des livrables professionnels détaillés en quelques heures.

---

## 2. Les utilisateurs

Outil **interne** — pas d'accès client.

| Profil | Usage principal |
|---|---|
| **Auditeur / consultant Ops** | Lance les audits, déploie l'agent, remplit les checklists terrain, collecte les preuves, génère les rapports |
| **Auditeur senior / responsable technique** | Supervise les audits, valide les rapports, suit le pipeline, configure les référentiels |
| **Direction / management** | Vue pipeline commercial, historique clients, métriques d'activité |

---

## 3. Architecture globale

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    App Web (self-hosted / interne)                            │
│                                                                              │
│  Dashboard audits · Synoptiques réseau · Vue Rack · Rapports 20-80+p        │
│  Pipeline audits · Suivi remédiation · Référentiels · Checklists terrain     │
│  Contrôle agent · Multi-sites · Historique · Preuves · Mode tablette         │
│  Système de tags · Quick wins · Points forts · Shadow IT                     │
│                                                                              │
│  Backend API (FastAPI + PostgreSQL) · Auth interne (JWT + RBAC + MFA)        │
│  Moteur de référentiels YAML · Moteur de tags · IA hybride (cloud/locale)   │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ HTTPS bidirectionnel
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │ Agent site A│  │ Agent site B│  │ Agent site C│
   │ nmap·ORADAD │  │ nmap·ORADAD │  │ nmap·ORADAD │
   │ Monkey365   │  │ Monkey365   │  │ Monkey365   │
   │ iperf3·PS   │  │ iperf3·PS   │  │ iperf3·PS   │
   └─────────────┘  └─────────────┘  └─────────────┘

   IA hybride : Claude API / OpenAI / Mistral OU Ollama / llama.cpp / vLLM
```

---

## 4. Contexte d'audit & checklist terrain

Avant même de lancer l'agent, l'auditeur remplit les **informations de contexte** de l'audit. Ces informations cadrent l'intervention et alimentent le rapport.

### 4.1 Fiche d'intervention

Remplie à la création de l'audit ou à l'arrivée sur site :
- Nom du client, site / localisation
- Date(s) de l'audit
- Interlocuteur technique côté client (nom, fonction, contact)
- Accès admin fournis : complet / partiel / aucun (détail de ce qui manque)
- Fenêtre d'intervention autorisée (horaires, contraintes)
- Périmètre convenu (ce qui est couvert, ce qui est exclu)
- Type d'audit : découverte initiale / récurrent / ciblé

### 4.2 Checklist terrain LAN

Checklist structurée que l'auditeur remplit sur le terrain, organisée par section. Chaque point peut être coché (OK / NOK / N-A / non vérifié) avec une note libre et des preuves rattachées.

**Architecture réseau globale** :
- Accès internet principal identifié (fibre / xDSL / 4G / satellite / autre)
- Lien de secours présent
- Firewall / routeur identifié
- Switch cœur identifié
- Segmentation réseau présente (VLANs)
- Schéma mental : Internet → Firewall → Core → Accès / Wi-Fi

**Équipements réseau (inventaire rapide)** :
- Pare-feu / routeur : modèle, constructeur, firmware, IP management, accès admin fonctionnel
- Switch cœur : modèle, IP, VLANs trunk, STP/LACP
- Switches d'accès : nombre, VLANs port access, PoE, administration centralisée
- Wi-Fi : contrôleur, AP standalone/managés, SSID internes/invités, séparation Wi-Fi/LAN

**IPAM / VLANs** (pour chaque VLAN) :
- VLAN ID, nom, usage (Users/Servers/WiFi/VoIP/Mgmt)
- Subnet associé, DHCP (où ?), routage inter-VLAN maîtrisé
- Incohérences : VLAN sans subnet, subnet sans VLAN, chevauchements IP, DHCP non documenté

**Services réseau critiques** :
- DHCP : serveur(s), redondance
- DNS : serveur(s), zones, résolution fonctionnelle
- NTP : source de temps configurée
- AD / LDAP : contrôleur(s) de domaine
- Serveurs critiques identifiés (métier, fichiers, messagerie)

**Sécurité (check rapide)** :
- Segmentation : VLAN management isolé, accès admin restreint, flux inter-VLAN filtrés
- Exposition : interfaces d'admin exposées, services obsolètes (SMBv1, Telnet, FTP), accès distant sécurisé (VPN)
- Hygiène : mots de passe partagés, comptes génériques, sauvegarde config réseau

**Performance & disponibilité** :
- Saturation LAN observée
- Boucles réseau suspectes
- SPOF identifiés (single point of failure)
- Supervision existante (outil, couverture)

**Shadow IT** :
- Switches non managés détectés
- Access points personnels (AP sauvages)
- Routeurs 4G non déclarés
- Matériel inconnu sur le LAN
- Tout équipement hors inventaire officiel

**Points forts observés** :
- Architecture claire et documentée
- Segmentation cohérente
- Matériel homogène et à jour
- Bon niveau de sécurité général
- Bonnes pratiques déjà en place (détailler lesquelles)

**Quick wins identifiés** :
- Actions simples à forte valeur, réalisables rapidement
- Exemples types : séparation VLAN management, mise à jour firmware, désactivation services obsolètes, documentation IP/VLAN, activation MFA

### 4.3 Protocole de départ du site

Checklist avant de quitter le client :
- Informations validées avec l'interlocuteur technique
- Zones d'ombre listées (ce qui n'a pas pu être vérifié et pourquoi)
- Prochaines étapes expliquées au client
- Date de restitution planifiée
- Toutes les photos/captures prises et rattachées dans l'outil

---

## 5. Système de tags

Chaque élément de l'audit (équipement, finding, recommandation, point de checklist) peut recevoir un ou plusieurs **tags** pour faciliter le tri, le filtrage et la priorisation.

**Tags prédéfinis** :

| Tag | Couleur | Usage |
|---|---|---|
| `critical` | Rouge | Risque critique, action immédiate nécessaire |
| `legacy` | Orange | Équipement ou logiciel obsolète / fin de vie |
| `quick-win` | Vert | Action simple à forte valeur, réalisable rapidement |
| `shadow-it` | Violet | Équipement ou service non déclaré / hors périmètre officiel |
| `unmanaged` | Gris | Équipement sans administration centralisée |
| `to-verify` | Bleu | Point à vérifier ultérieurement (information manquante) |
| `compliant` | Vert | Conforme aux bonnes pratiques |
| `non-compliant` | Rouge | Non conforme |

**Tags custom** : l'auditeur peut créer ses propres tags par audit ou globalement.

**Filtrage** : dans le dashboard et dans le rapport, filtrage par tag. Ex: "montre-moi tous les quick-wins" ou "tous les équipements shadow-it".

---

## 6. Modules de collecte de l'agent local

### 6.1 Inventaire infrastructure

**Serveurs physiques et virtuels** :
- Hostname, OS (nom + version + build), CPU (modèle, cœurs), RAM, stockage
- Santé hardware : RAID (type, état, hot spare), contrôleur disque, état des disques
- Carte de management (iLO/IPMI/iDRAC) : version firmware, alertes santé, notifications mail configurées et fonctionnelles
- Hyperviseur : type (Hyper-V, VMware, Proxmox), liste des VMs, ressources allouées vs utilisées
- Mises à jour matérielles disponibles (firmware, drivers)
- **Licences et garanties** : numéro de série, modèle, constructeur, statut garantie (en cours/expirée avec date), statut licence OS

**Machines virtuelles** :
- OS, RAM allouée vs consommée, vCPU, disques (taille, type VHDX/VMDK)
- État (en cours d'exécution, arrêtée, suspendue)
- Erreurs event log (erreurs disque, mémoire insuffisante)
- OS obsolètes → finding + tag `legacy`

**Équipements réseau** :
- Switches, routeurs, firewalls via SNMP/SSH
- Détail des ports par switch (numéro, type RJ45/SFP/SFP+, vitesse, statut, VLAN, appareil connecté)
- Tables MAC, ARP, LLDP/CDP pour découverte de topologie
- Version firmware + dernière version disponible
- Garantie constructeur (date début/fin, type de support)
- Stack/IRF : membres, rôle, CPU/mémoire

**NAS (Synology, QNAP, etc.)** :
- Modèle, firmware/DSM, mise à jour disponible
- Stockage : RAID, capacité, utilisation, santé disques
- Réseau : cartes, bonding configuré ou non
- Dossiers partagés et droits d'accès
- Comptes admin et MFA
- Conseiller de sécurité intégré
- Notifications email fonctionnelles

**Cartographie réseau** :
- Subnets, VLANs, plages IP actives
- Plan d'adressage IP (détection automatique)
- Analyse de segmentation (équipements dans le bon VLAN ?)

### 6.2 Active Directory / IAM

**Collecte PowerShell** :
- Domaine : nom NETBIOS, FQDN, niveau fonctionnel domaine/forêt, nombre de DC
- Structure OU complète
- Comptes utilisateurs : total, actifs, désactivés, dernière connexion, date MDP, PasswordNeverExpires, inactifs > 3 mois
- Groupes privilégiés : Domain/Enterprise/Schema Admins — membres
- Politiques MDP : Default Domain Policy + Fine-Grained
- Charte de nommage (détection du pattern)
- DCDIAG : santé du domaine
- GPO : liste complète avec analyse (ex: GPO désactivant le firewall → finding `critical`)
- DNS : zones, enregistrements obsolètes, zones orphelines
- DHCP : étendues, réservations, serveurs autorisés, redondance
- Azure AD Connect / Entra ID : statut sync, OU synchronisées

**Audit ORADAD** : analyse avancée sécurité AD (ANSSI)

### 6.3 Audit Wi-Fi

- Contrôleurs Wi-Fi, bornes/AP : modèle, IP, statut, firmware, mises à jour
- SSID configurés : nom, sécurité (WPA2/WPA3/Open), VLAN
- Clients connectés par borne/SSID
- Bornes hors ligne → finding
- Firmware non à jour → finding

### 6.4 Audit VPN

- Type (SSL, IPsec, WireGuard), liste des utilisateurs, statut, groupes, MFA
- Comptes inutilisés (inactifs > 6 mois) → finding
- Configuration tunnel (split/full tunneling)

### 6.5 Analyse des règles Firewall

- Modèle, firmware, fin de support constructeur
- Licence : expiration, modules activés (IPS, AV, web filtering, sandboxing, SD-WAN monitor)
- Garantie : type, dates
- Règles de filtrage avec analyse :
  - Inutilisées (0 hit) → finding + tag `legacy`
  - Trop permissives (any→any→all) → finding `critical`
  - IPS non activé → finding `critical`
  - Filtrage web non activé → finding
  - Inspection SSL non configurée → finding
- Virtual IPs : obsolètes → finding + tag `legacy`
- Comptes admin : liste, profil, MFA
- Interface admin exposée internet → finding `critical`
- Logs : config journalisation, rétention, cloud logging
- SD-WAN : liens, statut, répartition/failover
- FortiCloud / cloud logging : licence, stockage, rétention

### 6.6 Abonnements internet & débit

- Liens internet : type, opérateur, débit contractuel
- Test de débit par lien (speedtest) : download, upload, latence
- Comparaison mesuré vs contractuel → alerte si écart > 30%
- SD-WAN : mode, état des liens, lien de secours
- Test débit LAN (iperf3)

### 6.7 Audit Microsoft 365

- Monkey365 CLI + parsing JSON
- Tenant, domaines, DNS (SPF, DKIM, DMARC)
- Entra ID : utilisateurs, MFA (statut par compte : enabled/disabled/enforced), conditional access, apps, rôles admin, paramètres de sécurité par défaut
- Exchange Online : boîtes mail, groupes de distribution, contacts, règles de transport, délégations, protocoles legacy, connecteurs d'envoi, antispam, anti-phishing, anti-malware
- SharePoint / OneDrive : sites, permissions, liens anonymes, stockage
- Teams : politiques, guests
- Intune : appareils, conformité
- Licences M365 : types, total/affectées/disponibles
- Secure Score
- Logs de connexion : tentatives échouées, géolocalisation suspecte
- Évaluation automatique via référentiels YAML (CIS M365 v5)

### 6.8 Audit des sauvegardes

- Plan de sauvegarde documenté
- **Sauvegarde locale** (Veeam, Windows Server Backup, etc.) :
  - Version logiciel, mise à jour disponible, licence (type, expiration)
  - Repository : destination, capacité, espace libre
  - Jobs : liste, planification, dernier résultat
  - Versionning : points de restauration par serveur/VM
  - Chiffrement activé, notifications email fonctionnelles
- **Sauvegarde externalisée** (Acronis, Veeam Cloud, etc.) :
  - Statut tâches, stockage cloud, points de restauration
- **Sauvegarde M365** (Active Backup, Veeam for M365, Acronis) :
  - Services sauvegardés, fréquence, rétention, stockage, erreurs
- **Conformité 3-2-1** : 3 copies, 2 supports, 1 hors site → finding si non conforme
- **Tests de restauration** : date dernier test → finding si jamais testé

### 6.9 Audit Antivirus / EDR

- Solution, console (cloud/on-premise)
- Modules activés : antimalware, anti-exploit, IPS réseau, EDR, chiffrement
- Endpoints : total, actifs, inactifs > 6 mois
- Agents manquants vs inventaire → finding par machine non protégée
- Licences, menaces bloquées (30 jours), score de risque
- EDR non activé → finding

### 6.10 Parc informatique (postes)

- Liste postes : hostname, OS, numéro de série, dernier utilisateur
- Antivirus installé par poste → finding si absent
- Agent supervision installé → finding si absent
- OS fin de vie (Windows 10 après oct. 2025) → finding + tag `legacy`
- Recommandation LAPS

### 6.11 Détection Shadow IT

En complément de la checklist terrain, l'agent peut détecter automatiquement :
- Équipements sur le réseau non présents dans l'inventaire DHCP/DNS (scan nmap vs réservations DHCP)
- AP Wi-Fi non enregistrés dans le contrôleur (rogues)
- Appareils avec des services non standard (serveurs web, partages SMB sur des postes utilisateurs)
- Tout équipement détecté en shadow IT reçoit automatiquement le tag `shadow-it`

### 6.12 Performance & disponibilité réseau

- Détection de SPOF (équipement unique sans redondance sur un lien critique)
- Utilisation des ports (saturation sur les uplinks)
- Erreurs de ports (CRC, collisions, drops) via SNMP
- Supervision existante : outil déployé, couverture, alertes configurées

### 6.13 Audit physique — Salle serveur / locaux techniques

**Descriptif des lieux** :
- Localisation géographique, description bâtiments/zones
- Photos aériennes / plans annotés
- Localisation de chaque baie dans les bâtiments

**Inventaire physique des baies** (chaque baie) :
- Localisation (bâtiment, étage, pièce), type (sol 42U, murale 12U, etc.)
- Contenu de haut en bas : tiroir optique, bandeaux, switches, serveurs, NAS, onduleurs, PDU, stockeur vidéo, contrôleur Wi-Fi, routeurs
- Photos avant/arrière

**Onduleurs** (chaque onduleur) :
- Modèle, numéro de série, date fabrication, firmware
- Garantie (date début/fin), état batterie (date remplacement recommandé)
- Autonomie mesurée/estimée, charge actuelle
- Self-test : date du dernier, résultat
- Calibration : date de la dernière
- Agent d'arrêt automatique installé (PowerChute, etc.) et configuration
- Baies sans onduleur → finding

**Grille salle serveur** (scoring par criticité : Basique / Standard / Avancé) :
- Environnement : climatisation, température, humidité
- Alimentation : UPS, autonomie, groupe électrogène
- Sécurité physique : accès, caméras, journal
- Incendie : détection, extinction
- Câblage : organisation, étiquetage
- Redondance : liens, alimentation, clim
- Documentation : plan de salle, procédures

### 6.14 Détection de vulnérabilités

- Ports ouverts et services exposés (nmap)
- OS et logiciels obsolètes / fin de support → tag `legacy`
- Configurations à risque (SMBv1, RDP exposé, comptes par défaut, firewall Windows désactivé par GPO, accès admin sans MFA)
- Résultats ORADAD intégrés
- Benchmarks CIS

### 6.15 Conformité

- ISO 27001 Annexe A, RGPD, NIS2
- Scoring automatique avec recommandations priorisées

### 6.16 Documentation & outils internes (questionnaire auditeur)

- Synoptique réseau existant ? À jour ?
- Outil de gestion de parc / supervision déployé ? Couverture ? Agents manquants ?
- Procédure d'entrée/sortie des collaborateurs formalisée ?
- Charte informatique existante ?
- PRA/PCA documenté ?
- Contrats de maintenance à jour ?

---

## 7. Fonctionnalités de l'app web

### 7.1 Dashboard & gestion des audits
- Vue d'ensemble par client et par audit
- Création d'audits avec fiche d'intervention pré-remplie
- Scoring de risque par catégorie avec indicateurs visuels
- Filtrage par tags sur tous les éléments

### 7.2 Checklists terrain intégrées
- Checklist LAN remplissable dans l'app (mode tablette idéal)
- Chaque point : statut (OK/NOK/N-A/non vérifié) + note libre + preuves
- Checklist salle serveur (scoring par criticité)
- Checklist documentation & outils internes
- Protocole de départ du site
- Les checklists alimentent directement le rapport

### 7.3 Synoptiques réseau
- **Vue simplifiée (client)** : icônes, liens simples, code couleur par zone
- **Vue détaillée (technicien)** : switches avec ports, VLANs, clic détail
- Auto-généré depuis SNMP/LLDP/CDP, éditable ensuite

### 7.4 Vue rack
- Rack configurable, drag & drop, faces avant/arrière, photos
- Export image/PDF
- Auto-suggéré, éditable

### 7.5 Moteur de référentiels YAML
- Chargement et évaluation automatique
- Matrice de conformité par catégorie
- Extensible (référentiels custom)

| Référentiel | Engine | Statut |
|---|---|---|
| CIS M365 v5 (~180 contrôles) | monkey365 | Existant |
| CIS Windows Server | nmap + powershell | À créer |
| ANSSI AD | oradad | À créer |
| Audit salle serveur | questionnaire | À créer |
| Audit sauvegardes (3-2-1) | agent + questionnaire | À créer |
| CIS FortiGate | agent + API | À créer |
| CIS Linux | nmap + ssh | Post-MVP |
| ISO 27001 Annexe A | multi-engine | Post-MVP |

### 7.6 Preuves & pièces jointes
- Photos, captures, documents, notes rattachables à tout élément
- Auto-insertion dans le rapport
- Stockage : filesystem ou S3 compatible (MinIO)

### 7.7 Rapports & livrables

Rapports professionnels de **20 à 80+ pages**.

**Structure type d'un rapport complet** :

1. **Page de garde** (logo consultant, logo client, date, référence, auteur)
2. **Introduction** (remerciements, rappel de disponibilité)
3. **Objectifs de l'audit** (contexte de la demande)
4. **Périmètre de l'audit** (couvert / exclu, type d'audit, fenêtre d'intervention)
5. **Descriptif des lieux** (localisation, plan bâtiments, photos aériennes)
6. **Synoptique réseau** (existant du client + proposé par l'auditeur, par site)
7. **Descriptif des locaux informatiques** (par site : contenu de chaque baie, photos)
8. **Onduleurs** (modèle, garantie, firmware, autonomie, batterie, self-test)
9. **Abonnements internet** (liens, SD-WAN, état, débit)
10. **Plan d'adressage IP** (VLANs, segmentation, recommandations)
11. **Switches** (modèle, garantie, firmware, VLANs)
12. **Wi-Fi** (contrôleur, bornes, SSID, sécurité, mises à jour)
13. **Firewall** (modèle, firmware, licence, garantie, règles, VIPs, comptes admin, IPS, filtrage web, logs, SD-WAN, VPN)
14. **Analyse des serveurs** (physique : hardware, garantie, RAID, iLO ; VMs : détail par VM)
15. **Analyse du NAS** (modèle, DSM, stockage, RAID, réseau, sécurité)
16. **Active Directory** (domaine, comptes, groupes admin, nommage, DCDIAG, OU, GPO, DNS, DHCP, Azure AD Connect)
17. **Sauvegardes** (plan, locale, externalisée, M365, conformité 3-2-1, tests restauration)
18. **Documentation et outils internes** (gestion réseau, parc, utilisateurs, procédures)
19. **Antivirus / EDR** (solution, modules, endpoints, agents manquants, menaces, licences)
20. **Microsoft 365** (sécurité, Entra ID, Exchange, domaines, utilisateurs, licences, admins, MFA, antispam, Secure Score)
21. **Parc informatique** (postes, OS, antivirus, supervision)
22. **Shadow IT** (équipements non déclarés, AP sauvages, matériel inconnu)
23. **Points forts observés** (ce qui est bien fait, bonnes pratiques déjà en place)
24. **Quick wins** (actions simples à forte valeur, réalisables rapidement, avec estimation)
25. **Synthèse globale** — matrice de recommandations classée par :
    - **Catégorie** : environnement & matériel, réseau switches & firewall, serveurs & VMs & NAS, AD/DNS/DHCP, serveur de fichiers, sauvegardes, documentation, antivirus, M365, postes, shadow IT
    - **Niveau de risque** : critique / modéré / mineur / amélioration
    - **Tags** : quick-win, legacy, shadow-it, etc.
    - Chaque recommandation sur une ligne avec son niveau + tags

**Templates** : rapport complet, rapport allégé, rapport conformité.
**Formats** : PDF (brandable) et Word (éditable).
**Preuves** : auto-insérées aux bons endroits.

### 7.8 Pipeline commercial & chiffrage
- Dashboard pipeline audits
- Historique par client avec évolution scoring
- Chiffrage remédiation en j/h par catégorie (barèmes configurables)
- Les quick wins sont mis en avant avec leur estimation

### 7.9 Audits récurrents & évolution
- Planification récurrente
- Comparaison automatique avec audit précédent : nouveaux findings, résolus, persistants
- Timeline de maturité
- Alertes proactives (garanties, certificats, licences)

### 7.10 Workflow de remédiation
- Assignation interne, suivi (nouveau → recommandé → en cours → corrigé → re-vérifié)
- Commentaires et preuves avant/après
- Dashboard remédiation avec progression
- Les quick wins peuvent être marqués "fait" rapidement

### 7.11 Multi-sites
- Un agent par site, vue consolidée, comparaison entre sites
- Synoptiques et racks par site
- Rapport consolidé ou par site
- Checklists terrain par site

### 7.12 Intelligence artificielle — Hybride cloud/local

**Cloud** : Claude API, OpenAI, Mistral, tout compatible OpenAI API.
**Local** : Ollama, llama.cpp, vLLM.

**Usages** :
- Résumé exécutif auto-généré
- Suggestions de remédiation contextualisées
- Scoring de risque pondéré par contexte métier
- Détection d'anomalies
- Assistance rédaction rapport
- Identification automatique des quick wins depuis les findings
- **Fallback** : tout fonctionne sans IA

### 7.13 Contrôle agent à distance
- Lancer/arrêter des modules de collecte
- Modifier la configuration
- Logs et statut en temps réel
- Mise à jour agent + outils
- Mode CLI local toujours disponible

### 7.14 Mode terrain (tablette / mobile)
- Interface responsive tablette
- Checklists terrain tactiles (LAN, salle serveur, documentation, départ)
- Prise de photos rattachées au contexte
- Mode offline avec sync au retour en ligne
- Scan QR/code-barres (numéro de série, asset tag)
- Saisie rapide des informations d'intervention

---

## 8. Agent local — Outils embarqués

| Outil | Usage | Intégration |
|---|---|---|
| **nmap** | Scan ports, découverte réseau, détection OS, shadow IT | Binaire embarqué, CLI |
| **ORADAD** | Audit AD avancé (ANSSI) | Binaire embarqué, export JSON/HTML |
| **Monkey365** | Audit M365 (CIS benchmark) | Module PowerShell, CLI |
| **iperf3** | Test débit LAN | Binaire embarqué |
| **speedtest-cli** | Test débit internet | Module Python |

Vérification au démarrage. Mode air-gapped disponible (export fichier chiffré).

---

## 9. Stack technique

| Composant | Technologie |
|---|---|
| Frontend | React / Next.js / TypeScript / Tailwind / shadcn/ui |
| Backend API | Python / FastAPI / SQLAlchemy / Alembic |
| Base de données | PostgreSQL + Redis |
| Stockage fichiers | Filesystem local ou S3 compatible (MinIO) |
| Agent local | Python + PowerShell + outils embarqués |
| Auth | JWT + RBAC + MFA (interne) |
| Visualisation | React Flow ou D3.js (synoptiques) + dnd-kit (rack) |
| Rapports | WeasyPrint ou ReportLab (PDF) + python-docx (Word) |
| IA cloud | Claude API / OpenAI / Mistral |
| IA locale | Ollama / llama.cpp / vLLM |
| Conteneurisation | Docker / Docker Compose |
| CI/CD | GitHub Actions |

---

## 10. Ce qui rend AssistantAudit différent

1. **Tout-en-un** : de la checklist terrain au rapport 80+ pages avec matrice de risques
2. **Agent embarqué** : un installeur, tout inclus (nmap, ORADAD, Monkey365)
3. **Checklists terrain structurées** : fini les notes sur un carnet, tout est tracé et alimenté dans le rapport
4. **Synoptiques vivants** : pas un Visio statique, une vue interactive depuis les vraies données
5. **Système de tags** : critical, legacy, quick-win, shadow-it — classification transversale de tout l'audit
6. **Quick wins identifiés** : les actions simples à forte valeur sont mises en avant pour le client
7. **Points forts documentés** : pas que du négatif, on valorise aussi ce qui est bien fait
8. **Shadow IT détecté** : comparaison automatique inventaire officiel vs réalité réseau
9. **Référentiels extensibles** : YAML ouvert, CIS/ANSSI + custom
10. **Suivi dans le temps** : évolution mesurable audit après audit
11. **Chiffrage intégré** : findings → proposition j/h
12. **Preuves rattachées** : chaque constat documenté, intégré au rapport
13. **Licences & garanties** : vue consolidée avec alertes d'expiration
14. **IA hybride** : cloud ou locale, fonctionne aussi sans
15. **Mode terrain** : tablette, photos, offline, checklists tactiles

---

## 11. Contraintes techniques

- Agent compatible Windows Server 2016+ et Windows 10/11
- Mode air-gapped (export fichier chiffré)
- Données sensibles ne quittent jamais le réseau client
- IA locale possible pour environnements sans accès cloud
- Synoptiques performants jusqu'à 500 équipements / 2000 ports
- Vue rack jusqu'à 20 baies par site
- Référentiels YAML extensibles
- Rapports brandables de 20-80+ pages
- Stockage preuves : filesystem ou S3 compatible
- API avec rate limiting et logging d'audit
- Tests unitaires sur chaque module

---

## 12. Definition of Done

Un module est considéré terminé quand :
- Le code passe tous les tests unitaires
- La review de code est validée par le Dev Architect
- Le QA Tester a vérifié le fonctionnement en conditions réalistes
- L'IT Security a validé qu'aucune donnée sensible ne fuit
- Le Head of Quality a donné le feu vert
- La documentation est à jour
