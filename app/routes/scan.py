"""
Routes de gestion des scans réseau : Nmap, validation, typage
"""
import os
import subprocess
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from app import db
from app.models import (
    Site, Equipement, EquipementReseau, EquipementServeur, EquipementFirewall,
    EquipementAuditStatus, ScanReseau, ScanHost, ScanPort,
    ChecklistTemplate, EquipementChecklist, ChecklistStatut
)
from app.utils import validate_ip_or_cidr

logger = logging.getLogger(__name__)

scan_bp = Blueprint('scan', __name__)


@scan_bp.route('/site/<int:site_id>/scans')
@login_required
def liste_scans(site_id):
    """Liste historique des scans réseau d'un site"""
    site = Site.query.get_or_404(site_id)
    scans = ScanReseau.query.filter_by(site_id=site_id).order_by(ScanReseau.date_scan.desc()).all()

    return render_template('liste_scans.html', site=site, scans=scans)


@scan_bp.route('/scan/<int:scan_id>')
@login_required
def detail_scan(scan_id):
    """Vue détails d'un scan réseau"""
    scan = ScanReseau.query.get_or_404(scan_id)
    return render_template('detail_scan.html', scan=scan)


@scan_bp.route('/site/<int:site_id>/scans/nmap', methods=['GET', 'POST'])
@login_required
def lancer_scan_nmap(site_id):
    """Lance un scan Nmap sur le site"""
    site = Site.query.get_or_404(site_id)

    if request.method == 'POST':
        target = request.form.get('target', '').strip()

        if not target:
            flash('❌ Veuillez spécifier une cible (IP ou plage CIDR)', 'danger')
            return redirect(url_for('scan.lancer_scan_nmap', site_id=site_id))

        # Validation stricte de la cible avec le module ipaddress
        is_valid, error_msg = validate_ip_or_cidr(target)
        if not is_valid:
            flash(f'❌ {error_msg}', 'danger')
            return redirect(url_for('scan.lancer_scan_nmap', site_id=site_id))

        try:
            # Créer le dossier de scan
            scan_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'scans', f'site_{site_id}')
            os.makedirs(scan_dir, exist_ok=True)

            # Nom du fichier XML de sortie
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            xml_filename = f'nmap_scan_{timestamp}.xml'
            xml_path = os.path.join(scan_dir, xml_filename)

            # Construction de la commande Nmap
            nmap_cmd = [
                'nmap',
                '-sV',  # Detection de version
                '--top-ports', '500',  # Top 500 ports
                '-T4',  # Timing agressif
                '-oX', xml_path,  # Sortie XML
                target
            ]

            logger.info(f'Lancement scan Nmap sur: {target} (site_id={site_id})')

            # Exécution de Nmap
            nmap_timeout = current_app.config.get('NMAP_TIMEOUT', 600)
            start_time = datetime.now()
            result = subprocess.run(
                nmap_cmd,
                capture_output=True,
                text=True,
                timeout=nmap_timeout
            )
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())

            if result.returncode != 0:
                logger.error(f'Nmap erreur: {result.stderr}')
                flash(f'❌ Erreur lors de l\'exécution de Nmap: {result.stderr}', 'danger')
                return redirect(url_for('scan.lancer_scan_nmap', site_id=site_id))

            # Lecture du fichier XML
            if not os.path.exists(xml_path):
                flash('❌ Fichier XML de scan introuvable', 'danger')
                return redirect(url_for('scan.lancer_scan_nmap', site_id=site_id))

            with open(xml_path, 'r') as f:
                xml_content = f.read()

            # Parse XML
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Créer l'enregistrement ScanReseau (stocker le chemin, pas le XML complet)
            scan = ScanReseau(
                site_id=site_id,
                type_scan='NMAP',
                raw_xml_output=xml_content,
                duree_scan_secondes=duration
            )
            db.session.add(scan)
            db.session.flush()

            hosts_found = 0
            total_ports = 0

            # Parser les hôtes découverts
            for host_elem in root.findall('.//host'):
                status_elem = host_elem.find('status')
                if status_elem is None:
                    continue

                host_status = status_elem.get('state', 'unknown')

                # Extraire l'IP
                address_elem = host_elem.find("address[@addrtype='ipv4']")
                if address_elem is None:
                    address_elem = host_elem.find("address[@addrtype='ipv6']")
                if address_elem is None:
                    continue

                ip_address = address_elem.get('addr')

                # Extraire MAC et vendor
                mac_elem = host_elem.find("address[@addrtype='mac']")
                mac_address = mac_elem.get('addr') if mac_elem is not None else None
                vendor = mac_elem.get('vendor') if mac_elem is not None else None

                # Extraire hostname
                hostname = None
                hostnames_elem = host_elem.find('hostnames')
                if hostnames_elem is not None:
                    hostname_elem = hostnames_elem.find('hostname')
                    if hostname_elem is not None:
                        hostname = hostname_elem.get('name')

                # Extraire OS
                os_guess = None
                os_elem = host_elem.find('.//osmatch')
                if os_elem is not None:
                    os_guess = os_elem.get('name')

                # Compter les ports ouverts
                ports_elem = host_elem.find('ports')
                open_ports_count = 0
                if ports_elem is not None:
                    open_ports_count = len([
                        p for p in ports_elem.findall('port')
                        if p.find('state') is not None and p.find('state').get('state') == 'open'
                    ])

                # Créer l'enregistrement ScanHost
                scan_host = ScanHost(
                    scan_id=scan.id,
                    ip_address=ip_address,
                    hostname=hostname,
                    mac_address=mac_address,
                    vendor=vendor,
                    os_guess=os_guess,
                    status=host_status,
                    ports_open_count=open_ports_count,
                    decision='pending'
                )
                db.session.add(scan_host)
                db.session.flush()

                hosts_found += 1

                # Parser les ports
                if ports_elem is not None:
                    for port_elem in ports_elem.findall('port'):
                        state_elem = port_elem.find('state')
                        if state_elem is None:
                            continue

                        port_state = state_elem.get('state')
                        if port_state != 'open':
                            continue

                        port_number = int(port_elem.get('portid'))
                        protocol = port_elem.get('protocol')

                        # Extraire le service
                        service_elem = port_elem.find('service')
                        service_name = service_elem.get('name') if service_elem is not None else None
                        product = service_elem.get('product') if service_elem is not None else None
                        version = service_elem.get('version') if service_elem is not None else None
                        extra_info = service_elem.get('extrainfo') if service_elem is not None else None

                        scan_port = ScanPort(
                            host_id=scan_host.id,
                            port_number=port_number,
                            protocol=protocol,
                            state=port_state,
                            service_name=service_name,
                            product=product,
                            version=version,
                            extra_info=extra_info
                        )
                        db.session.add(scan_port)
                        total_ports += 1

            # Mettre à jour les statistiques du scan
            scan.nombre_hosts_trouves = hosts_found
            scan.nombre_ports_ouverts = total_ports

            db.session.commit()

            logger.info(f'Scan terminé: {hosts_found} hôtes, {total_ports} ports (scan_id={scan.id})')
            flash(f'✅ Scan terminé ! {hosts_found} hôte(s) découvert(s) avec {total_ports} port(s) ouvert(s)', 'success')
            return redirect(url_for('scan.valider_decouvertes', scan_id=scan.id))

        except subprocess.TimeoutExpired:
            db.session.rollback()
            logger.error(f'Scan Nmap timeout pour site_id={site_id}')
            flash('❌ Le scan a dépassé le délai maximum', 'danger')
            return redirect(url_for('scan.lancer_scan_nmap', site_id=site_id))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors du scan: {str(e)}', exc_info=True)
            flash(f'❌ Erreur lors du scan : {str(e)}', 'danger')
            return redirect(url_for('scan.lancer_scan_nmap', site_id=site_id))

    return render_template('lancer_scan_nmap.html', site=site)


