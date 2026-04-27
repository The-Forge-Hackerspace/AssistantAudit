"""
Service de dispatch de taches vers les agents.
Implemente la double verification d'ownership pour l'isolation inter-techniciens.
"""

import asyncio
import logging

from ..core.errors import ForbiddenError, NotFoundError
from sqlalchemy.orm import Session

from ..models.agent import Agent
from ..models.agent_task import AgentTask
from ..models.audit import Audit
from ..models.oradad_config import OradadConfig

logger = logging.getLogger(__name__)


def notify_agent_new_task(agent_uuid: str, task: AgentTask) -> None:
    """Pousse l'event `new_task` vers l'agent via WebSocket (best-effort).

    A appeler APRES le commit de la session pour eviter une race entre la
    reception du task_uuid par l'agent et sa visibilite en base. Tolerant aux
    erreurs : un echec WS ne doit pas casser le dispatch (l'agent peut aussi
    recuperer ses taches via HTTP/polling s'il est deconnecte).
    """
    try:
        from ..core.event_loop import get_app_loop
        from ..core.websocket_manager import ws_manager

        loop = get_app_loop()
        if loop is None:
            logger.warning(
                "App event loop not initialized; skipping new_task WS notify (task_uuid=%s)",
                task.task_uuid,
            )
            return

        asyncio.run_coroutine_threadsafe(
            ws_manager.send_to_agent(
                agent_uuid,
                "new_task",
                {
                    "task_uuid": task.task_uuid,
                    "tool": task.tool,
                    "parameters": task.parameters,
                },
            ),
            loop,
        )
    except Exception:
        logger.exception("Failed to push new_task WS event (task_uuid=%s)", task.task_uuid)


def dispatch_task(
    db: Session,
    agent_uuid: str,
    tool: str,
    parameters: dict,
    current_user_id: int,
    audit_id: int | None = None,
) -> AgentTask:
    """
    Cree et dispatch une tache vers un agent.
    Triple verification :
    1. Si audit_id fourni : l'audit appartient au technicien connecte
    2. L'agent cible appartient au meme technicien ET est actif
    3. L'outil demande est dans les allowed_tools de l'agent
    """
    # Verif 1 : l'audit appartient au bon tech
    if audit_id is not None:
        audit = (
            db.query(Audit)
            .filter(
                Audit.id == audit_id,
                Audit.owner_id == current_user_id,
            )
            .first()
        )
        if audit is None:
            raise NotFoundError("Audit introuvable")

    # Verif 2 : l'agent appartient au bon tech et est actif
    agent = (
        db.query(Agent)
        .filter(
            Agent.agent_uuid == agent_uuid,
            Agent.user_id == current_user_id,
            Agent.status == "active",
        )
        .first()
    )
    if agent is None:
        raise NotFoundError("Agent introuvable ou inactif")

    # Verif 3 : l'outil est autorise
    if tool not in agent.allowed_tools:
        raise ForbiddenError(f"Outil '{tool}' non autorise pour cet agent")

    # Injection du XML config pour les taches ORADAD
    if tool in ("oradad", "config-oradad") and parameters.get("config_id"):
        config = (
            db.query(OradadConfig)
            .filter(
                OradadConfig.id == parameters["config_id"],
            )
            .first()
        )
        if config is None:
            raise NotFoundError("Profil de configuration introuvable")
        parameters = {**parameters, "config_xml": config.to_xml()}

    # Creation de la tache
    task = AgentTask(
        agent_id=agent.id,
        owner_id=current_user_id,
        audit_id=audit_id,
        tool=tool,
        parameters=parameters,
        status="pending",
    )
    db.add(task)
    db.flush()
    db.refresh(task)

    logger.info(f"Task dispatched: task_uuid={task.task_uuid}, agent={agent_uuid}, tool={tool}, user={current_user_id}")
    return task
