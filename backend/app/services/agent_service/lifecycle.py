"""Lifecycle agent : heartbeat, mise hors-ligne, enrollment.

Style B : fonctions module-level (pas de classe statique).
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from sqlalchemy.orm import Session

from ...core.errors import BusinessRuleError
from ...core.rate_limit import enroll_rate_limiter
from ...core.security import create_agent_token
from ...models.agent import Agent
from ...models.agent_task import AgentTask
from ...schemas.agent import HeartbeatRequest

logger = logging.getLogger(__name__)


def _settings():
    """Resolve `settings` via le package parent pour respecter les patchs
    (`patch("app.services.agent_service.settings")` utilise par les tests)."""
    from . import settings as _s

    return _s


def update_agent_status(
    db: Session,
    agent: Agent,
    body: HeartbeatRequest,
    request: Request,
) -> None:
    """Met a jour last_seen et metadonnees d'un agent (heartbeat)."""
    agent.last_seen = datetime.now(timezone.utc)
    agent.last_ip = request.client.host if request.client else None
    if body.agent_version:
        agent.agent_version = body.agent_version
    if body.os_info:
        agent.os_info = body.os_info
    db.flush()


def mark_agent_offline_and_fail_tasks(
    db: Session,
    agent: Agent,
    reason: str,
    mark_offline: bool = True,
) -> list[dict]:
    """Marque un agent offline et ses taches non-terminales en failed.

    Retourne la liste des evenements task_status a emettre vers le owner
    (task_uuid + message d'erreur). La session n'est pas commitee :
    la responsabilite du commit reste a l'appelant.

    Args:
        db: session SQLAlchemy
        agent: l'agent cible
        reason: motif stocke dans task.error_message
        mark_offline: si True, positionne agent.status = 'offline'
    """
    now = datetime.now(timezone.utc)

    if mark_offline and agent.status == "active":
        agent.status = "offline"

    orphans = (
        db.query(AgentTask)
        .filter(
            AgentTask.agent_id == agent.id,
            AgentTask.status.in_(["running", "dispatched", "pending"]),
        )
        .all()
    )

    events: list[dict] = []
    for task in orphans:
        task.status = "failed"
        task.error_message = reason
        task.completed_at = now
        events.append(
            {
                "task_uuid": task.task_uuid,
                "status": "failed",
                "error_message": reason,
            }
        )

    db.flush()
    return events


def enroll_agent(db: Session, enrollment_code: str, request: Request) -> dict:
    """
    Enrolle un agent avec un code d'enrollment.
    Valide le code, signe le cert, retourne {agent_uuid, agent_token, certs}.
    """
    enroll_rate_limiter.acquire_attempt(request)

    code_hash = hashlib.sha256(enrollment_code.encode()).hexdigest()
    matched_agent = (
        db.query(Agent)
        .filter(
            Agent.status == "pending",
            Agent.enrollment_used == False,  # noqa: E712
            Agent.enrollment_token_hash == code_hash,
        )
        .with_for_update()
        .first()
    )

    if matched_agent is None:
        raise BusinessRuleError("Code d'enrollment invalide ou expire")

    # Vérifier expiration
    now = datetime.now(timezone.utc)
    exp = matched_agent.enrollment_token_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        raise BusinessRuleError("Code d'enrollment invalide ou expire")

    # Generer le certificat client
    settings = _settings()
    cert_pem = b""
    key_pem = b""
    ca_cert_path = Path(settings.CA_CERT_PATH)
    ca_key_path = Path(settings.CA_KEY_PATH)
    if ca_cert_path.exists() and ca_key_path.exists():
        from ...core.cert_manager import CertManager

        mgr = CertManager(ca_cert_path, ca_key_path)
        cert_pem, key_pem = mgr.sign_agent_cert(matched_agent.agent_uuid)

        matched_agent.cert_fingerprint = CertManager.get_cert_fingerprint(cert_pem)
        matched_agent.cert_serial = CertManager.get_cert_serial(cert_pem)
        matched_agent.cert_expires_at = CertManager.get_cert_expiry(cert_pem)

    # Generer le JWT agent
    agent_token = create_agent_token(
        agent_uuid=matched_agent.agent_uuid,
        owner_id=matched_agent.user_id,
    )

    # Mettre a jour l'agent
    matched_agent.status = "active"
    matched_agent.enrollment_used = True
    matched_agent.last_seen = datetime.now(timezone.utc)
    matched_agent.last_ip = request.client.host if request.client else None
    db.flush()

    # Lire le certificat CA
    ca_cert_pem = ""
    ca_cert_path = Path(settings.CA_CERT_PATH)
    try:
        ca_cert_pem = ca_cert_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("CA cert introuvable (%s) — ca_cert_pem vide", ca_cert_path)

    logger.info(f"Agent enrolled: uuid={matched_agent.agent_uuid}")
    return {
        "agent_uuid": matched_agent.agent_uuid,
        "agent_token": agent_token,
        "client_cert_pem": cert_pem.decode("utf-8") if cert_pem else "",
        "client_key_pem": key_pem.decode("utf-8") if key_pem else "",
        "ca_cert_pem": ca_cert_pem,
        "allowed_tools": matched_agent.allowed_tools or [],
        "agent_name": matched_agent.name or "",
    }
