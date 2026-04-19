"""
PipelineService — Orchestration du pipeline multi-étapes (TOS-13 / US009).

Enchaîne scan Nmap (délégué à un agent) → création d'équipements → collectes
SSH/WinRM pour un sous-réseau. Ce module contient aussi les helpers purs
(détection de profil) pour rester facilement testables.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Literal, Optional, TypedDict

from sqlalchemy.orm import Session

from ..core.audit_logger import log_access_denied
from ..core.database import SessionLocal
from ..core.helpers import user_has_access_to_entreprise
from ..models.agent import Agent
from ..models.agent_task import AgentTask
from ..models.collect_pipeline import CollectPipeline, PipelineStatus, PipelineStepStatus
from ..models.collect_result import CollectResult, CollectStatus
from ..models.equipement import Equipement
from ..models.site import Site

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

# Polling du scan agent
_SCAN_POLL_INTERVAL_SEC = 5
_SCAN_TIMEOUT_SEC = 30 * 60  # 30 minutes


class NmapPort(TypedDict, total=False):
    port: int
    protocol: str
    state: str
    service: str


class NmapHost(TypedDict, total=False):
    """Hôte Nmap normalisé à partir du JSON renvoyé par l'agent.

    Les agents renvoient soit des clés courtes (ip/mac/os/port) soit les
    clés longues historiques (ip_address/mac_address/os_guess/port_number).
    `_normalize_host` unifie les deux formats.
    """

    ip: str
    hostname: str
    mac: str
    vendor: str
    os: str
    ports: list[NmapPort]


def _normalize_host(raw: dict[str, Any]) -> NmapHost:
    """Transforme un host brut agent en NmapHost normalisé."""
    raw_ports = raw.get("ports") or []
    ports: list[NmapPort] = []
    for p in raw_ports:
        if not isinstance(p, dict):
            continue
        ports.append(
            {
                "port": int(p.get("port") or p.get("port_number") or 0),
                "protocol": str(p.get("proto") or p.get("protocol") or "tcp"),
                "state": str(p.get("state") or ""),
                "service": str(p.get("service") or p.get("service_name") or ""),
            }
        )
    return {
        "ip": str(raw.get("ip") or raw.get("ip_address") or ""),
        "hostname": str(raw.get("hostname") or ""),
        "mac": str(raw.get("mac") or raw.get("mac_address") or ""),
        "vendor": str(raw.get("vendor") or ""),
        "os": str(raw.get("os") or raw.get("os_guess") or ""),
        "ports": ports,
    }


def _open_port_numbers(host: NmapHost) -> set[int]:
    """Retourne l'ensemble des numéros de ports dans l'état `open` pour un hôte."""
    ports: set[int] = set()
    for p in host.get("ports") or []:
        if p.get("state") == "open" and p.get("port"):
            ports.add(int(p["port"]))
    return ports


def _matches(value: Optional[str], *needles: str) -> bool:
    """True si `value` (case-insensitive) contient au moins un des `needles`."""
    if not value:
        return False
    haystack = value.lower()
    return any(n in haystack for n in needles)


def _host_signals(host: NmapHost) -> dict:
    """Agrège les signaux textuels utiles à la détection (OS + banners services)."""
    os_guess = host.get("os") or ""
    # Concatène les services des ports pour détecter OPNsense/FreeBSD via les
    # banners SSH ou HTTP. L'agent fusionne déjà product/version/extra_info
    # dans le champ `service`.
    banners: list[str] = []
    for p in host.get("ports") or []:
        if p.get("state") != "open":
            continue
        svc = p.get("service")
        if svc:
            banners.append(svc)
    return {"os_guess": os_guess, "banners": " ".join(banners)}


def detect_collect_profile(host: NmapHost) -> AutoCollectProfile | None:
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
    agent_id: int,
    target: str,
    created_by: int,
    *,
    is_admin: bool = False,
) -> CollectPipeline:
    """Cree un pipeline en statut 'pending' et le persiste immediatement.

    Verifie l'ownership du site (via Site -> Entreprise -> Audit) et de
    l'agent (sauf admin). Leve ``ValueError`` si une entite est introuvable
    ou inaccessible.
    """
    site = db.get(Site, site_id)
    if not site:
        raise ValueError(f"Site {site_id} introuvable")
    if not is_admin and not user_has_access_to_entreprise(db, site.entreprise_id, created_by):
        log_access_denied(created_by, "Site", site_id, action="launch_pipeline")
        raise ValueError(f"Site {site_id} introuvable")

    agent = db.get(Agent, agent_id)
    if agent is None:
        raise ValueError(f"Agent {agent_id} introuvable")
    if not is_admin and agent.user_id != created_by:
        log_access_denied(created_by, "Agent", agent_id, action="launch_pipeline")
        raise ValueError(f"Agent {agent_id} introuvable")
    if agent.status != "active":
        raise ValueError(f"Agent {agent_id} inactif")
    if "nmap" not in (agent.allowed_tools or []):
        raise ValueError(f"Agent {agent_id} non autorisé à exécuter nmap")

    pipeline = CollectPipeline(
        site_id=site_id,
        agent_id=agent_id,
        target=target,
        created_by=created_by,
        status=PipelineStatus.PENDING,
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


def get_pipeline(
    db: Session,
    pipeline_id: int,
    *,
    owner_id: int | None = None,
    is_admin: bool = False,
) -> CollectPipeline | None:
    """Retourne un pipeline si accessible par l'utilisateur, None sinon."""
    pipeline = db.get(CollectPipeline, pipeline_id)
    if pipeline is None:
        return None
    if owner_id is not None and not is_admin and pipeline.created_by != owner_id:
        log_access_denied(owner_id, "CollectPipeline", pipeline_id, action="read")
        return None
    return pipeline


