# 📡 Module Physique & Réseau - Documentation Détaillée

**Version** : 1.0  
**Date** : 08 février 2026  
**Statut** : ✅ Production

---

## 📋 Table des Matières

1. [Architecture](#architecture)
2. [Modèles de Données](#modèles-de-données)
3. [Relations et Héritage](#relations-et-héritage)
4. [Routes et Endpoints](#routes-et-endpoints)
5. [Utilisation](#utilisation)
6. [Exemples Pratiques](#exemples-pratiques)
7. [Performance et Optimisations](#performance-et-optimisations)

---

## Architecture

### Approche Joined Table Inheritance

Le module utilise **SQLAlchemy's Joined Table Inheritance** pour modéliser les équipements :

```
┌─────────────────────────────┐
│      EQUIPEMENT (Mère)      │
│  - id (PK)                  │
│  - type_equipement (Disc.)  │
│  - ip_address               │
│  - mac_address              │
│  - hostname                 │
│  - fabricant                │
│  - os_detected              │
│  - status_audit             │
│  - notes_audit              │
│  - date_decouverte          │
│  - date_derniere_maj        │
└──────────────┬──────────────┘
               │
        ┌──────┼──────┐
        │      │      │
        ▼      ▼      ▼
    ┌─────────────┐  ┌──────────────┐  ┌────────────────┐
    │ RESEAU      │  │ SERVEUR      │  │ FIREWALL       │
    │─────────────│  │──────────────│  │────────────────│
    │ vlan_config │  │ os_version   │  │ license_status │
    │ ports_status│  │ role_list    │  │ vpn_users_count│
    │ firmware_v  │  │ cpu_ram_info │  │ rules_count    │
    └─────────────┘  └──────────────┘  └────────────────┘
        Switchs         Serveurs        Firewalls
        Routeurs        Hyperviseurs    Fortigate
        Bornes WiFi     Windows/Linux   PaloAlto
```

### Avantages de cette approche

✅ **Partage de code** : Attributs communs dans la table mère  
✅ **Type-safe** : Chaque type a ses propres propriétés  
✅ **Requêtes polymorphes** : Basculer entre types dynamiquement  
✅ **Extensibilité** : Ajouter facilement de nouveaux types  
✅ **Intégrité DB** : Chaque table a ses colonnes spécifiques  

---

## Modèles de Données

### 1. Énumération `EquipementAuditStatus`

```python
class EquipementAuditStatus(PyEnum):
    """État d'audit d'un équipement"""
    A_AUDITER = "A_AUDITER"      # Pas encore audité
    CONFORME = "CONFORME"        # Conforme aux normes
    NON_CONFORME = "NON_CONFORME"  # Problèmes identifiés
```

**Utilisation** :
```python
# Vérifier le statut
if eq.status_audit == EquipementAuditStatus.CONFORME:
    print("✓ Conforme")
elif eq.status_audit == EquipementAuditStatus.NON_CONFORME:
    print("⚠️ Action requise")
```

### 2. Modèle `Equipement` (Mère)

**Champs primaires** :
- `id` : Clé primaire auto-incrémentée
- `type_equipement` : Discriminateur pour l'héritage ('reseau', 'serveur', 'firewall')
- `site_id` : Clé étrangère vers Site

**Champs découverts par scan** :
- `ip_address` : Adresse IP (IPv4 ou IPv6)
- `mac_address` : Adresse MAC au format AA:BB:CC:DD:EE:FF
- `hostname` : Nom de l'hôte réseau
- `fabricant` : Fabricant de l'équipement
- `os_detected` : Système d'exploitation détecté

**Gestion d'audit** :
- `status_audit` : Statut d'audit (Enum)
- `notes_audit` : Commentaires d'audit (texte libre)

**Métadonnées** :
- `date_decouverte` : Quand l'équipement a été découvert
- `date_derniere_maj` : Dernière modification

**Exemple d'enregistrement** :
```json
{
  "id": 1,
  "type_equipement": "reseau",
  "site_id": 1,
  "ip_address": "192.168.1.1",
  "mac_address": "AA:BB:CC:DD:EE:01",
  "hostname": "SWITCH-CORE-01",
  "fabricant": "Cisco",
  "os_detected": "Cisco IOS",
  "status_audit": "CONFORME",
  "notes_audit": "Switch conforme audit juillet 2025",
  "date_decouverte": "2025-12-01T09:30:00",
  "date_derniere_maj": "2026-01-15T14:22:30"
}
```

### 3. Modèle `EquipementReseau` (Fille)

**Cas d'usage** :
- Switchs Cisco, Juniper, Arista
- Routeurs Cisco, Juniper
- Bornes WiFi Ubiquiti, Arista
- Tout équipement réseau layer 2/3

**Champs spécifiques** :

```python
vlan_config: JSON
# Exemple :
{
  "vlan_1": "Management",
  "vlan_10": "Data Network",
  "vlan_20": "VoIP",
  "vlan_100": "DMZ"
}

ports_status: JSON
# Exemple :
{
  "port_1": "UP",
  "port_2": "UP",
  "port_3": "DOWN",
  "port_48": "UP"
}

firmware_version: String
# Exemple : "15.2(4)M11" ou "JunOS 18.1R3"
```

**Requêtes utiles** :
```python
# Tous les switchs
switchs = EquipementReseau.query.filter_by(site_id=1).all()

# Equipements avec VLAN DMZ
dmz_vlans = db.session.query(EquipementReseau).filter(
    EquipementReseau.vlan_config.contains(['DMZ'])
).all()

# Ports avec problèmes (DOWN)
# À faire côté application (pas d'agrégation JSON directe)
problematic_equip = []
for eq in EquipementReseau.query.all():
    if eq.ports_status and 'DOWN' in eq.ports_status.values():
        problematic_equip.append(eq)
```

### 4. Modèle `EquipementServeur` (Fille)

**Cas d'usage** :
- Serveurs Windows Server (AD, DHCP, Exchange)
- Serveurs Linux (Web, Applications, Bases de données)
- Hyperviseurs (Hyper-V, VMware ESXi, KVM)

**Champs spécifiques** :

```python
os_version_detail: String
# Exemple : "Windows Server 2022 Datacenter Build 20348"
#           "Ubuntu 22.04 LTS (Kernel 5.15.0-86)"
#           "Hyper-V Server 2022"

role_list: JSON (Array)
# Exemple : ["Active Directory", "DHCP", "DNS"]
#           ["Web Server", "Application Server"]
#           ["Hypervisor"]

cpu_ram_info: JSON
# Exemple :
{
  "cpu_cores": 8,
  "ram_gb": 32,
  "cpu_model": "Intel Xeon E5-2620"
}
```

**Requêtes utiles** :
```python
# Serveurs AD
ad_servers = db.session.query(EquipementServeur).filter(
    EquipementServeur.role_list.contains(['Active Directory'])
).all()

# Serveurs avec peu de RAM (< 16 GB)
low_ram = [
    s for s in EquipementServeur.query.all()
    if s.cpu_ram_info and s.cpu_ram_info.get('ram_gb', 0) < 16
]

# Hyperviseurs du site
hypervisors = db.session.query(EquipementServeur).filter(
    EquipementServeur.role_list.contains(['Hypervisor']),
    EquipementServeur.site_id == 1
).all()

# Total de RAM disponible
total_ram = sum(
    s.cpu_ram_info.get('ram_gb', 0)
    for s in EquipementServeur.query.all()
    if s.cpu_ram_info
)
```

### 5. Modèle `EquipementFirewall` (Fille)

**Cas d'usage** :
- Fortigate (Fortinet)
- PaloAlto Networks
- Checkpoint
- Cisco ASA

**Champs spécifiques** :

```python
license_status: String
# Valeurs : 'ACTIVE', 'GRACE_PERIOD', 'EXPIRED'
# ⚠️ CRITICAL : Les firewall avec license EXPIRED
#    doivent être alertés urgemment

vpn_users_count: Integer
# Nombre d'utilisateurs VPN actuellement connectés
# Exemple : 42, 128, 0

rules_count: Integer
# Nombre total de règles configurées
# Exemple : 156, 89, 1200
```

**Requêtes utiles** :
```python
# Firewalls avec licence expirée (ALERTE)
expired_fws = EquipementFirewall.query.filter_by(
    license_status='EXPIRED'
).all()

# Firewalls avec beaucoup d'utilisateurs VPN
busy_vpn = [
    fw for fw in EquipementFirewall.query.all()
    if fw.vpn_users_count > 100
]

# Firewall avec le plus de règles
most_complex = max(
    EquipementFirewall.query.all(),
    key=lambda fw: fw.rules_count or 0
)
```

### 6. Modèle `ScanReseau`

**Champs** :

```python
id: Integer (PK)
site_id: Integer (FK → Site)
date_scan: DateTime           # Quand le scan a été lancé
type_scan: String             # 'NMAP', 'OPENVAS', 'QUALYS', etc.
nombre_hosts_trouves: Integer  # Count de hosts
nombre_ports_ouverts: Integer  # Total de ports
duree_scan_secondes: Integer   # Durée d'exécution
raw_xml_output: Text           # Sortie complète du scan
notes: Text                    # Observations
```

**Requêtes utiles** :
```python
# Derniers scans (Top 5)
recent = ScanReseau.query.order_by(
    ScanReseau.date_scan.desc()
).limit(5).all()

# Scans les plus longs
slow_scans = ScanReseau.query.order_by(
    ScanReseau.duree_scan_secondes.desc()
).limit(10).all()

# Scansmoyenne de ports/hosts par type
nmap_stats = db.session.query(
    func.count(ScanReseau.id).label('count'),
    func.avg(ScanReseau.nombre_ports_ouverts).label('avg_ports')
).filter_by(type_scan='NMAP').first()
```

---

## Relations et Héritage

### Relation Site → Équipements

```python
# Dans Site model
equipements = db.relationship('Equipement', back_populates='site')

# Utilisation
site = Site.query.get(1)
for eq in site.equipements:
    print(f"{eq.hostname} ({eq.type_equipement}): {eq.ip_address}")

# Filtrer par type
switchs = [eq for eq in site.equipements if isinstance(eq, EquipementReseau)]
```

### Requêtes Polymorphes

SQLAlchemy Joined Table Inheritance permet les requêtes sur la table mère :

```python
# Tous les équipements (tous types)
tous = Equipement.query.filter_by(site_id=1).all()
# Retourne: [<EquipementReseau>, <EquipementServeur>, <EquipementFirewall>]

# Filtrer par type
reseau_only = EquipementReseau.query.filter_by(site_id=1).all()
serv_only = EquipementServeur.query.filter_by(site_id=1).all()

# Polymorphise avec des opérateurs
conforme = Equipement.query.filter_by(
    site_id=1,
    status_audit=EquipementAuditStatus.CONFORME
).all()
```

---

## Routes et Endpoints

### GET `/site/<int:site_id>/equipements`

**Affichage** :
- Statistiques d'audit (total, conforme, à auditer, non conforme)
- Tableau des équipements réseau
- Tableau des serveurs
- Tableau des firewalls

**Template** : `liste_equipements.html`

### GET `/equipement/<int:equipement_id>`

**Affichage personnalisé selon le type** :

**Réseau** :
- Configuration VLAN
- État des ports
- Version firmware

**Serveur** :
- Détails OS
- Rôles et services
- Ressources CPU/RAM

**Firewall** :
- Statut licence
- Utilisateurs VPN
- Nombre de règles

**Template** : `detail_equipement.html`

### GET/POST `/equipement/<int:equipement_id>/audit`

**Action** : Modifier le statut d'audit et ajouter des notes

**Template** : `auditer_equipement.html`

### GET `/site/<int:site_id>/scans`

**Affichage** :
- Cartes des scans (date, type, hosts, ports)

**Template** : `liste_scans.html`

### GET `/scan/<int:scan_id>`

**Affichage** :
- Statistiques du scan
- Sortie XML brute (premiers 1000 chars)

**Template** : `detail_scan.html`

---

## Utilisation

### Créer un équipement réseau

```python
from app.models import EquipementReseau

switch = EquipementReseau(
    site_id=1,
    ip_address="192.168.1.1",
    mac_address="AA:BB:CC:DD:EE:01",
    hostname="SWITCH-CORE",
    fabricant="Cisco",
    os_detected="Cisco IOS",
    vlan_config={"vlan_1": "Mgmt", "vlan_10": "Data"},
    ports_status={"port_1": "UP", "port_2": "UP"},
    firmware_version="15.2(4)M11"
)

db.session.add(switch)
db.session.commit()
```

### Auditer un équipement

```python
equipement = Equipement.query.get(1)
equipement.status_audit = EquipementAuditStatus.CONFORME
equipement.notes_audit = "Switch Cisco conforme sécurité, audit {{ date }}"

db.session.commit()
```

### Récupérer et analyser

```python
# Tous les équipements non conformes
non_conformes = Equipement.query.filter_by(
    status_audit=EquipementAuditStatus.NON_CONFORME
).all()

for eq in non_conformes:
    print(f"❌ {eq.hostname}: {eq.notes_audit}")
```

---

## Exemples Pratiques

### 1. Rapport de Conformité par Site

```python
def rapport_conformite(site_id):
    site = Site.query.get(site_id)
    stats = {
        'conforme': 0,
        'a_auditer': 0,
        'non_conforme': 0
    }
    
    for eq in site.equipements:
        if eq.status_audit == EquipementAuditStatus.CONFORME:
            stats['conforme'] += 1
        elif eq.status_audit == EquipementAuditStatus.A_AUDITER:
            stats['a_auditer'] += 1
        else:
            stats['non_conforme'] += 1
    
    return stats

# Utilisation
rapport = rapport_conformite(1)
print(f"Site 1: {rapport['conforme']} conformes, {rapport['non_conforme']} à corriger")
```

### 2. Vérifier Licences Firewall

```python
def check_firewall_licenses():
    """Alerte sur les licences expirées"""
    expired = EquipementFirewall.query.filter_by(
        license_status='EXPIRED'
    ).all()
    
    if expired:
        print(f"⚠️ {len(expired)} firewall(s) avec licence expirée!")
        for fw in expired:
            print(f"  - {fw.hostname} ({fw.ip_address})")
    
    return len(expired)
```

### 3. Analyse de Capacité Réseau

```python
def capacite_vlan():
    """Analyser la capacité des VLANs"""
    vlans = {}
    
    for eq in EquipementReseau.query.all():
        if eq.vlan_config:
            for vlan_id, vlan_name in eq.vlan_config.items():
                if vlan_name not in vlans:
                    vlans[vlan_name] = 0
                vlans[vlan_name] += 1
    
    return vlans

# Résultat : {'Management': 3, 'Data': 5, 'VoIP': 2}
```

### 4. Statut des Serveurs

```python
def serveurs_critiques():
    """Lister les serveurs avec rôles critiques"""
    roles_critiques = ['Active Directory', 'DNS', 'DHCP']
    
    critiques = db.session.query(EquipementServeur).filter(
        EquipementServeur.role_list.contains(roles_critiques[0])
    ).all()
    
    for serveur in critiques:
        print(f"🚨 {serveur.hostname}: {serveur.role_list}")
```

---

## Performance et Optimisations

### Requêtes Couteuses à Optimiser

```python
# ❌ MAUVAIS : Charge chaque équipement indépendamment
for scan in ScanReseau.query.all():
    site = scan.site  # N+1 queries!
    
# ✅ BON : Eager loading
scans = ScanReseau.query.options(
    joinedload(ScanReseau.site)
).all()

# ❌ MAUVAIS : JSON filtering inefficace
matches = [s for s in EquipementServeur.query.all() if 'AD' in s.role_list]

# ✅ BON : Utiliser contains() de SQLAlchemy
matches = EquipementServeur.query.filter(
    EquipementServeur.role_list.contains(['AD'])
).all()
```

### Indexation

Les colonnes suivantes devraient être indexées :
- `ip_address` (recherches rapides)
- `hostname` (résolutions)
- `status_audit` (filtrage par statut)
- `date_scan` (tris temporels)

```python
# Déjà indexées dans les modèles :
site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False, index=True)
ip_address = db.Column(db.String(45), nullable=False, index=True)
```

---

## 📊 Statistiques d'Exemple

Après `init_db.py` :

| Métrique | Valeur |
|----------|--------|
| Équipements Réseau | 3 |
| Serveurs | 3 |
| Firewalls | 2 |
| **Total Équipements** | **8** |
| Équipements Conformes | 4 |
| À Auditer | 2 |
| Non Conformes | 2 |
| Scans Réseau | 3 |

---

**Mise à jour** : 08/02/2026  
**Module Version** : 1.0-stable  
**Next Version** : 1.1 (API REST, import Nmap XML)
