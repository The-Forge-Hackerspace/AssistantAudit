"""
Point d'entrée de l'application AssistantAudit
"""
from app import create_app, db
from app.models import (
    User, Entreprise, Contact, Audit, Site,
    Equipement, EquipementReseau, EquipementServeur, EquipementFirewall,
    ScanReseau, ScanHost, ScanPort, ChecklistTemplate, EquipementChecklist
)

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Rend les modèles disponibles dans le shell Flask"""
    return {
        'db': db,
        'User': User,
        'Entreprise': Entreprise,
        'Contact': Contact,
        'Audit': Audit,
        'Site': Site,
        'Equipement': Equipement,
        'ScanReseau': ScanReseau,
    }


if __name__ == '__main__':
    app.run(debug=True)
