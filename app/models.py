"""
Modèles SQLAlchemy pour le module Administratif & Client
et le module Physique & Réseau
Logiciel d'Audit IT - AssistantAudit
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


def utcnow():
    """Retourne l'heure UTC actuelle (timezone-aware)"""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """
    Modèle utilisateur pour l'authentification
    """
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nom_complet = db.Column(db.String(200))
    role = db.Column(db.String(50), default='auditeur')  # 'admin', 'auditeur'
    actif = db.Column(db.Boolean, default=True, nullable=False)
    date_creation = db.Column(db.DateTime, default=utcnow, nullable=False)
    derniere_connexion = db.Column(db.DateTime)

    def set_password(self, password):
        """Hash et stocke le mot de passe"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Vérifie le mot de passe"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class AuditStatus(PyEnum):
    """Énumération des statuts possibles pour un audit"""
    NOUVEAU = "NOUVEAU"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"


class EquipementAuditStatus(PyEnum):
    """Énumération des statuts d'audit pour les équipements"""
    A_AUDITER = "A_AUDITER"
    CONFORME = "CONFORME"
    NON_CONFORME = "NON_CONFORME"


class ChecklistStatut(PyEnum):
    """Énumération des statuts de checklist"""
    NON_VERIFIE = "non_verifie"
    CONFORME = "conforme"
    NON_CONFORME = "non_conforme"
    NON_APPLICABLE = "non_applicable"


class Entreprise(db.Model):
    """
    Modèle représentant une entreprise cliente
    """
    __tablename__ = 'entreprise'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Informations de base
    nom = db.Column(db.String(200), unique=True, nullable=False, index=True)
    adresse = db.Column(db.String(500))
    secteur_activite = db.Column(db.String(100))
    siret = db.Column(db.String(14), unique=True)
    
    # Informations détaillées
    presentation_desc = db.Column(db.Text)
    organigramme_path = db.Column(db.String(500))  # Chemin vers le fichier organigramme
    contraintes_reglementaires = db.Column(db.Text)
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Relations
    audits = db.relationship('Audit', back_populates='entreprise', lazy='dynamic', cascade='all, delete-orphan')
    contacts = db.relationship('Contact', back_populates='entreprise', lazy='dynamic', cascade='all, delete-orphan')
    sites = db.relationship('Site', back_populates='entreprise', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Entreprise(id={self.id}, nom='{self.nom}', siret='{self.siret}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'nom': self.nom,
            'adresse': self.adresse,
            'secteur_activite': self.secteur_activite,
            'siret': self.siret,
            'presentation_desc': self.presentation_desc,
            'organigramme_path': self.organigramme_path,
            'contraintes_reglementaires': self.contraintes_reglementaires,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None
        }


class Contact(db.Model):
    """
    Modèle représentant un contact au sein d'une entreprise
    """
    __tablename__ = 'contact'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Informations du contact
    nom = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(100))
    email = db.Column(db.String(200), index=True)
    telephone = db.Column(db.String(20))
    is_main_contact = db.Column(db.Boolean, default=False, nullable=False)
    
    # Clé étrangère
    entreprise_id = db.Column(db.Integer, db.ForeignKey('entreprise.id'), nullable=False)
    
    # Relation
    entreprise = db.relationship('Entreprise', back_populates='contacts')
    
    def __repr__(self):
        main = " (Principal)" if self.is_main_contact else ""
        return f"<Contact(id={self.id}, nom='{self.nom}', role='{self.role}'{main})>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'nom': self.nom,
            'role': self.role,
            'email': self.email,
            'telephone': self.telephone,
            'is_main_contact': self.is_main_contact,
            'entreprise_id': self.entreprise_id
        }


