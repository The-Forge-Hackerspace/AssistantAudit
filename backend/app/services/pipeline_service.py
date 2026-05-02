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
from ..core.database import get_db_session
from ..core.helpers import user_has_access_to_entreprise
from ..models.agent import Agent
from ..models.agent_task import AgentTask
from ..models.assessment import Assessment, ComplianceStatus, ControlResult
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

# Polling des collectes SSH/WinRM agent
_COLLECT_POLL_INTERVAL_SEC = 5
_COLLECT_TIMEOUT_SEC = 15 * 60  # 15 minutes par collecte


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


# ══════════════════════════════════════════════════════════════════════════
# Pré-remplissage assessment depuis un pipeline (TOS-15 / US011)
# ══════════════════════════════════════════════════════════════════════════

# Mapping signaux Nmap → contrôles d'audit existants (référentiels YAML).
# Logique : la présence d'un port "sensible" déclenche un finding NON_COMPLIANT
# sur le contrôle ciblé. L'absence de signal NE prouve PAS la conformité, donc
# on ne marque jamais COMPLIANT depuis un scan Nmap.
NMAP_CONTROL_MAP: list[dict] = [
    {"port": 23, "proto": "tcp", "control_ref": "SW-004", "service": "Telnet",
     "reason": "Protocole non chiffré, à désactiver"},
    {"port": 23, "proto": "tcp", "control_ref": "LSRV-021", "service": "Telnet",
     "reason": "Service inutile détecté sur le serveur"},
    {"port": 21, "proto": "tcp", "control_ref": "SW-004", "service": "FTP",
     "reason": "Protocole non chiffré, à désactiver"},
    {"port": 69, "proto": "udp", "control_ref": "SW-004", "service": "TFTP",
     "reason": "Protocole non chiffré"},
    {"port": 161, "proto": "udp", "control_ref": "SW-030", "service": "SNMP",
     "reason": "Vérifier que SNMP v3 est utilisé exclusivement"},
    {"port": 3389, "proto": "tcp", "control_ref": "WSRV-031", "service": "RDP",
     "reason": "RDP exposé, vérifier NLA et restriction par IP source"},
]


