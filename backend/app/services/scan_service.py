"""
Service Scan Réseau — Orchestration des scans Nmap et persistance des résultats.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.scan import ScanReseau, ScanHost, ScanPort
from ..models.site import Site
from ..models.equipement import Equipement
from ..tools.nmap_scanner.scanner import NmapScanner, NmapScanResult
from ..core.database import SessionLocal

logger = logging.getLogger(__name__)

# Mapping type_scan → arguments nmap (pour affichage)
NMAP_TYPE_ARGS: dict[str, list[str]] = {
    "discovery": ["-sn"],
    "port_scan": ["-sV", "--top-ports", "1000"],
    "full": ["-sV", "-sC", "-O", "-p-"],
}


def _build_display_command(target: str, scan_type: str, custom_args: Optional[str] = None) -> str:
    """Construit la commande nmap affichée à l'utilisateur."""
    parts = ["nmap"]
    if scan_type == "custom" and custom_args:
        parts.extend(custom_args.strip().split())
    else:
        parts.extend(NMAP_TYPE_ARGS.get(scan_type, ["-sn"]))
    parts.append(target)
    return " ".join(parts)


def get_nmap_command_preview(target: str, scan_type: str, custom_args: Optional[str] = None) -> str:
    """Retourne un aperçu de la commande nmap sans l'exécuter."""
    return _build_display_command(target or "<cible>", scan_type, custom_args)