class Audit(db.Model):
    """
    Modèle représentant un projet d'audit IT
    Inclut les blocs Administratif et Contexte
    """
    __tablename__ = 'audit'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Informations générales
    nom_projet = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Enum(AuditStatus), default=AuditStatus.NOUVEAU, nullable=False)
    date_debut = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Clé étrangère
    entreprise_id = db.Column(db.Integer, db.ForeignKey('entreprise.id'), nullable=False)
    
    # BLOC ADMINISTRATIF
    lettre_mission_path = db.Column(db.String(500))  # Chemin vers la lettre de mission
    contrat_path = db.Column(db.String(500))         # Chemin vers le contrat
    planning_path = db.Column(db.String(500))        # Chemin vers le planning
    
    # BLOC CONTEXTE
    objectifs = db.Column(db.Text)                   # Objectifs de l'audit
    limites = db.Column(db.Text)                     # Limites/périmètre
    hypotheses = db.Column(db.Text)                  # Hypothèses de travail
    risques_initiaux = db.Column(db.Text)            # Risques identifiés initialement
    
    # Relation
    entreprise = db.relationship('Entreprise', back_populates='audits')
    
    def __repr__(self):
        return f"<Audit(id={self.id}, projet='{self.nom_projet}', status={self.status.value}, entreprise_id={self.entreprise_id})>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'nom_projet': self.nom_projet,
            'status': self.status.value,
            'date_debut': self.date_debut.isoformat() if self.date_debut else None,
            'entreprise_id': self.entreprise_id,
            # Bloc Administratif
            'lettre_mission_path': self.lettre_mission_path,
            'contrat_path': self.contrat_path,
            'planning_path': self.planning_path,
            # Bloc Contexte
            'objectifs': self.objectifs,
            'limites': self.limites,
            'hypotheses': self.hypotheses,
            'risques_initiaux': self.risques_initiaux
        }


class Site(db.Model):
    """
    Modèle représentant un site/établissement d'une entreprise
    """
    __tablename__ = 'site'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Informations du site
    nom = db.Column(db.String(200), nullable=False)
    adresse = db.Column(db.String(500))
    
    # Clé étrangère
    entreprise_id = db.Column(db.Integer, db.ForeignKey('entreprise.id'), nullable=False)
    
    # Relation
    entreprise = db.relationship('Entreprise', back_populates='sites')
    # Relation vers les équipements du site
    equipements = db.relationship('Equipement', back_populates='site', lazy='dynamic', cascade='all, delete-orphan')
    # Relation vers les scans réseau du site
    scans = db.relationship('ScanReseau', back_populates='site', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Site(id={self.id}, nom='{self.nom}', adresse='{self.adresse}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'nom': self.nom,
            'adresse': self.adresse,
            'entreprise_id': self.entreprise_id
        }


# ============================================================================
# MODULE PHYSIQUE & RÉSEAU - Modélisation des Équipements
# ============================================================================

class Equipement(db.Model):
    """
    Modèle mère représentant un équipement réseau/infrastructure
    Utilise Joined Table Inheritance pour supporter différents types d'équipements
    """
    __tablename__ = 'equipement'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Type d'équipement (discriminateur pour l'héritage)
    type_equipement = db.Column(db.String(50), nullable=False, index=True)
    
    # Champs communs découverts par scan
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # Support IPv4 et IPv6
    mac_address = db.Column(db.String(17), index=True)  # Format AA:BB:CC:DD:EE:FF
    hostname = db.Column(db.String(255), index=True)
    fabricant = db.Column(db.String(200))
    os_detected = db.Column(db.String(255))  # OS détecté par scan
    
    # Gestion d'audit
    status_audit = db.Column(db.Enum(EquipementAuditStatus), default=EquipementAuditStatus.A_AUDITER, nullable=False)
    
    # Métadonnées
    date_decouverte = db.Column(db.DateTime, default=utcnow, nullable=False)
    date_derniere_maj = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    notes_audit = db.Column(db.Text)  # Commentaires sur l'audit
    
    # Relation vers le site
    site = db.relationship('Site', back_populates='equipements')
    
    # Contrainte d'unicité site + IP
    __table_args__ = (
        db.UniqueConstraint('site_id', 'ip_address', name='uq_site_ip'),
    )

    # Configuration pour l'héritage
    __mapper_args__ = {
        'polymorphic_identity': 'equipement',
        'polymorphic_on': type_equipement
    }
    
    def __repr__(self):
        return f"<Equipement(id={self.id}, type='{self.type_equipement}', ip='{self.ip_address}', hostname='{self.hostname}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'type_equipement': self.type_equipement,
            'site_id': self.site_id,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'hostname': self.hostname,
            'fabricant': self.fabricant,
            'os_detected': self.os_detected,
            'status_audit': self.status_audit.value,
            'date_decouverte': self.date_decouverte.isoformat() if self.date_decouverte else None,
            'date_derniere_maj': self.date_derniere_maj.isoformat() if self.date_derniere_maj else None,
            'notes_audit': self.notes_audit
        }