def prefill_assessment_from_pipeline(
    db: Session,
    pipeline_id: int,
    assessment_id: int,
) -> dict:
    """Pré-remplit un assessment à partir des résultats d'un pipeline Nmap.

    Pour chaque hôte découvert, on confronte les ports ouverts au
    ``NMAP_CONTROL_MAP``. Chaque correspondance déclenche un finding
    ``NON_COMPLIANT`` sur le contrôle ciblé, avec la liste des hôtes concernés
    en preuve. On ne marque jamais ``COMPLIANT`` : l'absence d'un service
    dans le scan ne prouve pas qu'il est désactivé.

    Lève ``ValueError`` si pipeline ou assessment introuvable, si le pipeline
    n'est pas terminé, ou si le scan n'a produit aucun hôte exploitable.
    """
    pipeline = db.get(CollectPipeline, pipeline_id)
    if pipeline is None:
        raise ValueError(f"Pipeline #{pipeline_id} introuvable")
    if pipeline.status != PipelineStatus.COMPLETED:
        raise ValueError(
            f"Pipeline #{pipeline_id} n'est pas terminé (status={pipeline.status.value})"
        )

    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise ValueError(f"Assessment #{assessment_id} introuvable")

    if not pipeline.scan_task_uuid:
        raise ValueError("Aucun résultat à exploiter — scan vide")
    task = db.query(AgentTask).filter(AgentTask.task_uuid == pipeline.scan_task_uuid).first()
    if task is None:
        raise ValueError("Aucun résultat à exploiter — scan vide")

    raw_hosts = (task.result_summary or {}).get("hosts") or []
    hosts: list[NmapHost] = [_normalize_host(h) for h in raw_hosts if isinstance(h, dict)]
    if not hosts:
        raise ValueError("Aucun résultat à exploiter — scan vide")

    control_results = (
        db.query(ControlResult).filter(ControlResult.assessment_id == assessment_id).all()
    )
    ref_to_result: dict[str, ControlResult] = {}
    for cr in control_results:
        if cr.control and cr.control.ref_id:
            ref_to_result[cr.control.ref_id] = cr

    findings: dict[str, list[str]] = {}
    for host in hosts:
        ip = host.get("ip") or "?"
        open_ports = {
            (int(p.get("port") or 0), str(p.get("protocol") or "").lower())
            for p in host.get("ports") or []
            if p.get("state") == "open" and p.get("port")
        }
        for mapping in NMAP_CONTROL_MAP:
            key = (mapping["port"], mapping["proto"])
            if key not in open_ports:
                continue
            line = (
                f"  - {ip} : {mapping['service']} "
                f"({mapping['port']}/{mapping['proto']}) — {mapping['reason']}"
            )
            findings.setdefault(mapping["control_ref"], []).append(line)

    prefilled = 0
    non_compliant_count = 0
    details: list[dict] = []
    now = datetime.now(timezone.utc)

    for control_ref, lines in findings.items():
        cr = ref_to_result.get(control_ref)
        if cr is None:
            continue
        evidence = "[Pipeline Nmap] Services exposés détectés :\n" + "\n".join(lines)
        cr.status = ComplianceStatus.NON_COMPLIANT
        cr.evidence = evidence
        cr.auto_result = f"Pipeline Nmap : {len(lines)} finding(s)"
        cr.is_auto_assessed = True
        cr.assessed_at = now
        cr.assessed_by = "pipeline_nmap"
        prefilled += 1
        non_compliant_count += 1
        details.append(
            {
                "control_ref": control_ref,
                "control_title": cr.control.title if cr.control else "",
                "status": "non_compliant",
                "findings_count": len(lines),
            }
        )

    db.flush()
    logger.info(
        "Pré-remplissage pipeline #%s → assessment #%s : %s contrôles non-conformes",
        pipeline_id,
        assessment_id,
        non_compliant_count,
    )

    return {
        "controls_prefilled": prefilled,
        "controls_compliant": 0,
        "controls_non_compliant": non_compliant_count,
        "controls_partial": 0,
        "details": details,
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
    db.commit()
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
        from ..core.event_loop import get_app_loop
        from ..core.websocket_manager import ws_manager

        loop = get_app_loop()
        if loop is None:
            logger.warning("app_loop not available, skipping WS notification")
            return
        asyncio.run_coroutine_threadsafe(
            ws_manager.send_to_user(user_id, event_type, data), loop
        )
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


def _poll_agent_task(task_id: int, timeout_sec: int, poll_interval_sec: int) -> Optional[AgentTask]:
    """Poll l'AgentTask via une session courte par iteration (TOS-81).

    Retourne l'AgentTask en etat terminal (`completed`/`failed`/`cancelled`),
    ou None si introuvable / timeout. Aucune session n'est tenue entre deux
    iterations : chaque tick ouvre/ferme un `get_db_session()` pour ne pas
    saturer le pool SQLAlchemy ni geler un snapshot REPEATABLE READ.
    """
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        time.sleep(poll_interval_sec)
        with get_db_session() as poll_db:
            logger.debug("Pipeline polling : open short session for AgentTask #%s", task_id)
            task_reloaded = poll_db.get(AgentTask, task_id)
            if task_reloaded is None:
                return None
            if task_reloaded.status in ("completed", "failed", "cancelled"):
                # Detacher : la session se ferme apres ce bloc
                poll_db.expunge(task_reloaded)
                return task_reloaded
            # Forcer la fin de transaction implicite avant fermeture
            poll_db.rollback()
    return None  # timeout


def _run_scan_phase(
    pipeline_id: int,
    current_user_id: int,
) -> list[NmapHost] | None:
    """Phase 1 : dispatch du scan Nmap vers l'agent, polling jusqu'au résultat.

    Ouvre/ferme sa propre session courte (TOS-81). Retourne la liste des
    hôtes normalisés (ou None si échec/timeout).
    """
    from . import task_service

    logger.debug("Pipeline #%s : open scan-phase session", pipeline_id)
    with get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return None
        agent = db.get(Agent, pipeline.agent_id) if pipeline.agent_id else None
        if agent is None:
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = "Agent introuvable"
            db.commit()
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
            logger.exception("Pipeline #%s : dispatch nmap échoué", pipeline_id)
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = f"Dispatch nmap échoué : {exc}"
            db.commit()
            return None

        pipeline.scan_task_uuid = task.task_uuid
        pipeline.scan_status = PipelineStepStatus.RUNNING
        db.commit()
        agent_uuid_local = agent.agent_uuid
        task_id_local = task.id

    # Notification hors session (pas de DB I/O dans le notify).
    task_service.notify_agent_new_task(agent_uuid_local, task)
    logger.debug("Pipeline #%s : scan-phase session closed before polling", pipeline_id)

    # Polling : sessions courtes, une par iteration.
    final_task = _poll_agent_task(task_id_local, _SCAN_TIMEOUT_SEC, _SCAN_POLL_INTERVAL_SEC)

    logger.debug("Pipeline #%s : open scan-phase finalize session", pipeline_id)
    with get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return None

        if final_task is None:
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = "Timeout du scan agent ou tâche agent introuvable"
            db.commit()
            return None

        if final_task.status != "completed":
            pipeline.scan_status = PipelineStepStatus.FAILED
            pipeline.error_message = final_task.error_message or f"Scan {final_task.status}"
            db.commit()
            return None

        raw_hosts = (final_task.result_summary or {}).get("hosts") or []
        hosts: list[NmapHost] = [_normalize_host(h) for h in raw_hosts if isinstance(h, dict)]
        pipeline.hosts_discovered = len(hosts)
        pipeline.scan_status = PipelineStepStatus.COMPLETED
        db.commit()
        return hosts


def _run_equipments_phase(
    pipeline_id: int,
    hosts: list[NmapHost],
) -> list[tuple[int, AutoCollectProfile]]:
    """Phase 2 : pour chaque host, detecter le profil et creer/dedupliquer l'equipement.

    Ouvre/ferme sa propre session courte (TOS-81). Retourne la liste
    (equipement_id, profile) a collecter ensuite — on renvoie les ids
    plutôt que des objets pour eviter qu'ils survivent a la session.
    """
    logger.debug("Pipeline #%s : open equipments-phase session", pipeline_id)
    with get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return []

        pipeline.equipments_status = PipelineStepStatus.RUNNING
        db.commit()

        to_collect: list[tuple[int, AutoCollectProfile]] = []

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

            to_collect.append((equip.id, profile))

        pipeline.equipments_status = PipelineStepStatus.COMPLETED
        pipeline.collects_total = len(to_collect)
        db.commit()
        logger.debug("Pipeline #%s : equipments-phase session closed", pipeline_id)
        return to_collect


def _run_collects_phase(
    pipeline_id: int,
    targets: list[tuple[int, AutoCollectProfile]],
    *,
    agent_uuid: str,
    current_user_id: int,
    username: str,
    password: Optional[str],
    private_key: Optional[str],
    passphrase: Optional[str],
    use_ssl: bool,
    transport: str,
) -> None:
    """Phase 3 : dispatcher une collecte par equipement vers l'agent et poller le resultat.

    Sessions courtes par etape (TOS-81) : dispatch dans une session, polling
    avec sessions courtes par iteration via _poll_agent_task, finalisation
    dans une nouvelle session courte.
    """
    from . import collect_service
    from . import task_service

    if not targets:
        logger.debug("Pipeline #%s : open collects-skip session", pipeline_id)
        with get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is not None:
                pipeline.collects_status = PipelineStepStatus.SKIPPED
                db.commit()
        return

    logger.debug("Pipeline #%s : open collects-init session", pipeline_id)
    with get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return
        pipeline.collects_status = PipelineStepStatus.RUNNING
        db.commit()

    for equip_id, profile in targets:
        method, default_port, _ = _PROFILE_METHOD[profile]
        target_port = default_port
        if profile == "windows_server" and use_ssl:
            target_port = 5986

        # 1) Dispatch (session courte)
        collect_id: Optional[int] = None
        task_id: Optional[int] = None
        dispatched_task = None
        try:
            logger.debug("Pipeline #%s : open collect-dispatch session (equip=%s)", pipeline_id, equip_id)
            with get_db_session() as db:
                equip = db.get(Equipement, equip_id)
                if equip is None:
                    raise RuntimeError(f"Equipement #{equip_id} introuvable")

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

                dispatched_task = collect_service.dispatch_collect_to_agent(
                    db=db,
                    collect_id=collect_id,
                    agent_uuid=agent_uuid,
                    current_user_id=current_user_id,
                    password=password,
                    private_key=private_key,
                    passphrase=passphrase,
                    use_ssl=use_ssl,
                    transport=transport,
                )
                db.commit()
                task_id = dispatched_task.id
                # Detacher la task pour la passer hors session
                db.expunge(dispatched_task)
        except Exception:
            logger.exception(
                "Pipeline #%s : dispatch collecte echoue (equipement=%s)",
                pipeline_id,
                equip_id,
            )
            with get_db_session() as db:
                pipeline = db.get(CollectPipeline, pipeline_id)
                if pipeline is not None:
                    pipeline.collects_failed += 1
                    db.commit()
                    _notify(pipeline.created_by, "pipeline_progress", _pipeline_event(pipeline))
            continue

        # Notification hors session
        if dispatched_task is not None:
            task_service.notify_agent_new_task(agent_uuid, dispatched_task)

        # 2) Polling : sessions courtes par iteration
        final_task = _poll_agent_task(task_id, _COLLECT_TIMEOUT_SEC, _COLLECT_POLL_INTERVAL_SEC)
        timed_out = final_task is None or (
            final_task.status not in ("completed", "failed", "cancelled")
        )

        # 3) Finalisation (session courte)
        logger.debug("Pipeline #%s : open collect-finalize session (collect=%s)", pipeline_id, collect_id)
        with get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                continue
            try:
                final = db.get(CollectResult, collect_id) if collect_id else None
                if timed_out and final is not None and final.status == CollectStatus.RUNNING:
                    final.status = CollectStatus.FAILED
                    final.error_message = "Timeout de la collecte agent"
                    final.completed_at = _utcnow()
                    logger.warning(
                        "Pipeline #%s : collecte #%s timeout (task #%s)",
                        pipeline_id,
                        collect_id,
                        task_id,
                    )
                if final is not None and final.status == CollectStatus.SUCCESS:
                    pipeline.collects_done += 1
                else:
                    pipeline.collects_failed += 1
            finally:
                db.commit()
                _notify(pipeline.created_by, "pipeline_progress", _pipeline_event(pipeline))

    # Statut final de la phase : session courte de cloture
    logger.debug("Pipeline #%s : open collects-final session", pipeline_id)
    with get_db_session() as db:
        pipeline = db.get(CollectPipeline, pipeline_id)
        if pipeline is None:
            return
        if pipeline.collects_failed == pipeline.collects_total and pipeline.collects_total > 0:
            pipeline.collects_status = PipelineStepStatus.FAILED
        else:
            pipeline.collects_status = PipelineStepStatus.COMPLETED
        db.commit()


def execute_pipeline_background(
    pipeline_id: int,
    *,
    agent_uuid: Optional[str] = None,  # conserve pour compat : non utilise (agent lu depuis pipeline.agent_id)
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
    try:
        # --- Init : session courte 1 ---
        logger.debug("Pipeline #%s : open init session", pipeline_id)
        with get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                logger.error("Pipeline #%s introuvable", pipeline_id)
                return
            pipeline.status = PipelineStatus.RUNNING
            pipeline.started_at = _utcnow()
            db.commit()
            init_event = _pipeline_event(pipeline)
            init_user = pipeline.created_by
        _notify(init_user, "pipeline_started", init_event)

        # --- Phase 1 — Scan agent (session courte interne) ---
        hosts = _run_scan_phase(pipeline_id, current_user_id)
        with get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            progress_event = _pipeline_event(pipeline)
            progress_user = pipeline.created_by
        _notify(progress_user, "pipeline_progress", progress_event)
        if hosts is None:
            with get_db_session() as db:
                pipeline = db.get(CollectPipeline, pipeline_id)
                if pipeline is None:
                    return
                pipeline.status = PipelineStatus.FAILED
                pipeline.completed_at = _utcnow()
                db.commit()
                done_event = _pipeline_event(pipeline)
                done_user = pipeline.created_by
            _notify(done_user, "pipeline_completed", done_event)
            return

        # --- Phase 2 — Equipements (session courte interne) ---
        targets = _run_equipments_phase(pipeline_id, hosts)
        with get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            progress_event = _pipeline_event(pipeline)
            progress_user = pipeline.created_by
        _notify(progress_user, "pipeline_progress", progress_event)

        # --- Phase 3 — Collectes ---
        # Resoudre l'agent dans une session courte avant de lancer les collectes.
        with get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            agent = db.get(Agent, pipeline.agent_id) if pipeline.agent_id else None
            if agent is None:
                logger.error("Pipeline #%s : agent introuvable pour la phase collectes", pipeline_id)
                pipeline.collects_status = PipelineStepStatus.FAILED
                pipeline.error_message = pipeline.error_message or "Agent introuvable pour collectes"
                db.commit()
                agent_uuid_local = None
            else:
                agent_uuid_local = agent.agent_uuid

        if agent_uuid_local is not None:
            _run_collects_phase(
                pipeline_id,
                targets,
                agent_uuid=agent_uuid_local,
                current_user_id=current_user_id,
                username=username,
                password=password,
                private_key=private_key,
                passphrase=passphrase,
                use_ssl=use_ssl,
                transport=transport,
            )

        # --- Finalisation : session courte ---
        logger.debug("Pipeline #%s : open finalize session", pipeline_id)
        with get_db_session() as db:
            pipeline = db.get(CollectPipeline, pipeline_id)
            if pipeline is None:
                return
            if pipeline.collects_status == PipelineStepStatus.FAILED:
                pipeline.status = PipelineStatus.FAILED
            else:
                pipeline.status = PipelineStatus.COMPLETED
            pipeline.completed_at = _utcnow()
            db.commit()
            created_by = pipeline.created_by
            event_payload = _pipeline_event(pipeline)
        _notify(created_by, "pipeline_completed", event_payload)

    except Exception as exc:
        logger.exception("Pipeline #%s : erreur inattendue", pipeline_id)
        try:
            with get_db_session() as db:
                pipeline = db.get(CollectPipeline, pipeline_id)
                if pipeline is not None:
                    pipeline.status = PipelineStatus.FAILED
                    pipeline.error_message = str(exc)
                    pipeline.completed_at = _utcnow()
                    db.commit()
                    created_by = pipeline.created_by
                    event_payload = _pipeline_event(pipeline)
                else:
                    created_by = None
                    event_payload = None
            if created_by is not None and event_payload is not None:
                _notify(created_by, "pipeline_completed", event_payload)
        except Exception:
            logger.exception("Impossible de marquer le pipeline #%s comme failed", pipeline_id)
