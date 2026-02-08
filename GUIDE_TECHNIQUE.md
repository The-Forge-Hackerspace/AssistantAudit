# Guide Technique - AssistantAudit

## 📋 Architecture de l'application

### Structure des fichiers

```
AssistantAudit/
├── app/
│   ├── __init__.py          # Factory de l'application Flask
│   ├── models.py            # Modèles SQLAlchemy (Entreprise, Contact, Audit, Site, Équipements)
│   ├── routes.py            # Blueprint avec toutes les routes
│   └── templates/           # Templates Jinja2 avec Bootstrap 5
│       ├── base.html        # Template de base
│       ├── index.html       # Page d'accueil
│       ├── nouveau_projet.html              # Formulaire wizard 3 étapes
│       ├── audit_detail.html                # Vue détail audit
│       ├── ajouter_site.html                # Formulaire ajout site
│       ├── liste_entreprises.html           # Liste entreprises
│       ├── entreprise_detail.html           # Détails entreprise
│       ├── liste_equipements.html           # Liste équipements d'un site
│       ├── detail_equipement.html           # Détails d'un équipement
│       ├── auditer_equipement.html          # Formulaire audit d'équipement
│       ├── liste_scans.html                 # Historique des scans
│       └── detail_scan.html                 # Détails d'un scan
├── uploads/                 # Dossier des fichiers uploadés
├── instance/                # Base de données SQLite
│   └── assistantaudit.db
├── run.py                   # Point d'entrée
├── init_db.py              # Script d'initialisation avec données de test
├── test_routes.py          # Script de test des routes
└── requirements.txt        # Dépendances Python
```

## 🔧 Routes et Fonctionnalités

### Routes principales

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Page d'accueil avec statistiques et liste des audits |
| `/nouveau-projet` | GET, POST | Formulaire wizard création projet d'audit |
| `/audit/<id>` | GET | Vue détail d'un audit (tableaux de bord) |
| `/audit/<id>/ajouter-site` | GET, POST | Formulaire d'ajout de site |
| `/audit/<id>/changer-status/<status>` | GET | Changement de statut d'audit |
| `/entreprises` | GET | Liste de toutes les entreprises |
| `/entreprise/<id>` | GET | Détails d'une entreprise |

## 📝 Workflow du formulaire "Nouveau Projet"

### Étape 1 : Informations Entreprise

**Choix 1 : Nouvelle entreprise**
```python
# Champs du formulaire
nom_entreprise: str (requis)
siret: str (14 chiffres, optionnel)
adresse: str
secteur_activite: str
presentation_desc: text
contraintes_reglementaires: text
organigramme: file (PDF, images)
```

**Choix 2 : Entreprise existante**
```python
entreprise_id: int (sélection dropdown)
```

### Étape 2 : Contacts Clés

Ajout dynamique de contacts (JavaScript) :
```python
# Pour chaque contact (index i)
contact_nom_{i}: str
contact_role_{i}: str
contact_email_{i}: str
contact_telephone_{i}: str
contact_principal_{i}: bool (checkbox)
```

### Étape 3 : Cadrage Audit

```python
# Informations générales
nom_projet: str (requis)

# Documents administratifs (uploads)
lettre_mission: file (PDF)
contrat: file (PDF)
planning: file (Excel, PDF)

# Contexte
objectifs: text
limites: text
hypotheses: text
risques_initiaux: text
```

## 🔒 Gestion des uploads de fichiers

### Configuration

```python
UPLOAD_FOLDER = 'uploads/'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xlsx', 'xls'}
```

### Sécurisation

1. **Validation de l'extension** : `allowed_file(filename)`
2. **Nom sécurisé** : `secure_filename(filename)`
3. **Horodatage** : `filename_{timestamp}.ext`
4. **Organisation par type** : `uploads/entreprises/`, `uploads/audits/lettres_mission/`

### Fonction d'upload

```python
def save_uploaded_file(file, subfolder=''):
    """
    Sauvegarde sécurisée avec :
    - Vérification extension
    - Nom sécurisé
    - Timestamp unique
    - Création dossier si nécessaire
    """
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        return os.path.join(subfolder, unique_filename)
    return None
```

## 🎨 Frontend - Bootstrap 5

### Composants utilisés

- **Cards** : Affichage des informations structurées
- **Badges** : Statuts d'audit (colorés selon l'état)
- **Forms** : Formulaires avec validation
- **List Groups** : Listes de contacts, sites, documents
- **Buttons** : Actions (créer, ajouter, changer statut)
- **Alerts** : Messages flash (success, danger, warning, info)

### Wizard multi-étapes

