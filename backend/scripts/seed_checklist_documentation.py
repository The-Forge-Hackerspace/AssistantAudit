"""Seed de la checklist documentation & outils internes (PROJECT-BRIEF §6.16)."""

import os
import sys

# Ajouter le répertoire backend au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.checklist import ChecklistItem, ChecklistSection, ChecklistTemplate

CHECKLIST_DOCUMENTATION = {
    "name": "Checklist documentation & outils internes",
    "category": "documentation",
    "description": "Questionnaire auditeur sur la documentation et les outils en place (brief §6.16)",
    "sections": [
        {
            "name": "Documentation réseau",
            "order": 0,
            "items": [
                {"ref": "1.1", "label": "Synoptique réseau existant"},
                {"ref": "1.2", "label": "Synoptique réseau à jour (moins de 6 mois)"},
                {"ref": "1.3", "label": "Plan d'adressage IP documenté"},
                {"ref": "1.4", "label": "Inventaire VLAN documenté"},
            ],
        },
        {
            "name": "Gestion de parc & supervision",
            "order": 1,
            "items": [
                {"ref": "2.1", "label": "Outil de gestion de parc déployé"},
                {"ref": "2.2", "label": "Couverture complète (tous les postes, serveurs, équipements réseau)"},
                {"ref": "2.3", "label": "Outil de supervision déployé (Zabbix, PRTG, etc.)"},
                {"ref": "2.4", "label": "Alertes de supervision configurées et opérationnelles"},
                {"ref": "2.5", "label": "Agents de supervision installés sur tous les équipements critiques"},
            ],
        },
        {
            "name": "Procédures & gouvernance",
            "order": 2,
            "items": [
                {"ref": "3.1", "label": "Procédure d'entrée des collaborateurs formalisée (onboarding IT)"},
                {"ref": "3.2", "label": "Procédure de sortie des collaborateurs formalisée (offboarding IT)"},
                {"ref": "3.3", "label": "Charte informatique existante et signée"},
                {"ref": "3.4", "label": "Politique de mots de passe documentée"},
                {"ref": "3.5", "label": "Registre des incidents de sécurité tenu"},
            ],
        },
        {
            "name": "Continuité d'activité",
            "order": 3,
            "items": [
                {"ref": "4.1", "label": "PRA (Plan de Reprise d'Activité) documenté"},
                {"ref": "4.2", "label": "PCA (Plan de Continuité d'Activité) documenté"},
                {"ref": "4.3", "label": "PRA/PCA testé dans les 12 derniers mois"},
                {"ref": "4.4", "label": "Contacts d'urgence identifiés et à jour"},
            ],
        },
        {
            "name": "Contrats & maintenance",
            "order": 4,
            "items": [
                {"ref": "5.1", "label": "Contrats de maintenance à jour"},
                {"ref": "5.2", "label": "SLA définis avec les prestataires critiques"},
                {"ref": "5.3", "label": "Garanties matérielles suivies (dates expiration connues)"},
                {"ref": "5.4", "label": "Licences logicielles inventoriées et conformes"},
            ],
        },
    ],
}


def seed(db=None):
    """Crée la checklist documentation. Idempotent si déjà présente."""
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        existing = db.query(ChecklistTemplate).filter(
            ChecklistTemplate.name == CHECKLIST_DOCUMENTATION["name"]
        ).first()

        if existing:
            print(
                f"Checklist '{CHECKLIST_DOCUMENTATION['name']}' déjà présente "
                f"(id={existing.id}), rien à faire."
            )
            return

        tpl = ChecklistTemplate(
            name=CHECKLIST_DOCUMENTATION["name"],
            category=CHECKLIST_DOCUMENTATION["category"],
            description=CHECKLIST_DOCUMENTATION["description"],
            is_predefined=True,
        )
        db.add(tpl)
        db.flush()

        total_items = 0
        for sec_data in CHECKLIST_DOCUMENTATION["sections"]:
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
            f"{len(CHECKLIST_DOCUMENTATION['sections'])} sections, {total_items} items."
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
