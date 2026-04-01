"""Seed de la checklist salle serveur / locaux techniques (PROJECT-BRIEF §6.13)."""

import os
import sys

# Ajouter le répertoire backend au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.checklist import ChecklistItem, ChecklistSection, ChecklistTemplate

CHECKLIST_SERVER_ROOM = {
    "name": "Checklist salle serveur / locaux techniques",
    "category": "server_room",
    "description": "Grille d'évaluation salle serveur avec scoring par criticité (brief §6.13)",
    "sections": [
        {
            "name": "Environnement",
            "order": 0,
            "items": [
                {"ref": "1.1", "label": "Climatisation dédiée présente et fonctionnelle"},
                {"ref": "1.2", "label": "Température maintenue entre 18°C et 27°C"},
                {"ref": "1.3", "label": "Humidité contrôlée (40-60%)"},
                {"ref": "1.4", "label": "Monitoring température/humidité en place"},
                {"ref": "1.5", "label": "Alertes en cas de dépassement de seuil configurées"},
                {"ref": "1.6", "label": "Climatisation redondante (N+1)"},
            ],
        },
        {
            "name": "Alimentation électrique",
            "order": 1,
            "items": [
                {"ref": "2.1", "label": "Onduleur (UPS) présent et fonctionnel"},
                {"ref": "2.2", "label": "Autonomie onduleur documentée et suffisante (>15 min)"},
                {"ref": "2.3", "label": "Agent d'arrêt automatique configuré (PowerChute ou équivalent)"},
                {"ref": "2.4", "label": "Self-test onduleur récent et réussi"},
                {"ref": "2.5", "label": "Date de remplacement batterie respectée"},
                {"ref": "2.6", "label": "Groupe électrogène présent"},
                {"ref": "2.7", "label": "PDU (Power Distribution Unit) organisées et identifiées"},
                {"ref": "2.8", "label": "Double alimentation serveurs (si disponible)"},
            ],
        },
        {
            "name": "Sécurité physique",
            "order": 2,
            "items": [
                {"ref": "3.1", "label": "Accès restreint (clé, badge, code, biométrie)"},
                {"ref": "3.2", "label": "Journal d'accès tenu (physique ou électronique)"},
                {"ref": "3.3", "label": "Caméra de surveillance en place"},
                {"ref": "3.4", "label": "Porte fermée en permanence"},
                {"ref": "3.5", "label": "Pas de stockage de matériel non informatique"},
                {"ref": "3.6", "label": "Accès visiteurs accompagnés uniquement"},
            ],
        },
        {
            "name": "Protection incendie",
            "order": 3,
            "items": [
                {"ref": "4.1", "label": "Détection incendie présente et fonctionnelle"},
                {"ref": "4.2", "label": "Extinction automatique (gaz inerte) ou manuelle (extincteur CO2)"},
                {"ref": "4.3", "label": "Extincteur accessible et date de vérification à jour"},
                {"ref": "4.4", "label": "Pas de matériaux inflammables dans la salle"},
            ],
        },
        {
            "name": "Câblage et organisation",
            "order": 4,
            "items": [
                {"ref": "5.1", "label": "Câblage organisé et identifié (étiquettes)"},
                {"ref": "5.2", "label": "Tiroirs optiques et bandeaux de brassage en bon état"},
                {"ref": "5.3", "label": "Séparation courants forts / courants faibles"},
                {"ref": "5.4", "label": "Chemins de câbles utilisés (pas de câbles au sol)"},
                {"ref": "5.5", "label": "Baies identifiées (numérotation, étiquetage)"},
            ],
        },
        {
            "name": "Redondance",
            "order": 5,
            "items": [
                {"ref": "6.1", "label": "Liens réseau redondants (uplink, trunk)"},
                {"ref": "6.2", "label": "Alimentation redondante (double PDU, double UPS)"},
                {"ref": "6.3", "label": "Climatisation redondante"},
                {"ref": "6.4", "label": "Stockage redondant (RAID, réplication)"},
            ],
        },
        {
            "name": "Documentation salle",
            "order": 6,
            "items": [
                {"ref": "7.1", "label": "Plan de salle à jour (disposition des baies)"},
                {"ref": "7.2", "label": "Inventaire du contenu de chaque baie documenté"},
                {"ref": "7.3", "label": "Procédure d'arrêt/redémarrage documentée"},
                {"ref": "7.4", "label": "Procédure d'accès en urgence documentée"},
                {"ref": "7.5", "label": "Contrats de maintenance identifiés et à jour"},
            ],
        },
    ],
}


def seed(db=None):
    """Crée la checklist salle serveur. Idempotent si déjà présente."""
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        existing = db.query(ChecklistTemplate).filter(
            ChecklistTemplate.name == CHECKLIST_SERVER_ROOM["name"]
        ).first()

        if existing:
            print(
                f"Checklist '{CHECKLIST_SERVER_ROOM['name']}' déjà présente "
                f"(id={existing.id}), rien à faire."
            )
            return

        tpl = ChecklistTemplate(
            name=CHECKLIST_SERVER_ROOM["name"],
            category=CHECKLIST_SERVER_ROOM["category"],
            description=CHECKLIST_SERVER_ROOM["description"],
            is_predefined=True,
        )
        db.add(tpl)
        db.flush()

        total_items = 0
        for sec_data in CHECKLIST_SERVER_ROOM["sections"]:
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
            f"{len(CHECKLIST_SERVER_ROOM['sections'])} sections, {total_items} items."
        )
    except Exception as e:
        db.rollback()
        print(f"Erreur lors du seed : {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if close_after:
            db.close()


if __name__ == "__main__":
    seed()