```javascript
// Gestion des étapes
function nextStep(step) {
    // Validation
    // Masquer toutes les étapes
    // Afficher l'étape courante
    // Marquer les étapes précédentes comme complétées
}

// Ajout dynamique de contacts
let contactCounter = 1;
function addContact() {
    // Crée un nouveau bloc contact avec index unique
    // Ajoute au DOM
    contactCounter++;
}
```

### Badges de statut

```html
<span class="status-badge status-NOUVEAU">NOUVEAU</span>
<span class="status-badge status-EN_COURS">EN COURS</span>
<span class="status-badge status-TERMINE">TERMINÉ</span>
```

CSS associé :
```css
.status-NOUVEAU { background: #cfe2ff; color: #084298; }
.status-EN_COURS { background: #fff3cd; color: #997404; }
.status-TERMINE { background: #d1e7dd; color: #0f5132; }
```

## 🗄️ Modèles de données

### Entreprise

```python
class Entreprise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), unique=True, nullable=False)
    # ... autres champs
    
    # Relations
    audits = db.relationship('Audit', back_populates='entreprise')
    contacts = db.relationship('Contact', back_populates='entreprise')
    sites = db.relationship('Site', back_populates='entreprise')
```

### Audit (avec Enum pour le statut)

```python
class AuditStatus(PyEnum):
    NOUVEAU = "NOUVEAU"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"

class Audit(db.Model):
    status = db.Column(db.Enum(AuditStatus), default=AuditStatus.NOUVEAU)
    # Bloc Administratif
    lettre_mission_path = db.Column(db.String(500))
    contrat_path = db.Column(db.String(500))
    planning_path = db.Column(db.String(500))
    # Bloc Contexte
    objectifs = db.Column(db.Text)
    limites = db.Column(db.Text)
    hypotheses = db.Column(db.Text)
    risques_initiaux = db.Column(db.Text)
```

## 🧪 Tests et développement

### Initialiser avec des données de test

```bash
python init_db.py
```

Crée :
- 2 entreprises
- 3 contacts
- 3 audits (différents statuts)
- 4 sites

### Tester les routes

```bash
python test_routes.py
```

### Shell interactif

```bash
flask shell
```

Modèles disponibles automatiquement :
```python
>>> from app.models import *
>>> Entreprise.query.all()
>>> Audit.query.filter_by(status=AuditStatus.EN_COURS).all()
```

## 📊 Messages Flash

Types de messages :
- `success` : Opération réussie (vert)
- `danger` : Erreur (rouge)
- `warning` : Avertissement (jaune)
- `info` : Information (bleu)

Utilisation :
```python
flash('✅ Projet créé avec succès !', 'success')
flash('❌ Erreur lors de la création', 'danger')
```

## 🔄 Flux complet de création d'un audit

1. **GET** `/nouveau-projet` → Affiche formulaire wizard
2. **User** remplit Étape 1 (Entreprise)
3. **User** remplit Étape 2 (Contacts)
4. **User** remplit Étape 3 (Audit + uploads)
5. **POST** `/nouveau-projet` avec `multipart/form-data`
6. **Backend** :
   - Crée/récupère Entreprise
   - Crée les Contacts (loop sur index)
   - Upload et sauvegarde les fichiers
   - Crée l'Audit
   - Commit en base
7. **Redirect** vers `/audit/<id>` avec message flash
8. **Affichage** du tableau de bord de l'audit

## 🚀 Améliorations possibles

- Authentification utilisateur
- Export PDF des rapports d'audit
- Gestion des versions de documents
- API REST pour intégration tierce
- Téléchargement de fichiers uploadés
- Recherche et filtrage avancés
- Dashboard avec graphiques (Chart.js)
- Notifications par email
- Historique des modifications

---

# 🔌 MODULE PHYSIQUE & RÉSEAU

## 📋 Présentation Générale

Le module **Physique & Réseau** gère l'inventaire des équipements informatiques d'un site (serveurs, switchs, routeurs, firewalls) et l'historique des scans réseau. Il utilise **SQLAlchemy Joined Table Inheritance** pour supporter différents types d'équipements avec leurs propriétés spécifiques tout en partageant des attributs communs.

### Architecture du modèle d'héritage

```
Equipement (table mère)
    ├── EquipementReseau (Switchs, Routeurs, Bornes WiFi)
    ├── EquipementServeur (Windows, Linux, Hyperviseurs)
    └── EquipementFirewall (Fortigate, PaloAlto, Checkpoint)
```

## 📊 Modèles de Données

### Table Mère - `Equipement`