@scan_bp.route('/scan/<int:scan_id>/decouvertes', methods=['GET', 'POST'])
@login_required
def valider_decouvertes(scan_id):
    """Étape 1: Valider les découvertes du scan (Garder/Ignorer)"""
    scan = ScanReseau.query.get_or_404(scan_id)
    hosts = ScanHost.query.filter_by(scan_id=scan_id).all()

    if request.method == 'POST':
        for host in hosts:
            decision_key = f'decision_{host.id}'
            decision = request.form.get(decision_key)

            if decision == 'garder':
                host.decision = 'kept'
            elif decision == 'ignorer':
                host.decision = 'ignored'

        db.session.commit()

        kept_count = ScanHost.query.filter_by(scan_id=scan_id, decision='kept').count()

        if kept_count == 0:
            flash('⚠️ Aucun hôte sélectionné. Scan terminé.', 'warning')
            return redirect(url_for('scan.detail_scan', scan_id=scan_id))

        flash(f'✅ {kept_count} hôte(s) sélectionné(s). Passons au typage et à la checklist.', 'success')
        return redirect(url_for('scan.typer_decouvertes', scan_id=scan_id))

    # Pour chaque hôte, chercher s'il existe déjà un équipement avec cette IP
    hosts_with_matches = []
    for host in hosts:
        existing = Equipement.query.filter_by(site_id=scan.site_id, ip_address=host.ip_address).first()
        hosts_with_matches.append({
            'host': host,
            'existing_equipement': existing
        })

    return render_template('valider_decouvertes.html', scan=scan, hosts_with_matches=hosts_with_matches)


