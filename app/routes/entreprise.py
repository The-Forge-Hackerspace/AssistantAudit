"""
Routes de gestion des entreprises : CRUD
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import Entreprise
from app.utils import validate_file_type, handle_file_upload, validate_siret

logger = logging.getLogger(__name__)

entreprise_bp = Blueprint('entreprise', __name__)


@entreprise_bp.route('/entreprises')
@login_required
def liste_entreprises():
    """Liste toutes les entreprises"""
    entreprises = Entreprise.query.order_by(Entreprise.nom).all()
    return render_template('liste_entreprises.html', entreprises=entreprises)


@entreprise_bp.route('/entreprise/<int:entreprise_id>')
@login_required
def entreprise_detail(entreprise_id):
    """Détails d'une entreprise"""
    entreprise = Entreprise.query.get_or_404(entreprise_id)
    audits = entreprise.audits.all()
    contacts = entreprise.contacts.all()
    sites = entreprise.sites.all()

    return render_template(
        'entreprise_detail.html',
        entreprise=entreprise,
        audits=audits,
        contacts=contacts,
        sites=sites
    )


@entreprise_bp.route('/entreprise/<int:entreprise_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_entreprise(entreprise_id):
    """Modifier les informations d'une entreprise"""
    entreprise = Entreprise.query.get_or_404(entreprise_id)

    if request.method == 'POST':
        try:
            new_nom = request.form.get('nom', '').strip()

            # Validation du nom
            if not new_nom:
                flash('Le nom de l\'entreprise est requis.', 'danger')
                return redirect(url_for('entreprise.modifier_entreprise', entreprise_id=entreprise_id))

            # Vérification d'unicité du nom
            existing = Entreprise.query.filter(
                Entreprise.nom == new_nom, Entreprise.id != entreprise.id
            ).first()
            if existing:
                flash(f'Une entreprise avec le nom "{new_nom}" existe déjà.', 'danger')
                return redirect(url_for('entreprise.modifier_entreprise', entreprise_id=entreprise_id))

            entreprise.nom = new_nom
            entreprise.adresse = request.form.get('adresse', '')
            entreprise.secteur_activite = request.form.get('secteur_activite', '')
            entreprise.presentation_desc = request.form.get('presentation_desc', '')
            entreprise.contraintes_reglementaires = request.form.get('contraintes_reglementaires', '')

            # Validation du SIRET
            siret = request.form.get('siret', '').strip() or None
            siret_valid, siret_error = validate_siret(siret)
            if not siret_valid:
                flash(f'❌ {siret_error}', 'danger')
                return redirect(url_for('entreprise.modifier_entreprise', entreprise_id=entreprise_id))
            entreprise.siret = siret

            # Upload d'un nouvel organigramme si fourni
            organigramme_path, org_error = handle_file_upload(
                request, 'organigramme', 'image', 'entreprises'
            )
            if org_error:
                flash(f'❌ {org_error}', 'danger')
                return redirect(url_for('entreprise.modifier_entreprise', entreprise_id=entreprise_id))
            if organigramme_path:
                entreprise.organigramme_path = organigramme_path

            db.session.commit()
            logger.info(f'Entreprise modifiée: "{entreprise.nom}" (id={entreprise_id})')
            flash(f'✅ Entreprise "{entreprise.nom}" mise à jour avec succès !', 'success')
            return redirect(url_for('entreprise.entreprise_detail', entreprise_id=entreprise.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification de l\'entreprise: {str(e)}', exc_info=True)
            flash('Erreur lors de la mise à jour. Veuillez réessayer.', 'danger')
            return redirect(url_for('entreprise.modifier_entreprise', entreprise_id=entreprise_id))

    return render_template('modifier_entreprise.html', entreprise=entreprise)