class EquipementReseau(Equipement):
    """
    Modèle pour les équipements réseau (Switchs, Routeurs, Bornes WiFi)
    Hérité de Equipement via Joined Table Inheritance
    """
    __tablename__ = 'equipement_reseau'
    
    # Clé étrangère vers la table mère
    id = db.Column(db.Integer, db.ForeignKey('equipement.id'), primary_key=True)
    
    # Champs spécifiques aux équipements réseau
    vlan_config = db.Column(db.JSON)  # Configuration VLAN en JSON
    ports_status = db.Column(db.JSON)  # État des ports {'port_1': 'UP', 'port_2': 'DOWN', ...}
    firmware_version = db.Column(db.String(100))  # Version du firmware
    
    # Configuration pour l'héritage
    __mapper_args__ = {
        'polymorphic_identity': 'reseau',
    }
    
    def __repr__(self):
        return f"<EquipementReseau(id={self.id}, ip='{self.ip_address}', firmware='{self.firmware_version}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        data = super().to_dict()
        data.update({
            'vlan_config': self.vlan_config,
            'ports_status': self.ports_status,
            'firmware_version': self.firmware_version
        })
        return data


class EquipementServeur(Equipement):
    """
    Modèle pour les serveurs (Windows, Linux, Hyperviseurs)
    Hérité de Equipement via Joined Table Inheritance
    """
    __tablename__ = 'equipement_serveur'
    
    # Clé étrangère vers la table mère
    id = db.Column(db.Integer, db.ForeignKey('equipement.id'), primary_key=True)
    
    # Champs spécifiques aux serveurs
    os_version_detail = db.Column(db.String(500))  # Ex: "Windows Server 2019 Build 17763"
    modele_materiel = db.Column(db.String(200))  # Ex: "Dell PowerEdge R740"
    role_list = db.Column(db.JSON)  # Liste des rôles ['AD', 'DHCP', 'DNS', ...]
    cpu_ram_info = db.Column(db.JSON)  # {'cpu_cores': 8, 'ram_gb': 32, 'cpu_model': 'Intel Xeon'}
    
    # Configuration pour l'héritage
    __mapper_args__ = {
        'polymorphic_identity': 'serveur',
    }
    
    def __repr__(self):
        return f"<EquipementServeur(id={self.id}, ip='{self.ip_address}', os='{self.os_version_detail}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        data = super().to_dict()
        data.update({
            'os_version_detail': self.os_version_detail,
            'modele_materiel': self.modele_materiel,
            'role_list': self.role_list,
            'cpu_ram_info': self.cpu_ram_info
        })
        return data


class EquipementFirewall(Equipement):
    """
    Modèle pour les firewalls (Fortigate, PaloAlto, Checkpoint, etc.)
    Hérité de Equipement via Joined Table Inheritance
    """
    __tablename__ = 'equipement_firewall'
    
    # Clé étrangère vers la table mère
    id = db.Column(db.Integer, db.ForeignKey('equipement.id'), primary_key=True)
    
    # Champs spécifiques aux firewalls
    license_status = db.Column(db.String(100))  # 'ACTIVE', 'EXPIRED', 'GRACE_PERIOD'
    vpn_users_count = db.Column(db.Integer, default=0)  # Nombre d'utilisateurs VPN connectés
    rules_count = db.Column(db.Integer, default=0)  # Nombre total de règles configurées
    
    # Configuration pour l'héritage
    __mapper_args__ = {
        'polymorphic_identity': 'firewall',
    }
    
    def __repr__(self):
        return f"<EquipementFirewall(id={self.id}, ip='{self.ip_address}', license='{self.license_status}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        data = super().to_dict()
        data.update({
            'license_status': self.license_status,
            'vpn_users_count': self.vpn_users_count,
            'rules_count': self.rules_count
        })
        return data