def create_pending_scan(
    db: Session,
    site_id: int,
    target: str,
    scan_type: str = "discovery",
    nom: Optional[str] = None,
    notes: Optional[str] = None,
    custom_args: Optional[str] = None,
) -> ScanReseau:
    """
    Crée un scan en statut 'running' et le persiste immédiatement.
    Le scan réel sera exécuté en arrière-plan via execute_scan_background().

    Returns:
        ScanReseau avec statut='running'
    """
    # Vérifier que le site existe
    site = db.get(Site, site_id)
    if not site:
        raise ValueError(f"Site {site_id} introuvable")

    effective_scan_type = scan_type
    nmap_command = _build_display_command(target, scan_type, custom_args)

    scan = ScanReseau(
        nom=nom,
        site_id=site_id,
        type_scan=effective_scan_type,
        nmap_command=nmap_command,
        statut="running",
        notes=notes,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    logger.info(f"Scan #{scan.id} créé en statut 'running' pour {target}")
    return scan


def execute_scan_background(
    scan_id: int,
    site_id: int,
    target: str,
    scan_type: str = "discovery",
    custom_args: Optional[str] = None,
    timeout: int = 600,
) -> None:
    """
    Exécute le scan Nmap en arrière-plan et met à jour l'enregistrement.
    Utilise sa propre session DB (les background tasks sont hors requête).
    """
    db = SessionLocal()
    try:
        scan = db.get(ScanReseau, scan_id)
        if not scan:
            logger.error(f"Scan #{scan_id} introuvable pour exécution background")
            return

        # Lancer le scan
        scanner = NmapScanner(timeout=timeout)
        extra_args: Optional[list[str]] = None

        if scan_type == "custom" and custom_args:
            extra_args = custom_args.strip().split()
            result: NmapScanResult = scanner.scan(target, "custom", extra_args)
        else:
            result = scanner.scan(target, scan_type)

        if not result.success:
            scan.statut = "failed"
            scan.error_message = result.error or "Échec du scan"
            db.commit()
            logger.warning(f"Scan #{scan_id} échoué: {result.error}")
            return

        # Mettre à jour le scan avec les résultats
        scan.raw_xml_output = result.raw_xml
        scan.nombre_hosts_trouves = len(result.hosts)
        scan.nombre_ports_ouverts = sum(
            len([p for p in h.ports if p.state == "open"])
            for h in result.hosts
        )
        scan.duree_scan_secondes = result.duration_seconds
        scan.statut = "completed"
        db.flush()

        # Persister les hosts et ports
        for discovered_host in result.hosts:
            host = ScanHost(
                scan_id=scan.id,
                ip_address=discovered_host.ip_address,
                hostname=discovered_host.hostname or None,
                mac_address=discovered_host.mac_address or None,
                vendor=discovered_host.vendor or None,
                os_guess=discovered_host.os_guess or None,
                status=discovered_host.status,
                ports_open_count=len([p for p in discovered_host.ports if p.state == "open"]),
                decision="pending",
            )
            # Vérifier si un équipement existe déjà avec cette IP sur ce site
            existing = (
                db.query(Equipement)
                .filter(
                    Equipement.site_id == site_id,
                    Equipement.ip_address == discovered_host.ip_address,
                )
                .first()
            )
            if existing:
                host.equipement_id = existing.id
                host.decision = "kept"
                host.chosen_type = existing.type_equipement

            db.add(host)
            db.flush()

            for discovered_port in discovered_host.ports:
                port = ScanPort(
                    host_id=host.id,
                    port_number=discovered_port.port_number,
                    protocol=discovered_port.protocol,
                    state=discovered_port.state,
                    service_name=discovered_port.service_name or None,
                    product=discovered_port.product or None,
                    version=discovered_port.version or None,
                )
                db.add(port)

        db.commit()

        logger.info(
            f"Scan #{scan_id} terminé: {len(result.hosts)} hosts, "
            f"{scan.nombre_ports_ouverts} ports ouverts ({result.duration_seconds}s)"
        )

    except Exception as e:
        logger.exception(f"Erreur inattendue lors du scan background #{scan_id}")
        try:
            scan = db.get(ScanReseau, scan_id)
            if scan:
                scan.statut = "failed"
                scan.error_message = str(e)
                db.commit()
        except Exception:
            logger.exception("Impossible de mettre à jour le statut du scan")
    finally:
        db.close()


def update_host_decision(
    db: Session,
    host_id: int,
    decision: str,
    chosen_type: Optional[str] = None,
    hostname_override: Optional[str] = None,
    create_equipement: bool = False,
) -> ScanHost:
    """
    Met à jour la décision sur un host découvert.
    Peut optionnellement créer un équipement à partir du host.

    Args:
        db: Session SQLAlchemy
        host_id: ID du ScanHost
        decision: 'kept' ou 'ignored'
        chosen_type: Type d'équipement (serveur, reseau, firewall, equipement)
        hostname_override: Override du hostname
        create_equipement: Si True, crée un équipement et le lie au host

    Returns:
        ScanHost mis à jour
    """
    host = db.get(ScanHost, host_id)
    if not host:
        raise ValueError(f"Host {host_id} introuvable")

    host.decision = decision
    if chosen_type:
        host.chosen_type = chosen_type
    if hostname_override is not None:
        host.hostname = hostname_override

    if create_equipement and decision == "kept":
        # Récupérer le site_id via le scan
        scan = db.get(ScanReseau, host.scan_id)
        if not scan:
            raise ValueError("Scan introuvable pour ce host")

        # Vérifier qu'un équipement n'existe pas déjà
        existing = (
            db.query(Equipement)
            .filter(
                Equipement.site_id == scan.site_id,
                Equipement.ip_address == host.ip_address,
            )
            .first()
        )

        if existing:
            host.equipement_id = existing.id
            logger.info(f"Host {host.ip_address} lié à l'équipement existant #{existing.id}")
        else:
            equip = Equipement(
                site_id=scan.site_id,
                type_equipement=chosen_type or "equipement",
                ip_address=host.ip_address,
                hostname=hostname_override or host.hostname,
                mac_address=host.mac_address,
                fabricant=host.vendor,
                os_detected=host.os_guess,
            )
            db.add(equip)
            db.flush()
            host.equipement_id = equip.id
            logger.info(
                f"Équipement créé depuis scan: {host.ip_address} "
                f"(type={chosen_type}, id={equip.id})"
            )

    db.commit()
    db.refresh(host)
    return host


def link_host_to_equipement(
    db: Session,
    host_id: int,
    equipement_id: int,
) -> ScanHost:
    """Lie un host découvert à un équipement existant."""
    host = db.get(ScanHost, host_id)
    if not host:
        raise ValueError(f"Host {host_id} introuvable")

    equip = db.get(Equipement, equipement_id)
    if not equip:
        raise ValueError(f"Équipement {equipement_id} introuvable")

    host.equipement_id = equipement_id
    host.decision = "kept"
    host.chosen_type = equip.type_equipement

    db.commit()
    db.refresh(host)
    return host


def get_scan_with_hosts(db: Session, scan_id: int) -> Optional[ScanReseau]:
    """Récupère un scan avec ses hosts et ports."""
    return db.get(ScanReseau, scan_id)


def list_scans(
    db: Session,
    site_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[ScanReseau], int]:
    """Liste les scans, optionnellement filtrés par site."""
    query = db.query(ScanReseau)
    if site_id:
        query = query.filter(ScanReseau.site_id == site_id)
    total = query.count()
    items = query.order_by(ScanReseau.date_scan.desc()).offset(skip).limit(limit).all()
    return items, total


def delete_scan(db: Session, scan_id: int) -> bool:
    """Supprime un scan et tous ses hosts/ports."""
    scan = db.get(ScanReseau, scan_id)
    if not scan:
        return False
    db.delete(scan)
    db.commit()
    return True


def import_all_kept_hosts(db: Session, scan_id: int) -> list[Equipement]:
    """
    Crée des équipements pour tous les hosts 'pending' d'un scan.
    Marque chaque host comme 'kept'.
    """
    scan = db.get(ScanReseau, scan_id)
    if not scan:
        raise ValueError(f"Scan {scan_id} introuvable")

    created = []
    for host in scan.hosts:
        if host.decision != "pending":
            continue
        if host.equipement_id:
            continue

        # Vérifier si l'IP existe déjà
        existing = (
            db.query(Equipement)
            .filter(
                Equipement.site_id == scan.site_id,
                Equipement.ip_address == host.ip_address,
            )
            .first()
        )
        if existing:
            host.equipement_id = existing.id
            host.decision = "kept"
            host.chosen_type = existing.type_equipement
            continue

        # Deviner le type en fonction des ports
        guessed_type = _guess_equipement_type(host)

        equip = Equipement(
            site_id=scan.site_id,
            type_equipement=guessed_type,
            ip_address=host.ip_address,
            hostname=host.hostname,
            mac_address=host.mac_address,
            fabricant=host.vendor,
            os_detected=host.os_guess,
        )
        db.add(equip)
        db.flush()

        host.equipement_id = equip.id
        host.decision = "kept"
        host.chosen_type = guessed_type
        created.append(equip)

    db.commit()
    logger.info(f"Import scan #{scan_id}: {len(created)} équipements créés")
    return created


def _guess_equipement_type(host: ScanHost) -> str:
    """
    Devine le type d'équipement en fonction des ports ouverts et de l'OS.
    """
    port_numbers = {p.port_number for p in host.ports if p.state == "open"}
    services = {p.service_name for p in host.ports if p.service_name}
    os_lower = (host.os_guess or "").lower()

    # Firewall signatures
    if any(p in port_numbers for p in [443, 8443]) and "fortinet" in (host.vendor or "").lower():
        return "firewall"
    if "fortigate" in os_lower or "pfsense" in os_lower or "opnsense" in os_lower:
        return "firewall"

    # Network equipment
    if 161 in port_numbers and not (22 in port_numbers or 3389 in port_numbers):
        return "reseau"
    if "cisco" in (host.vendor or "").lower() or "switch" in os_lower:
        return "reseau"

    # Server signatures
    if any(p in port_numbers for p in [22, 80, 443, 3389, 5985, 5986]):
        return "serveur"
    if "windows" in os_lower or "linux" in os_lower:
        return "serveur"

    return "equipement"