@scan_bp.route('/scan/<int:scan_id>/decouvertes/typer', methods=['GET', 'POST'])
@login_required
def typer_decouvertes(scan_id):
    """Étape 2: Typer les équipements gardés et remplir la checklist"""
    scan = ScanReseau.query.get_or_404(scan_id)
    kept_hosts = ScanHost.query.filter_by(scan_id=scan_id, decision='kept').all()

    if not kept_hosts:
        flash('⚠️ Aucun hôte à typer', 'warning')
        return redirect(url_for('scan.detail_scan', scan_id=scan_id))

    if request.method == 'POST':
        try:
            for host in kept_hosts:
                type_key = f'type_{host.id}'
                chosen_type = request.form.get(type_key)

                if not chosen_type or chosen_type not in ['reseau', 'serveur', 'firewall']:
                    continue

                action_key = f'action_{host.id}'
                action = request.form.get(action_key, 'create')

                existing = Equipement.query.filter_by(
                    site_id=scan.site_id, ip_address=host.ip_address
                ).first()

                if action == 'update' and existing:
                    equipement = existing
                    equipement.hostname = host.hostname or equipement.hostname
                    equipement.mac_address = host.mac_address or equipement.mac_address
                    equipement.fabricant = host.vendor or equipement.fabricant
                    equipement.os_detected = host.os_guess or equipement.os_detected
                    equipement.date_derniere_maj = datetime.now(timezone.utc)
                else:
                    if chosen_type == 'reseau':
                        equipement = EquipementReseau(
                            site_id=scan.site_id, ip_address=host.ip_address,
                            hostname=host.hostname, mac_address=host.mac_address,
                            fabricant=host.vendor, os_detected=host.os_guess,
                            status_audit=EquipementAuditStatus.A_AUDITER
                        )
                    elif chosen_type == 'serveur':
                        equipement = EquipementServeur(
                            site_id=scan.site_id, ip_address=host.ip_address,
                            hostname=host.hostname, mac_address=host.mac_address,
                            fabricant=host.vendor, os_detected=host.os_guess,
                            status_audit=EquipementAuditStatus.A_AUDITER,
                            os_version_detail=host.os_guess
                        )
                    elif chosen_type == 'firewall':
                        equipement = EquipementFirewall(
                            site_id=scan.site_id, ip_address=host.ip_address,
                            hostname=host.hostname, mac_address=host.mac_address,
                            fabricant=host.vendor, os_detected=host.os_guess,
                            status_audit=EquipementAuditStatus.A_AUDITER
                        )

                    db.session.add(equipement)

                db.session.flush()

                host.chosen_type = chosen_type
                host.equipement_id = equipement.id

                # Checklists
                templates = ChecklistTemplate.query.filter_by(
                    type_equipement=chosen_type, actif=True
                ).order_by(ChecklistTemplate.ordre).all()

                for template in templates:
                    checkbox_key = f'checklist_{host.id}_{template.id}'
                    if request.form.get(checkbox_key) == 'on':
                        checklist_item = EquipementChecklist(
                            equipement_id=equipement.id,
                            template_id=template.id,
                            statut=ChecklistStatut.NON_VERIFIE
                        )
                        db.session.add(checklist_item)

            db.session.commit()

            logger.info(f'{len(kept_hosts)} équipements créés/mis à jour depuis scan {scan_id}')
            flash(f'✅ {len(kept_hosts)} équipement(s) créé(s) ou mis à jour avec succès !', 'success')
            return redirect(url_for('equipement.liste_equipements', site_id=scan.site_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors du typage: {str(e)}', exc_info=True)
            flash(f'❌ Erreur lors de la création des équipements : {str(e)}', 'danger')
            return redirect(url_for('scan.typer_decouvertes', scan_id=scan_id))

    # Récupérer les templates de checklist
    templates_reseau = ChecklistTemplate.query.filter_by(type_equipement='reseau', actif=True).order_by(ChecklistTemplate.ordre).all()
    templates_serveur = ChecklistTemplate.query.filter_by(type_equipement='serveur', actif=True).order_by(ChecklistTemplate.ordre).all()
    templates_firewall = ChecklistTemplate.query.filter_by(type_equipement='firewall', actif=True).order_by(ChecklistTemplate.ordre).all()

    hosts_with_existing = []
    for host in kept_hosts:
        existing = Equipement.query.filter_by(site_id=scan.site_id, ip_address=host.ip_address).first()
        hosts_with_existing.append({'host': host, 'existing': existing})

    return render_template(
        'typer_decouvertes.html',
        scan=scan,
        hosts_with_existing=hosts_with_existing,
        templates_reseau=templates_reseau,
        templates_serveur=templates_serveur,
        templates_firewall=templates_firewall
    )
