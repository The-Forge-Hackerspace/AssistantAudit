"""CRUD agents : list, get, create, revoke, update_allowed_tools.

Style B : fonctions module-level (pas de classe statique).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from ...core.errors import ConflictError, ForbiddenError, NotFoundError
from ...core.security import create_enrollment_token
from ...models.agent import Agent
from ...models.agent_task import AgentTask
from ...models.user import User
from ...schemas.agent import AgentCreateRequest

logger = logging.getLogger(__name__)


def _settings():
    """Resolve `settings` via le package parent pour respecter les patchs."""
    from . import settings as _s

    return _s


def list_agents(db: Session, user_id: int, is_admin: bool = False) -> list[Agent]:
    """Liste les agents. Admin voit tout, auditeur voit les siens."""
    query = db.query(Agent).options(joinedload(Agent.owner))
    if not is_admin:
        query = query.filter(Agent.user_id == user_id)
    return query.all()


def get_agent(
    db: Session,
    agent_id: int,
    user_id: int,
    is_admin: bool = False,
) -> Agent:
    """Recupere un agent par ID avec verification ownership."""
    query = db.query(Agent).filter(Agent.id == agent_id)
    if not is_admin:
        query = query.filter(Agent.user_id == user_id)
    agent = query.first()
    if agent is None:
        raise NotFoundError("Agent introuvable")
    return agent


def create_agent(
    db: Session,
    data: AgentCreateRequest,
    user_id: int,
    user_role: str,
) -> tuple[Agent, str]:
    """Cree un agent et genere le code d'enrollment. Retourne (agent, code_clair)."""
    owner_id = user_id

    if data.target_user_id is not None:
        if user_role != "admin":
            raise ForbiddenError("Seul un admin peut attribuer un agent a un autre utilisateur")
        target_user = db.query(User).filter(User.id == data.target_user_id).first()
        if target_user is None or not target_user.is_active:
            raise NotFoundError("Utilisateur introuvable")
        owner_id = target_user.id

    code, code_hash, expiration = create_enrollment_token()

    agent = Agent(
        name=data.name,
        user_id=owner_id,
        allowed_tools=data.allowed_tools,
        enrollment_token_hash=code_hash,
        enrollment_token_expires=expiration,
        status="pending",
    )
    db.add(agent)
    db.flush()
    db.refresh(agent)

    logger.info(f"Agent created: uuid={agent.agent_uuid}, owner={owner_id}, by={user_id}")
    return agent, code


def revoke_agent(
    db: Session,
    agent_uuid: str,
    user_id: int,
    is_admin: bool = False,
) -> tuple[Agent, int]:
    """Revoque un agent et annule ses taches en cours.

    Returns (agent, cancelled_tasks_count) — utilise par l'endpoint pour
    afficher "Agent revoque — N taches annulees" cote frontend.
    Admin peut revoquer n'importe lequel.
    """
    query = db.query(Agent).filter(Agent.agent_uuid == agent_uuid)
    if not is_admin:
        query = query.filter(Agent.user_id == user_id)
    agent = query.first()
    if agent is None:
        raise NotFoundError("Agent introuvable")

    agent.status = "revoked"
    agent.revoked_at = datetime.now(timezone.utc)

    # Annuler toutes les taches encore actives (running/dispatched/pending)
    active_tasks = (
        db.query(AgentTask)
        .filter(
            AgentTask.agent_id == agent.id,
            AgentTask.status.in_(["pending", "dispatched", "running"]),
        )
        .all()
    )
    cancelled_count = 0
    for task in active_tasks:
        task.status = "cancelled"
        task.completed_at = datetime.now(timezone.utc)
        task.error_message = task.error_message or "Agent revoque"
        cancelled_count += 1

    db.flush()

    # Regenerer la CRL avec tous les agents revoques
    settings = _settings()
    ca_cert_path = Path(settings.CA_CERT_PATH)
    ca_key_path = Path(settings.CA_KEY_PATH)
    if ca_cert_path.exists() and ca_key_path.exists():
        from ...core.cert_manager import CertManager

        revoked_agents = (
            db.query(Agent)
            .filter(
                Agent.status == "revoked",
                Agent.cert_serial.isnot(None),
            )
            .all()
        )
        revoked_serials = [
            (int(a.cert_serial, 16), a.revoked_at or datetime.now(timezone.utc)) for a in revoked_agents
        ]
        if revoked_serials:
            mgr = CertManager(ca_cert_path, ca_key_path)
            mgr.generate_crl(revoked_serials, Path(settings.CRL_PATH))

    logger.info(
        "Agent revoked: uuid=%s, user=%s, cancelled_tasks=%s",
        agent_uuid, user_id, cancelled_count,
    )
    return agent, cancelled_count


def update_allowed_tools(
    db: Session,
    agent_uuid: str,
    allowed_tools: list[str],
    user_id: int,
    is_admin: bool = False,
) -> Agent:
    """Met a jour la liste des outils autorises pour un agent.

    Admin peut modifier n'importe quel agent ; auditeur uniquement les
    siens. La validation des outils (liste fermee) est faite cote schema
    Pydantic en amont.
    """
    query = db.query(Agent).filter(Agent.agent_uuid == agent_uuid)
    if not is_admin:
        query = query.filter(Agent.user_id == user_id)
    agent = query.first()
    if agent is None:
        raise NotFoundError("Agent introuvable")
    if agent.status == "revoked":
        raise ConflictError("Impossible de modifier un agent revoque")
    agent.allowed_tools = allowed_tools
    db.flush()
    logger.info(
        "Agent allowed_tools updated: uuid=%s, user=%s, tools=%s",
        agent_uuid, user_id, allowed_tools,
    )
    return agent
