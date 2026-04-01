"""Seed de la checklist protocole de départ du site (PROJECT-BRIEF §4.3)."""

import os
import sys

# Ajouter le répertoire backend au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.checklist import ChecklistItem, ChecklistSection, ChecklistTemplate

CHECKLIST_DEPARTURE = {
    "name": "Protocole de départ du site",
    "category": "departure",
    "description": "Checklist avant de quitter le client (brief §4.3)",
    "sections": [
        {
            "name": "Validation des informations",
            "order": 0,
            "items": [
                {"ref": "1.1", "label": "Informations collectées validées avec l'interlocuteur technique"},
                {"ref": "1.2", "label": "Résultats préliminaires communiqués au client"},
                {"ref": "1.3", "label": "Points de désaccord ou incompréhension clarifiés"},
            ],
        },
        {
            "name": "Zones d'ombre",
            "order": 1,
            "items": [
                {"ref": "2.1", "label": "Liste des points non vérifiés établie avec justification"},
                {"ref": "2.2", "label": "Informations manquantes identifiées et demandées au client"},
                {"ref": "2.3", "label": "Accès non obtenus documentés"},
            ],
        },
        {
            "name": "Prochaines étapes",
            "order": 2,
            "items": [
                {"ref": "3.1", "label": "Prochaines étapes expliquées au client"},
                {"ref": "3.2", "label": "Date de restitution planifiée et communiquée"},
                {"ref": "3.3", "label": "Délai de livraison du rapport communiqué"},
                {"ref": "3.4", "label": "Modalités de suivi convenues (email, réunion, etc.)"},
            ],
        },
        {
            "name": "Preuves et collecte",
            "order": 3,
            "items": [
                {"ref": "4.1", "label": "Toutes les photos prises et rattachées dans l'outil"},
                {"ref": "4.2", "label": "Toutes les captures d'écran enregistrées"},
                {"ref": "4.3", "label": "Exports de configuration collectés (firewall, switches, etc.)"},
                {"ref": "4.4", "label": "Checklists terrain complétées (LAN, salle serveur, documentation)"},
                {"ref": "4.5", "label": "Scans réseau terminés et résultats récupérés"},
            ],
        },
        {
            "name": "Logistique",
            "order": 4,
            "items": [
                {"ref": "5.1", "label": "Agent local désinstallé ou laissé en place (selon accord)"},
                {"ref": "5.2", "label": "Accès temporaires fournis au client révoqués ou planifiés pour révocation"},
                {"ref": "5.3", "label": "Matériel personnel récupéré"},
            ],
        },
    ],
}


def seed(db=None):
    """Crée la checklist protocole de départ. Idempotent si déjà présente."""
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        existing = db.query(ChecklistTemplate).filter(
            ChecklistTemplate.name == CHECKLIST_DEPARTURE["name"]
        ).first()

        if existing:
            print(
                f"Checklist '{CHECKLIST_DEPARTURE['name']}' déjà présente "
                f"(id={existing.id}), rien à faire."
            )
            return

        tpl = ChecklistTemplate(
            name=CHECKLIST_DEPARTURE["name"],
            category=CHECKLIST_DEPARTURE["category"],
            description=CHECKLIST_DEPARTURE["description"],
            is_predefined=True,
        )
        db.add(tpl)
        db.flush()

        total_items = 0
        for sec_data in CHECKLIST_DEPARTURE["sections"]:
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
            f"{len(CHECKLIST_DEPARTURE['sections'])} sections, {total_items} items."
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