```python
class Equipement(db.Model):
    """Équipement générique avec données communes (découverte par scan)"""
    id = db.Column(db.Integer, primary_key=True)
    type_equipement = db.Column(db.String(50), nullable=False)  # Discriminateur
    
    # Champs découverts par scan Nmap
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv4 ou IPv6
    mac_address = db.Column(db.String(17))  # Format: AA:BB:CC:DD:EE:FF
    hostname = db.Column(db.String(255))
    fabricant = db.Column(db.String(200))
    os_detected = db.Column(db.String(255))  # OS détecté par scan
    
    # Gestion d'audit
    status_audit = db.Column(db.Enum(EquipementAuditStatus))
    # Valeurs: 'A_AUDITER', 'CONFORME', 'NON_CONFORME'
    
    # Métadonnées
    date_decouverte = db.Column(db.DateTime)
    date_derniere_maj = db.Column(db.DateTime)
    notes_audit = db.Column(db.Text)
```

### Table Fille - `EquipementReseau`

```python
class EquipementReseau(Equipement):
    """Switchs, Routeurs, Bornes WiFi, etc."""
    
    # Champs spécifiques
    vlan_config = db.Column(db.JSON)      # {'vlan_1': 'Management', 'vlan_10': 'DATA'}
    ports_status = db.Column(db.JSON)     # {'port_1': 'UP', 'port_2': 'DOWN'}
    firmware_version = db.Column(db.String(100))  # Ex: "15.2(4)M11"
```

**Cas d'usage** :
- Détection d'un Switch Cisco avec 48 ports
- Historique VLAN pour segmentation réseau
- État des ports pour détecter déconnexions

### Table Fille - `EquipementServeur`

```python
class EquipementServeur(Equipement):
    """Serveurs Windows/Linux, Hyperviseurs, etc."""
    
    # Champs spécifiques
    os_version_detail = db.Column(db.String(500))  # "Windows Server 2022 Build 20348"
    role_list = db.Column(db.JSON)           # ['AD', 'DHCP', 'DNS']
    cpu_ram_info = db.Column(db.JSON)        # {'cpu_cores': 8, 'ram_gb': 32, 'cpu_model': '...'}
```

**Cas d'usage** :
- Serveur Active Directory avec DHCP/DNS
- Analyse des ressources (CPU/RAM) disponibles
- Validation des rôles en fonction de la charge

### Table Fille - `EquipementFirewall`

```python
class EquipementFirewall(Equipement):
    """Firewalls Fortigate, PaloAlto, Checkpoint, etc."""
    
    # Champs spécifiques
    license_status = db.Column(db.String(100))  # 'ACTIVE', 'GRACE_PERIOD', 'EXPIRED'
    vpn_users_count = db.Column(db.Integer)     # Nombre d'utilisateurs VPN actuels
    rules_count = db.Column(db.Integer)         # Nombre total de règles
```

**Cas d'usage** :
- Vérification de l'expiration de licence (critique ⚠️)
- Analyse de charge VPN
- Audit des règles de firewall

### Table `ScanReseau`

```python
class ScanReseau(db.Model):
    """Historique des scans réseau (Nmap, OpenVAS, Qualys, etc.)"""
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    
    # Résultats du scan
    date_scan = db.Column(db.DateTime, default=datetime.utcnow)
    type_scan = db.Column(db.String(50))  # 'NMAP', 'OPENVAS', 'QUALYS'
    nombre_hosts_trouves = db.Column(db.Integer)
    nombre_ports_ouverts = db.Column(db.Integer)
    duree_scan_secondes = db.Column(db.Integer)
    
    # Données brutes
    raw_xml_output = db.Column(db.Text)  # Sortie XML complète du scan
    notes = db.Column(db.Text)
```

## 🔧 Routes Disponibles

| Route | Méthode | Description |
|-------|---------|-------------|
| `/site/<id>/equipements` | GET | Liste des équipements d'un site |
| `/equipement/<id>` | GET | Détails détaillés d'un équipement |
| `/equipement/<id>/audit` | GET, POST | Auditer un équipement (changer statut, notes) |
| `/site/<id>/scans` | GET | Historique des scans du site |
| `/scan/<id>` | GET | Détails complets d'un scan |

## 📱 Interfaces Web

### Page de Liste des Équipements

**URL** : `/site/<id>/equipements`

**Affichage** :
- 🎯 **Statistiques d'audit** : Total, Conformes, À auditer, Non conformes
- 📊 **Tableaux par type** :
  - Équipements Réseau (Cisco Switch, Juniper Router, etc.)
  - Serveurs (Windows AD, Linux Web, Hyperviseur Hyper-V)
  - Firewalls (Fortigate, PaloAlto)

**Actions disponibles** :
- 👁️ Voir détails d'un équipement
- ✅ Auditer l'équipement
- 📊 Consulter l'historique des scans

### Page de Détails d'Équipement

**URL** : `/equipement/<id>`

**Affichage générique** :
- Informations générales (IP, MAC, Hostname, Fabricant)
- Statut d'audit actuel
- Dates de découverte et modification

