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
    page = 1
    audits = Audit.query.order_by(Audit.date_debut.desc()).all()
    entreprises = Entreprise.query.all()

    stats = {
        'total_audits': Audit.query.count(),
        'audits_en_cours': Audit.query.filter_by(status=AuditStatus.EN_COURS).count(),
        'audits_nouveaux': Audit.query.filter_by(status=AuditStatus.NOUVEAU).count(),
        'total_entreprises': Entreprise.query.count()
    }

    return render_template('index.html', audits=audits, entreprises=entreprises, stats=stats)
