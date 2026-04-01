"""Seed des 8 tags prédéfinis (PROJECT-BRIEF §5)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.tag import Tag

PREDEFINED_TAGS = [
    {"name": "critical",      "color": "#EF4444", "scope": "global"},  # Rouge
    {"name": "legacy",        "color": "#F97316", "scope": "global"},  # Orange
    {"name": "quick-win",     "color": "#10B981", "scope": "global"},  # Vert
    {"name": "shadow-it",     "color": "#8B5CF6", "scope": "global"},  # Violet
    {"name": "unmanaged",     "color": "#6B7280", "scope": "global"},  # Gris
    {"name": "to-verify",     "color": "#3B82F6", "scope": "global"},  # Bleu
    {"name": "compliant",     "color": "#22C55E", "scope": "global"},  # Vert
    {"name": "non-compliant", "color": "#EF4444", "scope": "global"},  # Rouge
]


def seed():
    db = SessionLocal()
    try:
        created = 0
        for tag_data in PREDEFINED_TAGS:
            existing = db.query(Tag).filter(
                Tag.name == tag_data["name"], Tag.scope == "global"
            ).first()
            if not existing:
                db.add(Tag(**tag_data))
                created += 1
                print(f"  Créé: {tag_data['name']} ({tag_data['color']})")
            else:
                print(f"  Existe: {tag_data['name']}")
        db.commit()
        print(f"\nSeed terminé: {created} tags créés")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