**Affichage spécifique par type** :
- **Réseau** : Configuration VLAN, état des ports, firmware
- **Serveur** : Rôles, ressources CPU/RAM, version OS détaillée
- **Firewall** : Statut licence, utilisateurs VPN, nombre de règles

### Page d'Audit d'Équipement

**URL** : `/equipement/<id>/audit`

**Formulaire** :
- Sélecteur de statut (Conforme / À Auditer / Non Conforme)
- Champ de notes d'audit (texte libre pour observations)

### Liste des Scans

**URL** : `/site/<id>/scans`

**Affichage** :
- Cartes par scan avec :
  - Type de scan (NMAP, OPENVAS, QUALYS)
  - Nombre de hosts découverts
  - Nombre de ports ouverts
  - Durée du scan
  - Notes

### Détails d'un Scan

**URL** : `/scan/<id>`

**Affichage** :
- Statistiques complètes du scan
- Date et heure d'exécution
- Sortie XML brute (premiers 1000 caractères + taille totale)

## 💾 Gestion des Données

### Insertion d'Équipements

```python
# Créer un switch Cisco
switch = EquipementReseau(
    site_id=1,
    ip_address="192.168.1.1",
    mac_address="AA:BB:CC:DD:EE:01",
    hostname="SWITCH-CORE-01",
    fabricant="Cisco",
    os_detected="Cisco IOS",
    status_audit=EquipementAuditStatus.CONFORME,
    vlan_config={"vlan_1": "Management", "vlan_10": "Data"},
    ports_status={"port_1": "UP", "port_2": "UP"},
    firmware_version="15.2(4)M11"
)
db.session.add(switch)
db.session.commit()
```

### Requêtes Polymorphes

```python
# Récupérer tous les équipements d'un site (tous types)
tous = Equipement.query.filter_by(site_id=1).all()

# Récupérer uniquement les serveurs
serveurs = EquipementServeur.query.filter_by(site_id=1).all()

# Équipements non conformes
non_conformes = Equipement.query.filter_by(
    site_id=1,
    status_audit=EquipementAuditStatus.NON_CONFORME
).all()

# Firewalls avec licence expirée
fw_expired = EquipementFirewall.query.filter(
    EquipementFirewall.license_status == 'EXPIRED'
).all()

# Serveurs avec rôle 'AD'
ad_servers = db.session.query(EquipementServeur).filter(
    EquipementServeur.role_list.contains(['AD'])
).all()
```

## 🔍 Cas d'Audit Typiques

### Audit Conformité Sécurité

```python
# Vérifier tous les firewalls avec licence expirée
expired_fws = EquipementFirewall.query.filter_by(license_status='EXPIRED').all()

# Vérifier les serveurs AD conformes
ad_servers = EquipementServeur.query.filter(
    EquipementServeur.role_list.contains(['AD']),
    EquipementServeur.status_audit == EquipementAuditStatus.CONFORME
).all()
```

### Analyse d'Infrastructure

```python
# Total de CPU et RAM
total_ram = sum(
    s.cpu_ram_info['ram_gb'] for s in EquipementServeur.query.all()
    if s.cpu_ram_info
)

# Equipements manquants d'audit
a_auditer = Equipement.query.filter_by(
    status_audit=EquipementAuditStatus.A_AUDITER
).count()
```

## 📈 Exemples d'Utilisation

### Intégration avec Scans Nmap

1. **Importer les résultats Nmap** en XML
2. **Parser le XML** et créer des `Equipement` correspondants
3. **Automatiser** via cron job
4. **Alerter** si équipements inconnus découverts

### Dashboard de Conformité

Visualiser par site :
- ✓ Equipements conformes
- ⚠️ En attente d'audit
- ✗ Non conformes

## 🧪 Données de Test

Le script `init_db.py` crée :

**Équipements Réseau (3)** :
- Switch Cisco CONFORME
- Routeur Juniper À AUDITER
- Borne WiFi Ubiquiti NON CONFORME

**Serveurs (3)** :
- Active Directory CONFORME (8 CPU, 32 GB RAM)
- Web Server Linux À AUDITER (16 CPU, 64 GB RAM)
- Hyperviseur Hyper-V CONFORME (32 CPU, 256 GB RAM)

**Firewalls (2)** :
- Fortigate license ACTIVE avec 42 users VPN
- PaloAlto license EXPIRED ⚠️

**Scans (3)** :
- NMAP : 8 hosts, 34 ports
- OPENVAS : 12 hosts, 28 ports
- QUALYS : 15 hosts, 45 ports

### Générer les données

```bash
python init_db.py
```

Les données apparaissent dans les requêtes (exemples affichés).
