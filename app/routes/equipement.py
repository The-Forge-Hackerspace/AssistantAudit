"""
Routes de gestion des équipements : CRUD, audit
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import (
    Site, Equipement, EquipementReseau, EquipementServeur, EquipementFirewall,
    EquipementAuditStatus, ChecklistTemplate, EquipementChecklist, ChecklistStatut
)
from app.utils import validate_ip_address, validate_mac_address

logger = logging.getLogger(__name__)

equipement_bp = Blueprint('equipement', __name__)


@equipement_bp.route('/site/<int:site_id>/equipements')
@login_required
def liste_equipements(site_id):
    """Liste les équipements d'un site"""
    site = Site.query.get_or_404(site_id)

    # Récupérer les équipements par type
    equipements_reseau = EquipementReseau.query.filter_by(site_id=site_id).all()
    equipements_serveur = EquipementServeur.query.filter_by(site_id=site_id).all()
    equipements_firewall = EquipementFirewall.query.filter_by(site_id=site_id).all()

    # Calculer les statistiques depuis les données déjà chargées
    all_equips = equipements_reseau + equipements_serveur + equipements_firewall
    stats = {
        'total': len(all_equips),
        'conforme': sum(1 for e in all_equips if e.status_audit == EquipementAuditStatus.CONFORME),
        'a_auditer': sum(1 for e in all_equips if e.status_audit == EquipementAuditStatus.A_AUDITER),
        'non_conforme': sum(1 for e in all_equips if e.status_audit == EquipementAuditStatus.NON_CONFORME)
    }

    return render_template(
        'liste_equipements.html',
        site=site,
        equipements_reseau=equipements_reseau,
        equipements_serveur=equipements_serveur,
        equipements_firewall=equipements_firewall,
        stats=stats
    )


@equipement_bp.route('/equipement/<int:equipement_id>')
@login_required
def detail_equipement(equipement_id):
    """Vue détails d'un équipement"""
    equipement = Equipement.query.get_or_404(equipement_id)
    return render_template('detail_equipement.html', equipement=equipement)