def list_pipelines(
    db: Session,
    *,
    site_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
    owner_id: int | None = None,
    is_admin: bool = False,
) -> tuple[list[CollectPipeline], int]:
    """Liste les pipelines, filtrables par site. Non-admin : scope au owner."""
    query = db.query(CollectPipeline)
    if owner_id is not None and not is_admin:
        query = query.filter(CollectPipeline.created_by == owner_id)
    if site_id is not None:
        query = query.filter(CollectPipeline.site_id == site_id)
    total = query.count()
    items = (
        query.order_by(CollectPipeline.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


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


def _run_scan_phase(
    db: Session,
    pipeline: CollectPipeline,
    current_user_id: int,
) -> list[NmapHost] | None:
    """Phase 1 : dispatch du scan Nmap vers l'agent, polling jusqu'au résultat.

    Retourne la liste des hôtes normalisés (ou None si échec/timeout).
    """
    from . import task_service

    agent = db.get(Agent, pipeline.agent_id) if pipeline.agent_id else None
    if agent is None:
        pipeline.scan_status = PipelineStepStatus.FAILED
        pipeline.error_message = "Agent introuvable"
        return None

    try:
        task = task_service.dispatch_task(
            db=db,
            agent_uuid=agent.agent_uuid,
            tool="nmap",
            parameters={
                "target": pipeline.target,
                "scan_type": "port_scan",
            },
            current_user_id=current_user_id,
        )
    except Exception as exc:
        logger.exception("Pipeline #%s : dispatch nmap échoué", pipeline.id)
        pipeline.scan_status = PipelineStepStatus.FAILED
        pipeline.error_message = f"Dispatch nmap échoué : {exc}"
        return None

    pipeline.scan_task_uuid = task.task_uuid
    pipeline.scan_status = PipelineStepStatus.RUNNING
    db.commit()

    # Polling jusqu'à completed/failed/timeout
    deadline = time.monotonic() + _SCAN_TIMEOUT_SEC
    while time.monotonic() < deadline:
        time.sleep(_SCAN_POLL_INTERVAL_SEC)
        db.expire_all()
        task_reloaded = db.get(AgentTask, task.id)
        if task_reloaded is None:
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = "Tâche agent introuvable"
            return None
        if task_reloaded.status in ("completed", "failed", "cancelled"):
            task = task_reloaded
            break
    else:
        pipeline.scan_status = PipelineStepStatus.FAILED
        pipeline.error_message = "Timeout du scan agent"
        return None

    if task.status != "completed":
        pipeline.scan_status = PipelineStepStatus.FAILED
        pipeline.error_message = task.error_message or f"Scan {task.status}"
        return None

    raw_hosts = (task.result_summary or {}).get("hosts") or []
    hosts: list[NmapHost] = [_normalize_host(h) for h in raw_hosts if isinstance(h, dict)]
    pipeline.hosts_discovered = len(hosts)
    pipeline.scan_status = PipelineStepStatus.COMPLETED
    return hosts


def _run_equipments_phase(
    db: Session,
    pipeline: CollectPipeline,
    hosts: list[NmapHost],
) -> list[tuple[Equipement, AutoCollectProfile]]:
    """Phase 2 : pour chaque host, detecter le profil et creer/dedupliquer l'equipement.

    Retourne la liste (equipement, profile) a collecter ensuite.
    """
    pipeline.equipments_status = PipelineStepStatus.RUNNING
    db.commit()

    to_collect: list[tuple[Equipement, AutoCollectProfile]] = []

    for host in hosts:
        profile = detect_collect_profile(host)
        ip = host.get("ip") or ""
        if profile is None or not ip:
            pipeline.hosts_skipped += 1
            continue

        equip_type = _PROFILE_METHOD[profile][2]
        existing = (
            db.query(Equipement)
            .filter(
                Equipement.site_id == pipeline.site_id,
                Equipement.ip_address == ip,
            )
            .first()
        )
        if existing is not None:
            equip = existing
        else:
            equip = Equipement(
                site_id=pipeline.site_id,
                type_equipement=equip_type,
                ip_address=ip,
                hostname=host.get("hostname") or None,
                mac_address=host.get("mac") or None,
                fabricant=host.get("vendor") or None,
                os_detected=host.get("os") or None,
            )
            db.add(equip)
            db.flush()
            pipeline.equipments_created += 1

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
    agent_uuid: Optional[str] = None,  # conservé pour compat, non utilisé
    current_user_id: int,
    username: str,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
) -> None:
    """Orchestre scan agent → equipements → collectes pour un pipeline.

    Execute de maniere synchrone dans un thread dedie (LocalTaskRunner). Chaque
    etape est isolee : un echec de collecte individuelle n'arrete pas la boucle.
    """
    del agent_uuid  # l'agent est lu depuis pipeline.agent_id
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

        # Phase 1 — Scan agent
        hosts = _run_scan_phase(db, pipeline, current_user_id)
        db.commit()
        _notify(pipeline.created_by, "pipeline_progress", _pipeline_event(pipeline))
        if hosts is None:
            pipeline.status = PipelineStatus.FAILED
            pipeline.completed_at = _utcnow()
            db.commit()
            _notify(pipeline.created_by, "pipeline_completed", _pipeline_event(pipeline))
            return

        # Phase 2 — Equipements
        targets = _run_equipments_phase(db, pipeline, hosts)
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
