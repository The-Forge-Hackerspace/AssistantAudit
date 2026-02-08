"""
Routes de gestion des audits : CRUD, changement de statut, sites
"""
import logging
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import Audit, Entreprise, Contact, Site, AuditStatus
from app.utils import (
    validate_contacts, validate_file_type, validate_siret,
    create_audit_folder_structure, save_uploaded_file, handle_file_upload
)

logger = logging.getLogger(__name__)

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/nouveau-projet', methods=['GET', 'POST'])
@login_required
def nouveau_projet():
    """
    Formulaire multi-étapes pour créer un nouveau projet d'audit

    Étape 1: Informations Entreprise
    Étape 2: Contacts Clés (avec validation contact principal)
    Étape 3: Cadrage Audit (avec validation types de fichiers)
    """
    if request.method == 'POST':
        try:
            # === VALIDATION DES CONTACTS ===
            contacts_valid, contact_error = validate_contacts(request.form)
            if not contacts_valid:
                flash(f'❌ {contact_error}', 'danger')
                return redirect(url_for('audit.nouveau_projet'))

            # === ÉTAPE 1 : CRÉATION ENTREPRISE ===

            # Vérifier si l'entreprise existe déjà
            entreprise_id = request.form.get('entreprise_id')

            if entreprise_id:
                # Utiliser une entreprise existante
                entreprise = db.session.get(Entreprise, entreprise_id)
                if not entreprise:
                    flash('Entreprise non trouvée.', 'danger')
                    return redirect(url_for('audit.nouveau_projet'))
            else:
                # Créer une nouvelle entreprise
                nom_entreprise = request.form.get('nom_entreprise', '').strip()

                if not nom_entreprise:
                    flash("Le nom de l'entreprise est requis.", 'danger')
                    return redirect(url_for('audit.nouveau_projet'))

                # Validation du SIRET
                siret = request.form.get('siret', '').strip() or None
                siret_valid, siret_error = validate_siret(siret)
                if not siret_valid:
                    flash(f'❌ {siret_error}', 'danger')
                    return redirect(url_for('audit.nouveau_projet'))

                # Vérifier si l'entreprise existe déjà
                existing = Entreprise.query.filter_by(nom=nom_entreprise).first()
                if existing:
                    flash(f'L\'entreprise "{nom_entreprise}" existe déjà.', 'warning')
                    entreprise = existing
                else:
                    # Upload de l'organigramme
                    organigramme_path, org_error = handle_file_upload(
                        request, 'organigramme', 'image', 'entreprises'
                    )
                    if org_error:
                        flash(f'❌ {org_error}', 'danger')
                        return redirect(url_for('audit.nouveau_projet'))

                    entreprise = Entreprise(
                        nom=nom_entreprise,
                        adresse=request.form.get('adresse', ''),
                        secteur_activite=request.form.get('secteur_activite', ''),
                        siret=siret,
                        presentation_desc=request.form.get('presentation_desc', ''),
                        contraintes_reglementaires=request.form.get('contraintes_reglementaires', ''),
                        organigramme_path=organigramme_path
                    )

                    db.session.add(entreprise)
                    db.session.flush()  # Pour obtenir l'ID

            # === CRÉER LA STRUCTURE DE DOSSIERS POUR L'AUDIT ===
            audit_folder = create_audit_folder_structure(entreprise.nom, datetime.now())

            # === ÉTAPE 2 : CRÉATION CONTACTS ===

            contact_index = 0
            contacts_created = 0

            while True:
                nom_contact = request.form.get(f'contact_nom_{contact_index}', '').strip()

                if not nom_contact:
                    break

                contact = Contact(
                    nom=nom_contact,
                    role=request.form.get(f'contact_role_{contact_index}', ''),
                    email=request.form.get(f'contact_email_{contact_index}', ''),
                    telephone=request.form.get(f'contact_telephone_{contact_index}', ''),
                    is_main_contact=request.form.get(f'contact_principal_{contact_index}') == 'on',
                    entreprise_id=entreprise.id
                )

                db.session.add(contact)
                contacts_created += 1
                contact_index += 1

            # === ÉTAPE 3 : CRÉATION AUDIT ===

            nom_projet = request.form.get('nom_projet', '').strip()

            if not nom_projet:
                flash('Le nom du projet est requis.', 'danger')
                return redirect(url_for('audit.nouveau_projet'))

            # Upload des fichiers administratifs de manière centralisée
            admin_folder = f'{audit_folder}/bloc_01_administratif'

            lettre_mission_path, lm_error = handle_file_upload(
                request, 'lettre_mission', 'pdf', admin_folder
            )
            if lm_error:
                flash(f'❌ {lm_error}', 'danger')
                return redirect(url_for('audit.nouveau_projet'))

            contrat_path, c_error = handle_file_upload(
                request, 'contrat', 'pdf', admin_folder
            )
            if c_error:
                flash(f'❌ {c_error}', 'danger')
                return redirect(url_for('audit.nouveau_projet'))

            planning_path, p_error = handle_file_upload(
                request, 'planning', 'spreadsheet', admin_folder
            )
            if p_error:
                flash(f'❌ {p_error}', 'danger')
                return redirect(url_for('audit.nouveau_projet'))

            # Création de l'audit
            audit = Audit(
                nom_projet=nom_projet,
                status=AuditStatus.NOUVEAU,
                entreprise_id=entreprise.id,
                lettre_mission_path=lettre_mission_path,
                contrat_path=contrat_path,
                planning_path=planning_path,
                objectifs=request.form.get('objectifs', ''),
                limites=request.form.get('limites', ''),
                hypotheses=request.form.get('hypotheses', ''),
                risques_initiaux=request.form.get('risques_initiaux', '')
            )

            db.session.add(audit)
            db.session.commit()

            logger.info(f'Projet d\'audit créé: "{nom_projet}" (id={audit.id})')
            flash(f'✅ Projet d\'audit "{nom_projet}" créé avec succès ! ({contacts_created} contact(s) ajouté(s))', 'success')
            flash(f'📁 Dossier audit créé : {audit_folder}/', 'info')
            return redirect(url_for('audit.audit_detail', audit_id=audit.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la création du projet: {str(e)}', exc_info=True)
            flash(f'❌ Erreur lors de la création du projet : {str(e)}', 'danger')
            return redirect(url_for('audit.nouveau_projet'))

    # GET - Affichage du formulaire
    entreprises = Entreprise.query.order_by(Entreprise.nom).all()
    return render_template('nouveau_projet.html', entreprises=entreprises)


@audit_bp.route('/audit/<int:audit_id>')
@login_required
def audit_detail(audit_id):
    """Vue détaillée d'un audit avec tableau de bord récapitulatif"""
    audit = Audit.query.get_or_404(audit_id)
    entreprise = audit.entreprise
    contacts = entreprise.contacts.all()
    sites = entreprise.sites.all()

    return render_template(
        'audit_detail.html',
        audit=audit,
        entreprise=entreprise,
        contacts=contacts,
        sites=sites
    )


@audit_bp.route('/audit/<int:audit_id>/ajouter-site', methods=['GET', 'POST'])
@login_required
def ajouter_site(audit_id):
    """Ajoute un site à l'entreprise liée à l'audit"""
    audit = Audit.query.get_or_404(audit_id)

    if request.method == 'POST':
        try:
            nom_site = request.form.get('nom_site', '').strip()

            if not nom_site:
                flash('Le nom du site est requis.', 'danger')
                return redirect(url_for('audit.ajouter_site', audit_id=audit_id))

            site = Site(
                nom=nom_site,
                adresse=request.form.get('adresse_site', ''),
                entreprise_id=audit.entreprise_id
            )

            db.session.add(site)
            db.session.commit()

            logger.info(f'Site ajouté: "{nom_site}" (audit_id={audit_id})')
            flash(f'✅ Site "{nom_site}" ajouté avec succès !', 'success')
            return redirect(url_for('audit.audit_detail', audit_id=audit_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de l\'ajout du site: {str(e)}', exc_info=True)
            flash(f'❌ Erreur lors de l\'ajout du site : {str(e)}', 'danger')
            return redirect(url_for('audit.ajouter_site', audit_id=audit_id))

    return render_template('ajouter_site.html', audit=audit)


@audit_bp.route('/audit/<int:audit_id>/changer-status', methods=['POST'])
@login_required
def changer_status(audit_id):
    """Change le statut d'un audit (POST uniquement pour sécurité)"""
    audit = Audit.query.get_or_404(audit_id)
    status = request.form.get('status', '')

    try:
        new_status = AuditStatus[status]
        audit.status = new_status
        db.session.commit()

        logger.info(f'Statut de l\'audit {audit_id} changé en "{new_status.value}"')
        flash(f'✅ Statut de l\'audit changé en "{new_status.value}".', 'success')
    except (KeyError, ValueError):
        flash('❌ Statut invalide.', 'danger')

    return redirect(url_for('audit.audit_detail', audit_id=audit_id))


@audit_bp.route('/audit/<int:audit_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_audit(audit_id):
    """Modifier les informations d'un audit"""
    audit = Audit.query.get_or_404(audit_id)

    if request.method == 'POST':
        try:
            # Mise à jour des informations générales
            audit.nom_projet = request.form.get('nom_projet', '').strip()

            # Mise à jour du contexte
            audit.objectifs = request.form.get('objectifs', '')
            audit.limites = request.form.get('limites', '')
            audit.hypotheses = request.form.get('hypotheses', '')
            audit.risques_initiaux = request.form.get('risques_initiaux', '')

            # Obtenir le dossier audit
            entreprise = audit.entreprise
            audit_folder = create_audit_folder_structure(
                entreprise.nom, audit.date_creation or datetime.now()
            )
            admin_folder = f'{audit_folder}/bloc_01_administratif'

            # Upload de nouveaux documents si fournis
            for field, file_type in [
                ('lettre_mission', 'pdf'),
                ('contrat', 'pdf'),
                ('planning', 'spreadsheet')
            ]:
                path, error = handle_file_upload(request, field, file_type, admin_folder)
                if error:
                    flash(f'❌ {error}', 'danger')
                    return redirect(url_for('audit.modifier_audit', audit_id=audit_id))
                if path:
                    setattr(audit, f'{field}_path', path)

            db.session.commit()
            logger.info(f'Audit modifié: "{audit.nom_projet}" (id={audit_id})')
            flash(f'✅ Audit "{audit.nom_projet}" mis à jour avec succès !', 'success')
            return redirect(url_for('audit.audit_detail', audit_id=audit.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification de l\'audit: {str(e)}', exc_info=True)
            flash(f'❌ Erreur lors de la mise à jour : {str(e)}', 'danger')
            return redirect(url_for('audit.modifier_audit', audit_id=audit_id))

    return render_template('modifier_audit.html', audit=audit)