@equipement_bp.route('/equipement/<int:equipement_id>/audit', methods=['GET', 'POST'])
@login_required
def auditer_equipement(equipement_id):
    """Audit d'un équipement - modification du statut, notes et checklist"""
    equipement = Equipement.query.get_or_404(equipement_id)

    if request.method == 'POST':
        try:
            from datetime import datetime, timezone
            from flask_login import current_user as audit_user

            # Mise à jour du statut d'audit
            nouveau_status = request.form.get('status_audit')
            if nouveau_status:
                equipement.status_audit = EquipementAuditStatus[nouveau_status]

            # Mise à jour des notes d'audit
            equipement.notes_audit = request.form.get('notes_audit', '')

            # Mise à jour des items de checklist
            for item in equipement.checklist_items:
                statut_key = f'checklist_statut_{item.id}'
                commentaire_key = f'checklist_commentaire_{item.id}'
                new_statut = request.form.get(statut_key)
                new_commentaire = request.form.get(commentaire_key, '')

                if new_statut:
                    try:
                        item.statut = ChecklistStatut(new_statut)
                        item.commentaire = new_commentaire.strip() or None
                        item.date_verification = datetime.now(timezone.utc)
                        item.verifie_par = audit_user.nom_complet or audit_user.username
                    except (KeyError, ValueError):
                        pass

            db.session.commit()
            logger.info(f'Équipement {equipement_id} audité: {equipement.status_audit.value}')
            flash(f'✅ Audit de "{equipement.hostname}" mis à jour avec succès', 'success')
            return redirect(url_for('equipement.detail_equipement', equipement_id=equipement.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de l\'audit: {str(e)}', exc_info=True)
            flash('Erreur lors de l\'audit. Veuillez réessayer.', 'danger')
            return redirect(url_for('equipement.auditer_equipement', equipement_id=equipement_id))

    checklist_items = equipement.checklist_items.all()
    return render_template('auditer_equipement.html', equipement=equipement, checklist_items=checklist_items)


@equipement_bp.route('/equipement/<int:equipement_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_equipement(equipement_id):
    """Modifier les informations d'un équipement"""
    equipement = Equipement.query.get_or_404(equipement_id)

    if request.method == 'POST':
        try:
            def parse_int_field(field_name):
                raw_value = request.form.get(field_name, '').strip()
                if not raw_value:
                    return None
                try:
                    return int(raw_value)
                except ValueError:
                    return None

            # Mise à jour des champs communs
            hostname = request.form.get('hostname')
            if hostname is not None:
                equipement.hostname = hostname.strip() or None
            equipement.mac_address = request.form.get('mac_address', '').strip() or None
            equipement.fabricant = request.form.get('fabricant', '').strip() or None
            equipement.os_detected = request.form.get('os_detected', '').strip() or None

            # Champs spécifiques par type
            if isinstance(equipement, EquipementReseau):
                equipement.firmware_version = request.form.get('firmware_version', '').strip()

            elif isinstance(equipement, EquipementServeur):
                equipement.os_version_detail = request.form.get('os_version_detail', '').strip() or None
                equipement.modele_materiel = request.form.get('modele_materiel', '').strip() or None
                roles = request.form.get('role_list', '').strip()
                equipement.role_list = [r.strip() for r in roles.split(',') if r.strip()] if roles else None

                cpu_cores = parse_int_field('cpu_cores')
                ram_gb = parse_int_field('ram_gb')
                storage_gb = parse_int_field('storage_gb')
                cpu_model = request.form.get('cpu_model', '').strip()
                cpu_ram_info = {}
                if cpu_cores is not None:
                    cpu_ram_info['cpu_cores'] = cpu_cores
                if ram_gb is not None:
                    cpu_ram_info['ram_gb'] = ram_gb
                if storage_gb is not None:
                    cpu_ram_info['storage_gb'] = storage_gb
                if cpu_model:
                    cpu_ram_info['cpu_model'] = cpu_model
                equipement.cpu_ram_info = cpu_ram_info or None

            elif isinstance(equipement, EquipementFirewall):
                equipement.license_status = request.form.get('license_status', '').strip()
                vpn_users = request.form.get('vpn_users_count', '0').strip()
                rules = request.form.get('rules_count', '0').strip()
                try:
                    equipement.vpn_users_count = int(vpn_users) if vpn_users else 0
                    equipement.rules_count = int(rules) if rules else 0
                except ValueError:
                    pass

            db.session.commit()
            logger.info(f'Équipement modifié: {equipement.hostname or equipement.ip_address} (id={equipement_id})')
            flash(f'✅ Équipement "{equipement.hostname or equipement.ip_address}" mis à jour avec succès !', 'success')
            return redirect(url_for('equipement.detail_equipement', equipement_id=equipement.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification de l\'équipement: {str(e)}', exc_info=True)
            flash('Erreur lors de la mise à jour. Veuillez réessayer.', 'danger')
            return redirect(url_for('equipement.modifier_equipement', equipement_id=equipement_id))

    return render_template('modifier_equipement.html', equipement=equipement)


@equipement_bp.route('/site/<int:site_id>/equipements/nouveau', methods=['GET', 'POST'])
@login_required
def ajouter_equipement(site_id):
    """Ajout manuel d'un équipement"""
    site = Site.query.get_or_404(site_id)

    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            type_equipement = request.form.get('type_equipement')
            ip_address = request.form.get('ip_address', '').strip()
            hostname = request.form.get('hostname', '').strip()
            mac_address = request.form.get('mac_address', '').strip()
            fabricant = request.form.get('fabricant', '').strip()
            os_detected = request.form.get('os_detected', '').strip()

            # Validation
            if not type_equipement or type_equipement not in ['reseau', 'serveur', 'firewall']:
                flash("❌ Type d'équipement invalide", 'danger')
                return redirect(url_for('equipement.ajouter_equipement', site_id=site_id))

            if not ip_address:
                flash("L'adresse IP est obligatoire", 'danger')
                return redirect(url_for('equipement.ajouter_equipement', site_id=site_id))

            # Validation du format IP
            ip_valid, ip_error = validate_ip_address(ip_address)
            if not ip_valid:
                flash(f'{ip_error}', 'danger')
                return redirect(url_for('equipement.ajouter_equipement', site_id=site_id))

            # Validation du format MAC si fourni
            mac_valid, mac_error = validate_mac_address(mac_address)
            if not mac_valid:
                flash(f'{mac_error}', 'danger')
                return redirect(url_for('equipement.ajouter_equipement', site_id=site_id))

            # Vérifier si l'IP existe déjà sur ce site
            existing = Equipement.query.filter_by(site_id=site_id, ip_address=ip_address).first()
            if existing:
                flash(f"❌ Un équipement avec l'IP {ip_address} existe déjà sur ce site", 'danger')
                return redirect(url_for('equipement.ajouter_equipement', site_id=site_id))

            # Créer l'équipement selon le type
            if type_equipement == 'reseau':
                firmware_version = request.form.get('firmware_version', '').strip()
                equipement = EquipementReseau(
                    site_id=site_id, ip_address=ip_address,
                    hostname=hostname or None, mac_address=mac_address or None,
                    fabricant=fabricant or None, os_detected=os_detected or None,
                    status_audit=EquipementAuditStatus.A_AUDITER,
                    firmware_version=firmware_version or None
                )

            elif type_equipement == 'serveur':
                os_version_detail = request.form.get('os_version_detail', '').strip()
                modele_materiel = request.form.get('modele_materiel', '').strip()
                cpu_cores_raw = request.form.get('cpu_cores', '').strip()
                ram_gb_raw = request.form.get('ram_gb', '').strip()
                storage_gb_raw = request.form.get('storage_gb', '').strip()
                cpu_model = request.form.get('cpu_model', '').strip()

                cpu_ram_info = {}
                if cpu_cores_raw.isdigit():
                    cpu_ram_info['cpu_cores'] = int(cpu_cores_raw)
                if ram_gb_raw.isdigit():
                    cpu_ram_info['ram_gb'] = int(ram_gb_raw)
                if storage_gb_raw.isdigit():
                    cpu_ram_info['storage_gb'] = int(storage_gb_raw)
                if cpu_model:
                    cpu_ram_info['cpu_model'] = cpu_model

                equipement = EquipementServeur(
                    site_id=site_id, ip_address=ip_address,
                    hostname=hostname or None, mac_address=mac_address or None,
                    fabricant=fabricant or None, os_detected=os_detected or None,
                    status_audit=EquipementAuditStatus.A_AUDITER,
                    os_version_detail=os_version_detail or None,
                    modele_materiel=modele_materiel or None,
                    cpu_ram_info=cpu_ram_info or None
                )

            elif type_equipement == 'firewall':
                license_status = request.form.get('license_status', '').strip()
                equipement = EquipementFirewall(
                    site_id=site_id, ip_address=ip_address,
                    hostname=hostname or None, mac_address=mac_address or None,
                    fabricant=fabricant or None, os_detected=os_detected or None,
                    status_audit=EquipementAuditStatus.A_AUDITER,
                    license_status=license_status or None
                )

            db.session.add(equipement)
            db.session.flush()

            # Ajouter les items de checklist sélectionnés
            templates = ChecklistTemplate.query.filter_by(
                type_equipement=type_equipement, actif=True
            ).all()

            for template in templates:
                checkbox_key = f'checklist_{template.id}'
                if request.form.get(checkbox_key) == 'on':
                    checklist_item = EquipementChecklist(
                        equipement_id=equipement.id,
                        template_id=template.id,
                        statut=ChecklistStatut.NON_VERIFIE
                    )
                    db.session.add(checklist_item)

            db.session.commit()

            logger.info(f'Équipement ajouté: {hostname or ip_address} (site_id={site_id})')
            flash(f'✅ Équipement "{hostname or ip_address}" ajouté avec succès !', 'success')
            return redirect(url_for('equipement.detail_equipement', equipement_id=equipement.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de l\'ajout de l\'équipement: {str(e)}', exc_info=True)
            flash('Erreur lors de l\'ajout. Veuillez réessayer.', 'danger')
            return redirect(url_for('equipement.ajouter_equipement', site_id=site_id))

    # Récupérer les templates de checklist pour chaque type
    templates_reseau = ChecklistTemplate.query.filter_by(type_equipement='reseau', actif=True).order_by(ChecklistTemplate.ordre).all()
    templates_serveur = ChecklistTemplate.query.filter_by(type_equipement='serveur', actif=True).order_by(ChecklistTemplate.ordre).all()
    templates_firewall = ChecklistTemplate.query.filter_by(type_equipement='firewall', actif=True).order_by(ChecklistTemplate.ordre).all()

    return render_template(
        'ajouter_equipement.html',
        site=site,
        templates_reseau=templates_reseau,
        templates_serveur=templates_serveur,
        templates_firewall=templates_firewall
    )
