"""
Routes principales : accueil et pages générales
"""
import logging
from flask import Blueprint, render_template
from flask_login import login_required
from app import db
from app.models import Audit, Entreprise, AuditStatus

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    """Page d'accueil - Liste des audits avec statistiques"""
    audits = Audit.query.order_by(Audit.date_debut.desc()).all()
    entreprises = Entreprise.query.all()

    # Calculer les statistiques depuis les données déjà chargées
    stats = {
        'total_audits': len(audits),
        'audits_en_cours': sum(1 for a in audits if a.status == AuditStatus.EN_COURS),
        'audits_nouveaux': sum(1 for a in audits if a.status == AuditStatus.NOUVEAU),
        'total_entreprises': len(entreprises)
    }

    return render_template('index.html', audits=audits, entreprises=entreprises, stats=stats)
