"""Seed de la checklist terrain LAN (PROJECT-BRIEF §4.2)."""

import os
import sys

# Ajouter le répertoire backend au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, SessionLocal, engine
from app.models.checklist import ChecklistItem, ChecklistSection, ChecklistTemplate

CHECKLIST_LAN = {
    "name": "Checklist terrain LAN",
    "category": "lan",
    "description": "Checklist structurée pour audit terrain réseau local (brief §4.2)",
    "sections": [
        {
            "name": "Architecture réseau globale",
            "order": 0,
            "items": [
                {"ref": "1.1", "label": "Accès internet principal identifié (fibre / xDSL / 4G / satellite / autre)"},
                {"ref": "1.2", "label": "Lien de secours présent"},
                {"ref": "1.3", "label": "Firewall / routeur identifié"},
                {"ref": "1.4", "label": "Switch cœur identifié"},
                {"ref": "1.5", "label": "Segmentation réseau présente (VLANs)"},
                {"ref": "1.6", "label": "Schéma mental : Internet → Firewall → Core → Accès / Wi-Fi"},
            ],
        },
        {
            "name": "Équipements réseau (inventaire rapide)",
            "order": 1,
            "items": [
                {"ref": "2.1", "label": "Pare-feu / routeur : modèle, constructeur, firmware, IP management, accès admin fonctionnel"},
                {"ref": "2.2", "label": "Switch cœur : modèle, IP, VLANs trunk, STP/LACP"},
                {"ref": "2.3", "label": "Switches d'accès : nombre, VLANs port access, PoE, administration centralisée"},
                {"ref": "2.4", "label": "Wi-Fi : contrôleur, AP standalone/managés, SSID internes/invités, séparation Wi-Fi/LAN"},
            ],
        },
        {
            "name": "IPAM / VLANs",
            "order": 2,
            "items": [
                {"ref": "3.1", "label": "VLAN ID, nom, usage (Users/Servers/WiFi/VoIP/Mgmt) identifié pour chaque VLAN"},
                {"ref": "3.2", "label": "Subnet associé, DHCP (où ?), routage inter-VLAN maîtrisé"},
                {"ref": "3.3", "label": "Incohérences : VLAN sans subnet, subnet sans VLAN, chevauchements IP, DHCP non documenté"},
            ],
        },
        {
            "name": "Services réseau critiques",
            "order": 3,
            "items": [
                {"ref": "4.1", "label": "DHCP : serveur(s), redondance"},
                {"ref": "4.2", "label": "DNS : serveur(s), zones, résolution fonctionnelle"},
                {"ref": "4.3", "label": "NTP : source de temps configurée"},
                {"ref": "4.4", "label": "AD / LDAP : contrôleur(s) de domaine"},
                {"ref": "4.5", "label": "Serveurs critiques identifiés (métier, fichiers, messagerie)"},
            ],
        },
        {
            "name": "Sécurité (check rapide)",
            "order": 4,
            "items": [
                {"ref": "5.1", "label": "VLAN management isolé"},
                {"ref": "5.2", "label": "Accès admin restreint"},
                {"ref": "5.3", "label": "Flux inter-VLAN filtrés"},
                {"ref": "5.4", "label": "Interfaces d'admin non exposées sur internet"},
                {"ref": "5.5", "label": "Services obsolètes absents (SMBv1, Telnet, FTP)"},
                {"ref": "5.6", "label": "Accès distant sécurisé (VPN)"},
                {"ref": "5.7", "label": "Pas de mots de passe partagés / comptes génériques"},
                {"ref": "5.8", "label": "Sauvegarde config réseau existante"},
            ],
        },
        {
            "name": "Performance & disponibilité",
            "order": 5,
            "items": [
                {"ref": "6.1", "label": "Saturation LAN non observée"},
                {"ref": "6.2", "label": "Boucles réseau non suspectes"},
                {"ref": "6.3", "label": "SPOF identifiés (single point of failure)"},
                {"ref": "6.4", "label": "Supervision existante (outil, couverture)"},
            ],
        },
        {
            "name": "Shadow IT",
            "order": 6,
            "items": [
                {"ref": "7.1", "label": "Switches non managés non détectés"},
                {"ref": "7.2", "label": "Access points personnels (AP sauvages) non détectés"},
                {"ref": "7.3", "label": "Routeurs 4G non déclarés absents"},
                {"ref": "7.4", "label": "Matériel inconnu sur le LAN non détecté"},
                {"ref": "7.5", "label": "Tout équipement hors inventaire officiel absent"},
            ],
        },
        {
            "name": "Points forts observés",
            "order": 7,
            "items": [
                {"ref": "8.1", "label": "Architecture claire et documentée"},
                {"ref": "8.2", "label": "Segmentation cohérente"},
                {"ref": "8.3", "label": "Matériel homogène et à jour"},
                {"ref": "8.4", "label": "Bon niveau de sécurité général"},
                {"ref": "8.5", "label": "Bonnes pratiques déjà en place (détailler lesquelles)"},
            ],
        },
        {
            "name": "Quick wins identifiés",
            "order": 8,
            "items": [
                {"ref": "9.1", "label": "Séparation VLAN management si non fait"},
                {"ref": "9.2", "label": "Mise à jour firmware si obsolète"},
                {"ref": "9.3", "label": "Désactivation services obsolètes si présents"},
                {"ref": "9.4", "label": "Documentation IP/VLAN si inexistante"},
                {"ref": "9.5", "label": "Activation MFA si non fait"},
            ],
        },
    ],
}


def seed_checklist_lan():
    db = SessionLocal()
    try:
        # Idempotent : ne crée pas si le template existe déjà
        existing = db.query(ChecklistTemplate).filter(
            ChecklistTemplate.name == CHECKLIST_LAN["name"]
        ).first()

        if existing:
            print(f"Checklist '{CHECKLIST_LAN['name']}' déjà présente (id={existing.id}), rien à faire.")
            return

        tpl = ChecklistTemplate(
            name=CHECKLIST_LAN["name"],
            category=CHECKLIST_LAN["category"],
            description=CHECKLIST_LAN["description"],
            is_predefined=True,
        )
        db.add(tpl)
        db.flush()

        total_items = 0
        for sec_data in CHECKLIST_LAN["sections"]:
            section = ChecklistSection(
                template_id=tpl.id,
                name=sec_data["name"],
                order=sec_data["order"],
            )
            db.add(section)
            db.flush()

            for idx, item_data in enumerate(sec_data["items"]):
                item = ChecklistItem(
                    section_id=section.id,
                    label=item_data["label"],
                    ref_code=item_data["ref"],
                    order=idx,
                )
                db.add(item)
                total_items += 1

        db.commit()
        print(
            f"Checklist '{tpl.name}' créée (id={tpl.id}) — "
            f"{len(CHECKLIST_LAN['sections'])} sections, {total_items} items."
        )
    except Exception as e:
        db.rollback()
        print(f"Erreur lors du seed : {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_checklist_lan()
