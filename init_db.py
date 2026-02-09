"""
Script de test pour valider les modèles SQLAlchemy
Crée des données d'exemple pour les modules Administratif & Client et Physique & Réseau
"""
from app import create_app, db
from app.models import (
    User, Entreprise, Contact, Audit, Site, AuditStatus,
    Equipement, EquipementReseau, EquipementServeur, EquipementFirewall, 
    EquipementAuditStatus, ScanReseau, ChecklistTemplate, EquipementChecklist
)
from datetime import datetime, timedelta, timezone
import json


def init_sample_data():
    """Initialise la base avec des données d'exemple"""
    
    app = create_app()
    
    with app.app_context():
        # Nettoyer la base
        db.drop_all()
        db.create_all()
        
        print("📊 Création des données d'exemple...\n")
        
        # === UTILISATEUR ADMIN ===
        admin = User(username='admin', email='admin@assistantaudit.local')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Utilisateur admin créé (login: admin / admin)\n")
        
        # === ENTREPRISE 1 ===
        entreprise1 = Entreprise(
            nom="TechSecure Solutions",
            adresse="42 Avenue des Champs-Élysées, 75008 Paris",
            secteur_activite="Cybersécurité",
            siret="12345678901234",
            presentation_desc="Leader européen en solutions de cybersécurité et audit IT. "
                            "Spécialisé dans la protection des infrastructures critiques.",
            contraintes_reglementaires="RGPD, NIS2, ISO 27001",
            date_creation=datetime(2020, 1, 15)
        )
        
        # === ENTREPRISE 2 ===
        entreprise2 = Entreprise(
            nom="HealthData Corp",
            adresse="15 Rue de la Santé, 69003 Lyon",
            secteur_activite="Santé numérique",
            siret="98765432109876",
            presentation_desc="Gestionnaire de données de santé pour hôpitaux et cliniques.",
            contraintes_reglementaires="RGPD, HDS (Hébergeur de Données de Santé), ISO 27001",
            date_creation=datetime(2018, 6, 20)
        )
        
        db.session.add_all([entreprise1, entreprise2])
        db.session.commit()
        print(f"✅ Créé: {entreprise1}")
        print(f"✅ Créé: {entreprise2}\n")
        
        # === CONTACTS ENTREPRISE 1 ===
        contact1_1 = Contact(
            nom="Marie Dubois",
            role="Directrice des Systèmes d'Information",
            email="m.dubois@techsecure.fr",
            telephone="+33 1 23 45 67 89",
            is_main_contact=True,
            entreprise_id=entreprise1.id
        )
        
        contact1_2 = Contact(
            nom="Pierre Martin",
            role="Responsable Sécurité",
            email="p.martin@techsecure.fr",
            telephone="+33 1 23 45 67 90",
            is_main_contact=False,
            entreprise_id=entreprise1.id
        )
        
        # === CONTACTS ENTREPRISE 2 ===
        contact2_1 = Contact(
            nom="Sophie Leclerc",
            role="DSI",
            email="s.leclerc@healthdata.fr",
            telephone="+33 4 12 34 56 78",
            is_main_contact=True,
            entreprise_id=entreprise2.id
        )
        
        db.session.add_all([contact1_1, contact1_2, contact2_1])
        db.session.commit()
        print(f"✅ Créé: {contact1_1}")
        print(f"✅ Créé: {contact1_2}")
        print(f"✅ Créé: {contact2_1}\n")
        
        # === AUDITS ===
        audit1 = Audit(
            nom_projet="Audit Infrastructure Cloud 2026",
            status=AuditStatus.EN_COURS,
            date_debut=datetime(2026, 1, 10),
            entreprise_id=entreprise1.id,
            # Bloc Administratif
            lettre_mission_path="/documents/audits/2026/lettre_mission_techsecure.pdf",
            contrat_path="/documents/audits/2026/contrat_techsecure.pdf",
            planning_path="/documents/audits/2026/planning_techsecure.xlsx",
            # Bloc Contexte
            objectifs="Évaluer la sécurité et la conformité de l'infrastructure cloud AWS. "
                     "Identifier les vulnérabilités critiques et proposer un plan d'action.",
            limites="Périmètre limité aux environnements de production. "
                   "Les environnements de développement sont exclus.",
            hypotheses="L'équipe IT dispose de 2 administrateurs cloud certifiés. "
                      "Les backups sont effectués quotidiennement.",
            risques_initiaux="Risque de configuration réseau inadéquate. "
                           "Absence potentielle de segmentation des environnements."
        )
        
        audit2 = Audit(
            nom_projet="Audit de conformité RGPD",
            status=AuditStatus.NOUVEAU,
            date_debut=datetime(2026, 2, 1),
            entreprise_id=entreprise2.id,
            # Bloc Administratif
            lettre_mission_path="/documents/audits/2026/lettre_mission_healthdata.pdf",
            # Bloc Contexte
            objectifs="Vérifier la conformité RGPD et HDS des traitements de données de santé.",
            limites="Audit documentaire et entretiens uniquement. Pas de tests techniques.",
            hypotheses="Le DPO est en poste depuis au moins 6 mois.",
            risques_initiaux="Documentation potentiellement incomplète. "
                           "Manque de traçabilité des consentements patients."
        )
        
        audit3 = Audit(
            nom_projet="Audit Sécurité Périmétrique 2025",
            status=AuditStatus.TERMINE,
            date_debut=datetime(2025, 11, 1),
            entreprise_id=entreprise1.id,
            objectifs="Évaluation de la sécurité du pare-feu et des règles de filtrage.",
            limites="Pas de tests d'intrusion.",
            contrat_path="/documents/audits/2025/contrat_secu_perimetrique.pdf"
        )
        
        db.session.add_all([audit1, audit2, audit3])
        db.session.commit()
        print(f"✅ Créé: {audit1}")
        print(f"✅ Créé: {audit2}")
        print(f"✅ Créé: {audit3}\n")
        
        # === SITES ===
        site1_1 = Site(
            nom="Siège social Paris",
            adresse="42 Avenue des Champs-Élysées, 75008 Paris",
            entreprise_id=entreprise1.id
        )
        
        site1_2 = Site(
            nom="Data Center Marseille",
            adresse="Zone Industrielle Nord, 13015 Marseille",
            entreprise_id=entreprise1.id
        )
        
        site2_1 = Site(
            nom="Siège Lyon",
            adresse="15 Rue de la Santé, 69003 Lyon",
            entreprise_id=entreprise2.id
        )
        
        site2_2 = Site(
            nom="Agence Bordeaux",
            adresse="8 Cours de l'Intendance, 33000 Bordeaux",
            entreprise_id=entreprise2.id
        )
        
        db.session.add_all([site1_1, site1_2, site2_1, site2_2])
        db.session.commit()
        print(f"✅ Créé: {site1_1}")
        print(f"✅ Créé: {site1_2}")
        print(f"✅ Créé: {site2_1}")
        print(f"✅ Créé: {site2_2}\n")
        
        # === ÉQUIPEMENTS RÉSEAU DU SITE 1 ===
        print("🔌 Création des équipements réseau...\n")
        
        switch1 = EquipementReseau(
            site_id=site1_1.id,
            ip_address="192.168.1.1",
            mac_address="AA:BB:CC:DD:EE:01",
            hostname="SWITCH-CORE-01",
            fabricant="Cisco",
            os_detected="Cisco IOS",
            status_audit=EquipementAuditStatus.CONFORME,
            vlan_config={"vlan_1": "Management", "vlan_10": "Data", "vlan_20": "VoIP"},
            ports_status={"port_1": "UP", "port_2": "UP", "port_3": "DOWN", "port_48": "UP"},
            firmware_version="15.2(4)M11",
            notes_audit="Switch validé lors du dernier audit"
        )
        
        routeur1 = EquipementReseau(
            site_id=site1_1.id,
            ip_address="192.168.1.254",
            mac_address="AA:BB:CC:DD:EE:02",
            hostname="ROUTER-CORE-01",
            fabricant="Juniper",
            os_detected="Junos OS",
            status_audit=EquipementAuditStatus.A_AUDITER,
            vlan_config={"vlan_1": "Management", "vlan_100": "DMZ"},
            ports_status={"port_0": "UP", "port_1": "UP"},
            firmware_version="18.1R3.10"
        )
        
        borne_wifi = EquipementReseau(
            site_id=site1_2.id,
            ip_address="10.0.1.1",
            mac_address="AA:BB:CC:DD:EE:03",
            hostname="BORNE-WIFI-01",
            fabricant="Ubiquiti",
            os_detected="UniFi OS",
            status_audit=EquipementAuditStatus.NON_CONFORME,
            vlan_config={"vlan_1": "Guest", "vlan_200": "Employees"},
            ports_status={"port_1": "UP"},
            firmware_version="5.14.23",
            notes_audit="Firmware à mettre à jour - Vulnérabilité CVE-2024-xxxx"
        )
        
        db.session.add_all([switch1, routeur1, borne_wifi])
        db.session.commit()
        print(f"✅ Créé: {switch1}")
        print(f"✅ Créé: {routeur1}")
        print(f"✅ Créé: {borne_wifi}\n")
        
        # === SERVEURS ===
        print("🖥️  Création des serveurs...\n")
        
        serveur_ad = EquipementServeur(
            site_id=site1_1.id,
            ip_address="172.16.0.10",
            mac_address="BB:CC:DD:EE:FF:01",
            hostname="DC-AD-01",
            fabricant="Dell",
            os_detected="Windows Server",
            status_audit=EquipementAuditStatus.CONFORME,
            os_version_detail="Windows Server 2022 Build 20348",
            role_list=["Active Directory", "DNS", "LDAP"],
            cpu_ram_info={"cpu_cores": 8, "ram_gb": 32, "cpu_model": "Intel Xeon E5-2620"},
            notes_audit="Serveur AD conforme aux standards de sécurité"
        )
        
        serveur_linux = EquipementServeur(
            site_id=site1_2.id,
            ip_address="10.0.2.50",
            mac_address="BB:CC:DD:EE:FF:02",
            hostname="WEB-SERVER-01",
            fabricant="HP",
            os_detected="Linux",
            status_audit=EquipementAuditStatus.A_AUDITER,
            os_version_detail="Ubuntu 22.04 LTS (Kernel 5.15.0-86)",
            role_list=["Web Server", "Application Server"],
            cpu_ram_info={"cpu_cores": 16, "ram_gb": 64, "cpu_model": "Intel Xeon Gold 6148"}
        )
        
        hyperviseur = EquipementServeur(
            site_id=site2_1.id,
            ip_address="172.17.0.1",
            mac_address="BB:CC:DD:EE:FF:03",
            hostname="HYPERV-HOST-01",
            fabricant="HP",
            os_detected="Windows Server Hyper-V",
            status_audit=EquipementAuditStatus.CONFORME,
            os_version_detail="Windows Server 2022 Datacenter Build 20348 with Hyper-V",
            role_list=["Hypervisor", "Virtual Machine Host"],
            cpu_ram_info={"cpu_cores": 32, "ram_gb": 256, "cpu_model": "Intel Xeon Platinum 8280"}
        )
        
        db.session.add_all([serveur_ad, serveur_linux, hyperviseur])
        db.session.commit()
        print(f"✅ Créé: {serveur_ad}")
        print(f"✅ Créé: {serveur_linux}")
        print(f"✅ Créé: {hyperviseur}\n")
        
        # === FIREWALLS ===
        print("🔥 Création des firewalls...\n")
        
        firewall_fg = EquipementFirewall(
            site_id=site1_1.id,
            ip_address="192.168.1.100",
            mac_address="CC:DD:EE:FF:00:01",
            hostname="FORTIGATE-FG100D",
            fabricant="Fortinet",
            os_detected="FortiOS",
            status_audit=EquipementAuditStatus.CONFORME,
            license_status="ACTIVE",
            vpn_users_count=42,
            rules_count=156,
            notes_audit="Licence renouvelée jusqu'à 2025-12-31"
        )
        
        firewall_palo = EquipementFirewall(
            site_id=site2_1.id,
            ip_address="172.17.0.254",
            mac_address="CC:DD:EE:FF:00:02",
            hostname="PALOALTO-PA220",
            fabricant="Palo Alto Networks",
            os_detected="PAN-OS",
            status_audit=EquipementAuditStatus.NON_CONFORME,
            license_status="EXPIRED",
            vpn_users_count=0,
            rules_count=89,
            notes_audit="⚠️ Licence expirée depuis 2024-01-15 - Renouvellement impératif"
        )
        
        db.session.add_all([firewall_fg, firewall_palo])
        db.session.commit()
        print(f"✅ Créé: {firewall_fg}")
        print(f"✅ Créé: {firewall_palo}\n")
        
        # === SCANS RÉSEAU ===
        print("🔍 Création des scans réseau...\n")
        
        scan1 = ScanReseau(
            site_id=site1_1.id,
            date_scan=datetime.now(timezone.utc) - timedelta(days=7),
            type_scan="NMAP",
            nombre_hosts_trouves=8,
            nombre_ports_ouverts=34,
            duree_scan_secondes=145,
            notes="Scan réalisé avec Nmap 7.92"
        )
        
        scan2 = ScanReseau(
            site_id=site1_2.id,
            date_scan=datetime.now(timezone.utc) - timedelta(days=3),
            type_scan="OPENVAS",
            nombre_hosts_trouves=12,
            nombre_ports_ouverts=28,
            duree_scan_secondes=320,
            notes="Openvas pour recherche de vulnérabilités"
        )
        
        scan3 = ScanReseau(
            site_id=site2_1.id,
            date_scan=datetime.now(timezone.utc) - timedelta(days=1),
            type_scan="QUALYS",
            nombre_hosts_trouves=15,
            nombre_ports_ouverts=45,
            duree_scan_secondes=450,
            notes="Scan Qualys complet du datacenter"
        )
        
        db.session.add_all([scan1, scan2, scan3])
        db.session.commit()
        print(f"✅ Créé: {scan1}")
        print(f"✅ Créé: {scan2}")
        print(f"✅ Créé: {scan3}\n")
        
        # === TEMPLATES DE CHECKLIST ===
        print("📋 Création des templates de checklist...\n")
        
        # Checklists Équipement Réseau
        checklist_reseau = [
            ChecklistTemplate(
                type_equipement='reseau',
                label='Vérifier la version du firmware',
                description='S\'assurer que le firmware est à jour et sécurisé',
                ordre=1
            ),
            ChecklistTemplate(
                type_equipement='reseau',
                label='Vérifier la configuration VLAN',
                description='Valider la segmentation réseau et l\'isolation des VLAN',
                ordre=2
            ),
            ChecklistTemplate(
                type_equipement='reseau',
                label='Vérifier les accès SSH/Telnet',
                description='S\'assurer que l\'accès management est sécurisé (SSH uniquement)',
                ordre=3
            ),
            ChecklistTemplate(
                type_equipement='reseau',
                label='Vérifier les ACL configurées',
                description='Contrôler les access lists et la politique de sécurité réseau',
                ordre=4
            ),
            ChecklistTemplate(
                type_equipement='reseau',
                label='Vérifier la disponibilité du SNMP',
                description='Vérifier les traps SNMP et la monitoring configurés',
                ordre=5
            ),
        ]
        
        # Checklists Serveur
        checklist_serveur = [
            ChecklistTemplate(
                type_equipement='serveur',
                label='Vérifier les mises à jour de sécurité',
                description='S\'assurer que tous les patches de sécurité sont installés',
                ordre=1
            ),
            ChecklistTemplate(
                type_equipement='serveur',
                label='Vérifier le firewall local',
                description='Valider la configuration du firewall Windows/Linux',
                ordre=2
            ),
            ChecklistTemplate(
                type_equipement='serveur',
                label='Vérifier les services en cours d\'exécution',
                description='Identifier et auditer les services non autorisés',
                ordre=3
            ),
            ChecklistTemplate(
                type_equipement='serveur',
                label='Vérifier la politique de mot de passe',
                description='Valider la force et la complexité des mot de passe',
                ordre=4
            ),
            ChecklistTemplate(
                type_equipement='serveur',
                label='Vérifier les logs et la monitoring',
                description='S\'assurer que logging et monitoring sont correctement configurés',
                ordre=5
            ),
            ChecklistTemplate(
                type_equipement='serveur',
                label='Vérifier les sauvegardes',
                description='Valider que les sauvegardes régulières sont en place',
                ordre=6
            ),
        ]
        
        # Checklists Firewall
        checklist_firewall = [
            ChecklistTemplate(
                type_equipement='firewall',
                label='Vérifier le statut de la licence',
                description='S\'assurer que la licence est valide et à jour',
                ordre=1
            ),
            ChecklistTemplate(
                type_equipement='firewall',
                label='Vérifier les règles de filtrage',
                description='Auditer les règles firewall et leur pertinence',
                ordre=2
            ),
            ChecklistTemplate(
                type_equipement='firewall',
                label='Vérifier la version du firmware',
                description='S\'assurer que la version est sécurisée et à jour',
                ordre=3
            ),
            ChecklistTemplate(
                type_equipement='firewall',
                label='Vérifier les VPN configurés',
                description='Valider la configuration des connexions VPN',
                ordre=4
            ),
            ChecklistTemplate(
                type_equipement='firewall',
                label='Vérifier les logs et alertes',
                description='S\'assurer que logging et alertes sont fonctionnels',
                ordre=5
            ),
            ChecklistTemplate(
                type_equipement='firewall',
                label='Vérifier les certificats SSL/TLS',
                description='Valider que les certificats ne sont pas expirés',
                ordre=6
            ),
            ChecklistTemplate(
                type_equipement='firewall',
                label='Vérifier la performance et les statistiques',
                description='Auditer le taux d\'utilisation et les performances',
                ordre=7
            ),
        ]
        
        db.session.add_all(checklist_reseau + checklist_serveur + checklist_firewall)
        db.session.commit()
        print(f"✅ Créé: {len(checklist_reseau)} templates Équipement Réseau")
        print(f"✅ Créé: {len(checklist_serveur)} templates Serveur")
        print(f"✅ Créé: {len(checklist_firewall)} templates Firewall\n")

        
        # === STATISTIQUES ===
        print("=" * 60)
        print("📈 RÉSUMÉ DES DONNÉES CRÉÉES")
        print("=" * 60)
        print(f"Entreprises                 : {Entreprise.query.count()}")
        print(f"Contacts                    : {Contact.query.count()}")
        print(f"Audits                      : {Audit.query.count()}")
        print(f"Sites                       : {Site.query.count()}")
        print(f"Équipements Réseau          : {EquipementReseau.query.count()}")
        print(f"Serveurs                    : {EquipementServeur.query.count()}")
        print(f"Firewalls                   : {EquipementFirewall.query.count()}")
        print(f"Total Équipements           : {Equipement.query.count()}")
        print(f"Scans Réseau                : {ScanReseau.query.count()}")
        print(f"Templates de Checklist      : {ChecklistTemplate.query.count()}")

        print()
        
        # === EXEMPLES DE REQUÊTES ===
        print("=" * 60)
        print("🔍 EXEMPLES DE REQUÊTES")
        print("=" * 60)
        
        # Tous les audits en cours
        audits_en_cours = Audit.query.filter_by(status=AuditStatus.EN_COURS).all()
        print(f"\n📋 Audits en cours ({len(audits_en_cours)}):")
        for audit in audits_en_cours:
            print(f"   - {audit.nom_projet} (Entreprise: {audit.entreprise.nom})")
        
        # Contacts principaux
        contacts_principaux = Contact.query.filter_by(is_main_contact=True).all()
        print(f"\n👥 Contacts principaux ({len(contacts_principaux)}):")
        for contact in contacts_principaux:
            print(f"   - {contact.nom} ({contact.role}) - {contact.entreprise.nom}")
        
        # Entreprises avec leurs sites
        print(f"\n🏢 Entreprises et leurs sites:")
        for entreprise in Entreprise.query.all():
            print(f"   {entreprise.nom}:")
            for site in entreprise.sites:
                print(f"      → {site.nom}")
        
        # Équipements par statut d'audit
        print(f"\n🔌 Équipements par statut:")
        for status in [EquipementAuditStatus.CONFORME, EquipementAuditStatus.A_AUDITER, EquipementAuditStatus.NON_CONFORME]:
            equipements = Equipement.query.filter_by(status_audit=status).all()
            print(f"   {status.value}: {len(equipements)} équipement(s)")
            for eq in equipements[:2]:  # Affiche les 2 premiers
                print(f"      - {eq.hostname} ({eq.type_equipement}) - {eq.ip_address}")
        
        # Serveurs et leurs rôles
        print(f"\n🖥️  Serveurs et leurs rôles:")
        serveurs = EquipementServeur.query.all()
        for serveur in serveurs:
            roles = ", ".join(serveur.role_list) if serveur.role_list else "Aucun rôle"
            print(f"   - {serveur.hostname}: {roles}")
        
        # Firewalls avec statut de licence
        print(f"\n🔥 Firewalls et statut de licence:")
        firewalls = EquipementFirewall.query.all()
        for fw in firewalls:
            vpn_info = f" ({fw.vpn_users_count} utilisateurs VPN)" if fw.vpn_users_count > 0 else ""
            print(f"   - {fw.hostname}: {fw.license_status}{vpn_info}")
        
        # Scans réseau les plus récents
        print(f"\n🔍 Scans réseau (les plus récents):")
        scans = ScanReseau.query.order_by(ScanReseau.date_scan.desc()).limit(3).all()
        for scan in scans:
            site_name = scan.site.nom if scan.site else "Inconnu"
            print(f"   - {scan.date_scan.strftime('%Y-%m-%d %H:%M')}: {scan.type_scan} ({site_name}) - "
                  f"{scan.nombre_hosts_trouves} hosts, {scan.nombre_ports_ouverts} ports ouverts")
        
        print("\n" + "=" * 60)
        print("✅ Base de données initialisée avec succès!")
        print("=" * 60)


if __name__ == '__main__':
    init_sample_data()