class ScanReseau(db.Model):
    """
    Modèle pour garder un historique des scans réseau (Nmap, etc.)
    """
    __tablename__ = 'scan_reseau'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Relations
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False, index=True)
    site = db.relationship('Site', back_populates='scans')
    hosts = db.relationship('ScanHost', back_populates='scan', lazy='dynamic', cascade='all, delete-orphan')
    
    # Données du scan
    date_scan = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    raw_xml_output = db.Column(db.Text)  # Résultat brut du scan (XML Nmap par exemple)
    type_scan = db.Column(db.String(50))  # 'NMAP', 'OPENVAS', 'QUALYS', etc.
    
    # Métadonnées du scan
    nombre_hosts_trouves = db.Column(db.Integer, default=0)
    nombre_ports_ouverts = db.Column(db.Integer, default=0)
    duree_scan_secondes = db.Column(db.Integer)  # Durée du scan en secondes
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f"<ScanReseau(id={self.id}, site_id={self.site_id}, date='{self.date_scan}', type='{self.type_scan}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'site_id': self.site_id,
            'date_scan': self.date_scan.isoformat() if self.date_scan else None,
            'type_scan': self.type_scan,
            'nombre_hosts_trouves': self.nombre_hosts_trouves,
            'nombre_ports_ouverts': self.nombre_ports_ouverts,
            'duree_scan_secondes': self.duree_scan_secondes,
            'notes': self.notes,
            'raw_xml_output': self.raw_xml_output[:200] + '...' if self.raw_xml_output and len(self.raw_xml_output) > 200 else self.raw_xml_output
        }


class ScanHost(db.Model):
    """
    Modèle représentant un hôte découvert lors d'un scan réseau
    Utilisé pour la validation des découvertes avant création d'équipement
    """
    __tablename__ = 'scan_host'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Relation vers le scan
    scan_id = db.Column(db.Integer, db.ForeignKey('scan_reseau.id'), nullable=False, index=True)
    scan = db.relationship('ScanReseau', back_populates='hosts')
    
    # Informations découvertes
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    hostname = db.Column(db.String(255))
    mac_address = db.Column(db.String(17))
    vendor = db.Column(db.String(200))  # Vendor du MAC (ex: Cisco, Dell)
    os_guess = db.Column(db.String(255))  # OS détecté par Nmap
    status = db.Column(db.String(20))  # 'up', 'down', 'unknown'
    ports_open_count = db.Column(db.Integer, default=0)
    
    # Décision de validation
    decision = db.Column(db.String(20))  # 'pending', 'kept', 'ignored'
    chosen_type = db.Column(db.String(50))  # Type d'équipement choisi si 'kept': 'reseau', 'serveur', 'firewall'
    equipement_id = db.Column(db.Integer, db.ForeignKey('equipement.id'), index=True)  # Lien vers équipement créé ou mis à jour
    
    # Métadonnées
    date_decouverte = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Relations
    ports = db.relationship('ScanPort', back_populates='host', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<ScanHost(id={self.id}, ip='{self.ip_address}', hostname='{self.hostname}', decision='{self.decision}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'scan_id': self.scan_id,
            'ip_address': self.ip_address,
            'hostname': self.hostname,
            'mac_address': self.mac_address,
            'vendor': self.vendor,
            'os_guess': self.os_guess,
            'status': self.status,
            'ports_open_count': self.ports_open_count,
            'decision': self.decision,
            'chosen_type': self.chosen_type,
            'equipement_id': self.equipement_id,
            'date_decouverte': self.date_decouverte.isoformat() if self.date_decouverte else None
        }


class ScanPort(db.Model):
    """
    Modèle représentant un port découvert lors d'un scan réseau
    """
    __tablename__ = 'scan_port'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Relation vers l'hôte
    host_id = db.Column(db.Integer, db.ForeignKey('scan_host.id'), nullable=False, index=True)
    host = db.relationship('ScanHost', back_populates='ports')
    
    # Informations du port
    port_number = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(10))  # 'tcp', 'udp'
    state = db.Column(db.String(20))  # 'open', 'closed', 'filtered'
    service_name = db.Column(db.String(100))  # 'http', 'ssh', 'mysql', etc.
    product = db.Column(db.String(200))  # Ex: 'Apache httpd'
    version = db.Column(db.String(100))  # Ex: '2.4.41'
    extra_info = db.Column(db.Text)  # Infos supplémentaires (JSON ou texte)
    
    def __repr__(self):
        return f"<ScanPort(id={self.id}, port={self.port_number}/{self.protocol}, state='{self.state}', service='{self.service_name}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'host_id': self.host_id,
            'port_number': self.port_number,
            'protocol': self.protocol,
            'state': self.state,
            'service_name': self.service_name,
            'product': self.product,
            'version': self.version,
            'extra_info': self.extra_info
        }


