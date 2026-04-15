"""
PipelineService — Orchestration du pipeline multi-étapes (TOS-13 / US009).

Enchaîne scan Nmap → création d'équipements → collectes SSH/WinRM pour un
sous-réseau. Ce module contient aussi les helpers purs (détection de profil)
pour rester facilement testables.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.collect_pipeline import CollectPipeline, PipelineStatus, PipelineStepStatus
from ..models.collect_result import CollectResult, CollectStatus
from ..models.equipement import Equipement
from ..models.scan import ScanHost, ScanReseau

logger = logging.getLogger(__name__)

# Profils supportés par la détection automatique.
# Les profils "stormshield" / "fortigate" existent côté collecteur mais ne
# sont pas auto-détectables de façon fiable depuis un scan Nmap : ils doivent
# être choisis explicitement par l'auditeur.
AutoCollectProfile = Literal["linux_server", "windows_server", "opnsense"]


# Ports "signaux" pour la détection.
_SSH_PORT = 22
_WINRM_HTTP_PORT = 5985
_WINRM_HTTPS_PORT = 5986


def _open_port_numbers(host: ScanHost) -> set[int]:
    """Retourne l'ensemble des numéros de ports dans l'état `open` pour un hôte."""
    ports: set[int] = set()
    for p in host.ports or []:
        if p.state == "open" and p.port_number is not None:
            ports.add(int(p.port_number))
    return ports


def _matches(value: Optional[str], *needles: str) -> bool:
    """True si `value` (case-insensitive) contient au moins un des `needles`."""
    if not value:
        return False
    haystack = value.lower()
    return any(n in haystack for n in needles)


def _host_signals(host: ScanHost) -> dict:
    """Agrège les signaux textuels utiles à la détection (OS + banners services)."""
    os_guess = host.os_guess or ""
    # Concatène les `product`/`version`/`extra_info` des ports pour détecter
    # OPNsense/FreeBSD via les banners SSH ou HTTP.
    banners: list[str] = []
    for p in host.ports or []:
        if p.state != "open":
            continue
        for field in (p.product, p.version, p.extra_info, p.service_name):
            if field:
                banners.append(field)
    return {"os_guess": os_guess, "banners": " ".join(banners)}


def detect_collect_profile(host: ScanHost) -> AutoCollectProfile | None:
    """
    Détermine le profil de collecte approprié pour un hôte découvert.

    Règles (dans l'ordre) :
      1. OPNsense/pfSense/FreeBSD + SSH ouvert → ``"opnsense"`` (plus spécifique
         que linux_server, doit donc être testé en premier).
      2. Windows + WinRM (5985/5986) ouvert → ``"windows_server"``.
      3. Linux/Unix + SSH (22) ouvert → ``"linux_server"``.
      4. SSH seul sans OS identifié → ``"linux_server"`` (fallback raisonnable).
      5. WinRM seul sans OS identifié → ``"windows_server"``.
      6. Aucun port compatible → ``None`` (l'hôte sera skippé).

    Retourne ``None`` si aucun profil n'est applicable : l'orchestrateur
    incrémentera alors ``hosts_skipped`` et continuera avec les autres hôtes.
    """
    signals = _host_signals(host)
    os_text = signals["os_guess"]
    banners_text = signals["banners"]
    open_ports = _open_port_numbers(host)

    has_ssh = _SSH_PORT in open_ports
    has_winrm = _WINRM_HTTP_PORT in open_ports or _WINRM_HTTPS_PORT in open_ports

    is_opnsense = _matches(os_text, "opnsense", "pfsense", "freebsd") or _matches(
        banners_text, "opnsense", "pfsense"
    )
    is_windows = _matches(os_text, "windows", "microsoft")
    is_linux = _matches(os_text, "linux", "ubuntu", "debian", "centos", "redhat", "rhel", "fedora", "alpine")

    # 1. OPNsense / pfSense — doit passer avant linux (SSH aussi ouvert)
    if is_opnsense and has_ssh:
        return "opnsense"

    # 2. Windows confirmé + WinRM ouvert
    if is_windows and has_winrm:
        return "windows_server"

    # 3. Linux confirmé + SSH ouvert
    if is_linux and has_ssh:
        return "linux_server"

    # 4. SSH seul sans OS clair — on tente linux_server
    if has_ssh and not has_winrm:
        return "linux_server"

    # 5. WinRM seul sans OS clair — on tente windows_server
    if has_winrm and not has_ssh:
        return "windows_server"

    # 6. Rien d'exploitable
    return None


# ══════════════════════════════════════════════════════════════════════════
# Orchestration du pipeline (T002)
# ══════════════════════════════════════════════════════════════════════════


# Profil de collecte → (methode de collecte, port par defaut, type equipement)
_PROFILE_METHOD: dict[AutoCollectProfile, tuple[str, int, str]] = {
    "linux_server": ("ssh", 22, "serveur"),
    "opnsense": ("ssh", 22, "firewall"),
    "windows_server": ("winrm", 5985, "serveur"),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_pending_pipeline(
    db: Session,
    site_id: int,
    target: str,
    created_by: int,
) -> CollectPipeline:
    """Cree un pipeline en statut 'pending' et le persiste immediatement."""
    pipeline = CollectPipeline(
        site_id=site_id,
        target=target,
        created_by=created_by,
        status=PipelineStatus.PENDING,
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


def _notify(user_id: int | None, event_type: str, data: dict) -> None:
    """Envoie un evenement WS au owner du pipeline, tolerant aux erreurs.

    Comme on tourne dans un thread dedie (LocalTaskRunner), on instancie un
    event loop dedie a l'appel. Les erreurs sont loguees mais n'interrompent
    jamais le pipeline — les clients peuvent aussi poller GET /pipelines/{id}.
    """
    if user_id is None:
        return
    try:
        from ..core.websocket_manager import ws_manager

        asyncio.run(ws_manager.send_to_user(user_id, event_type, data))
    except Exception:
        logger.exception("Pipeline WS notify failed (event=%s)", event_type)


def _pipeline_event(pipeline: CollectPipeline) -> dict:
    """Serialise l'etat courant d'un pipeline pour une notif WS."""
    return {
        "pipeline_id": pipeline.id,
        "status": pipeline.status.value if hasattr(pipeline.status, "value") else str(pipeline.status),
        "scan_status": pipeline.scan_status.value,
        "equipments_status": pipeline.equipments_status.value,
        "collects_status": pipeline.collects_status.value,
        "hosts_discovered": pipeline.hosts_discovered,
        "equipments_created": pipeline.equipments_created,
        "hosts_skipped": pipeline.hosts_skipped,
        "collects_total": pipeline.collects_total,
        "collects_done": pipeline.collects_done,
        "collects_failed": pipeline.collects_failed,
        "error_message": pipeline.error_message,
    }


def _run_scan_phase(db: Session, pipeline: CollectPipeline) -> ScanReseau | None:
    """Phase 1 : scan Nmap. Retourne le ScanReseau (completed) ou None si echec."""
    from . import scan_service

    scan = scan_service.create_pending_scan(
        db=db,
        site_id=pipeline.site_id,
        target=pipeline.target,
        scan_type="port_scan",  # besoin des ports pour detecter le profil
        nom=f"Pipeline #{pipeline.id}",
        owner_id=pipeline.created_by,
        is_admin=True,  # le check d'ownership a deja ete fait a la creation
    )
    pipeline.scan_id = scan.id
    pipeline.scan_status = PipelineStepStatus.RUNNING
    db.commit()

    # execute_scan_background ouvre sa propre session, ce qui nous convient.
    scan_service.execute_scan_background(
        scan_id=scan.id,
        site_id=pipeline.site_id,
        target=pipeline.target,
        scan_type="port_scan",
    )

    # Recharger le scan mis a jour par le worker
    db.refresh(pipeline)
    scan_reloaded = db.get(ScanReseau, scan.id)
    if scan_reloaded is None or scan_reloaded.statut != "completed":
        pipeline.scan_status = PipelineStepStatus.FAILED
        pipeline.error_message = (
            scan_reloaded.error_message if scan_reloaded else "Scan introuvable"
        )
        return None

    pipeline.hosts_discovered = scan_reloaded.nombre_hosts_trouves
    pipeline.scan_status = PipelineStepStatus.COMPLETED
    return scan_reloaded


def _run_equipments_phase(
    db: Session,
    pipeline: CollectPipeline,
    scan: ScanReseau,
) -> list[tuple[Equipement, AutoCollectProfile]]:
    """Phase 2 : pour chaque host, detecter le profil et creer/dedupliquer l'equipement.

    Retourne la liste (equipement, profile) a collecter ensuite.
    """
    pipeline.equipments_status = PipelineStepStatus.RUNNING
    db.commit()

    to_collect: list[tuple[Equipement, AutoCollectProfile]] = []
    hosts = db.query(ScanHost).filter(ScanHost.scan_id == scan.id).all()

    for host in hosts:
        profile = detect_collect_profile(host)
        if profile is None:
            pipeline.hosts_skipped += 1
            continue

        equip_type = _PROFILE_METHOD[profile][2]
        existing = (
            db.query(Equipement)
            .filter(
                Equipement.site_id == pipeline.site_id,
                Equipement.ip_address == host.ip_address,
            )
            .first()
        )
        if existing is not None:
            equip = existing
        else:
            equip = Equipement(
                site_id=pipeline.site_id,
                type_equipement=equip_type,
                ip_address=host.ip_address,
                hostname=host.hostname,
                mac_address=host.mac_address,
                fabricant=host.vendor,
                os_detected=host.os_guess,
            )
            db.add(equip)
            db.flush()
            pipeline.equipments_created += 1

        host.equipement_id = equip.id
        host.decision = "kept"
        host.chosen_type = equip_type
        to_collect.append((equip, profile))

    pipeline.equipments_status = PipelineStepStatus.COMPLETED
    pipeline.collects_total = len(to_collect)
    db.commit()
    return to_collect


def _run_collects_phase(
    db: Session,
    pipeline: CollectPipeline,
    targets: list[tuple[Equipement, AutoCollectProfile]],
    *,
    username: str,
    password: Optional[str],
    private_key: Optional[str],
    passphrase: Optional[str],
    use_ssl: bool,
    transport: str,
) -> None:
    """Phase 3 : lancer une collecte par equipement, tolerer les echecs individuels."""
    from . import collect_service

    if not targets:
        pipeline.collects_status = PipelineStepStatus.SKIPPED
        db.commit()
        return

    pipeline.collects_status = PipelineStepStatus.RUNNING
    db.commit()

    for equip, profile in targets:
        method, default_port, _ = _PROFILE_METHOD[profile]
        target_port = default_port
        if profile == "windows_server" and use_ssl:
            target_port = 5986

        try:
            collect = collect_service.create_pending_collect(
                db=db,
                equipement_id=equip.id,
                method=method,
                target_host=equip.ip_address,
                target_port=target_port,
                username=username,
                device_profile=profile,
            )
            db.commit()
            collect_id = collect.id

            collect_service.execute_collect_background(
                collect_id=collect_id,
                password=password,
                private_key=private_key,
                passphrase=passphrase,
                use_ssl=use_ssl,
                transport=transport,
            )

            # Lire le statut final dans une session propre
            db.expire_all()
            final = db.get(CollectResult, collect_id)
            if final is not None and final.status == CollectStatus.SUCCESS:
                pipeline.collects_done += 1
            else:
                pipeline.collects_failed += 1
        except Exception:
            logger.exception(
                "Pipeline #%s : collecte echouee pour equipement #%s",
                pipeline.id,
                equip.id,
            )
            pipeline.collects_failed += 1
        finally:
            db.commit()
            _notify(pipeline.created_by, "pipeline_progress", _pipeline_event(pipeline))

    # Statut final de la phase : completed si tout s'est passe, failed si 100% KO
    if pipeline.collects_failed == pipeline.collects_total and pipeline.collects_total > 0:
        pipeline.collects_status = PipelineStepStatus.FAILED
    else:
        pipeline.collects_status = PipelineStepStatus.COMPLETED
    db.commit()


def execute_pipeline_background(
    pipeline_id: int,
    *,
    username: str,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
) -> None:
    """Orchestre scan → equipements → collectes pour un pipeline.

    Execute de maniere synchrone dans un thread dedie (LocalTaskRunner). Chaque
    etape est isolee : un echec de collecte individuelle n'arrete pas la boucle.
    """
    db = SessionLocal()
    try:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            logger.error("Pipeline #%s introuvable", pipeline_id)
            return

        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = _utcnow()
        db.commit()
        _notify(pipeline.created_by, "pipeline_started", _pipeline_event(pipeline))

        # Phase 1 — Scan
        scan = _run_scan_phase(db, pipeline)
        db.commit()
        _notify(pipeline.created_by, "pipeline_progress", _pipeline_event(pipeline))
        if scan is None:
            pipeline.status = PipelineStatus.FAILED
            pipeline.completed_at = _utcnow()
            db.commit()
            _notify(pipeline.created_by, "pipeline_completed", _pipeline_event(pipeline))
            return

        # Phase 2 — Equipements
        targets = _run_equipments_phase(db, pipeline, scan)
        _notify(pipeline.created_by, "pipeline_progress", _pipeline_event(pipeline))

        # Phase 3 — Collectes
        _run_collects_phase(
            db,
            pipeline,
            targets,
            username=username,
            password=password,
            private_key=private_key,
            passphrase=passphrase,
            use_ssl=use_ssl,
            transport=transport,
        )

        pipeline.status = PipelineStatus.COMPLETED
        pipeline.completed_at = _utcnow()
        db.commit()
        _notify(pipeline.created_by, "pipeline_completed", _pipeline_event(pipeline))

    except Exception as exc:
        logger.exception("Pipeline #%s : erreur inattendue", pipeline_id)
        try:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is not None:
                pipeline.status = PipelineStatus.FAILED
                pipeline.error_message = str(exc)
                pipeline.completed_at = _utcnow()
                db.commit()
                _notify(pipeline.created_by, "pipeline_completed", _pipeline_event(pipeline))
        except Exception:
            logger.exception("Impossible de marquer le pipeline #%s comme failed", pipeline_id)
    finally:
        db.close()