class ChecklistTemplate(db.Model):
    """
    Modèle représentant un template de checklist par type d'équipement
    """
    __tablename__ = 'checklist_template'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Type d'équipement concerné
    type_equipement = db.Column(db.String(50), nullable=False, index=True)  # 'reseau', 'serveur', 'firewall'
    
    # Item de checklist
    label = db.Column(db.String(500), nullable=False)  # Ex: "Vérifier la version du firmware"
    description = db.Column(db.Text)  # Description détaillée facultative
    ordre = db.Column(db.Integer, default=0)  # Ordre d'affichage
    actif = db.Column(db.Boolean, default=True, nullable=False)  # Activer/désactiver l'item
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ChecklistTemplate(id={self.id}, type='{self.type_equipement}', label='{self.label}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'type_equipement': self.type_equipement,
            'label': self.label,
            'description': self.description,
            'ordre': self.ordre,
            'actif': self.actif,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None
        }


class EquipementChecklist(db.Model):
    """
    Modèle représentant une checklist d'audit associée à un équipement
    Lien entre l'équipement et les templates de checklist
    """
    __tablename__ = 'equipement_checklist'
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Relations
    equipement_id = db.Column(db.Integer, db.ForeignKey('equipement.id'), nullable=False, index=True)
    template_id = db.Column(db.Integer, db.ForeignKey('checklist_template.id'), nullable=False, index=True)
    
    # État de validation
    statut = db.Column(db.Enum(ChecklistStatut), default=ChecklistStatut.NON_VERIFIE, nullable=False)
    commentaire = db.Column(db.Text)  # Commentaires sur cet item
    
    # Métadonnées
    date_verification = db.Column(db.DateTime)  # Date de vérification
    verifie_par = db.Column(db.String(200))  # Auditeur qui a vérifié
    
    # Relations
    equipement = db.relationship('Equipement', backref=db.backref('checklist_items', lazy='dynamic', cascade='all, delete-orphan'))
    template = db.relationship('ChecklistTemplate', backref=db.backref('equipement_usages', lazy='dynamic'))
    
    def __repr__(self):
        return f"<EquipementChecklist(id={self.id}, equipement_id={self.equipement_id}, template_id={self.template_id}, statut='{self.statut}')>"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'equipement_id': self.equipement_id,
            'template_id': self.template_id,
            'statut': self.statut.value if self.statut else None,
            'commentaire': self.commentaire,
            'date_verification': self.date_verification.isoformat() if self.date_verification else None,
            'verifie_par': self.verifie_par
        }

