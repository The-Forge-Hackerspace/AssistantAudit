"""
Service de dispatch de taches vers les agents.
Implemente la double verification d'ownership pour l'isolation inter-techniciens.
"""
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.agent import Agent
from ..models.agent_task import AgentTask
from ..models.audit import Audit
from ..models.oradad_config import OradadConfig

logger = logging.getLogger(__name__)


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
        audit = db.query(Audit).filter(
            Audit.id == audit_id,
            Audit.owner_id == current_user_id,
        ).first()
        if audit is None:
            raise HTTPException(status_code=404, detail="Audit introuvable")

    # Verif 2 : l'agent appartient au bon tech et est actif
    agent = db.query(Agent).filter(
        Agent.agent_uuid == agent_uuid,
        Agent.user_id == current_user_id,
        Agent.status == "active",
    ).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent introuvable ou inactif")

    # Verif 3 : l'outil est autorise
    if tool not in agent.allowed_tools:
        raise HTTPException(
            status_code=403,
            detail=f"Outil '{tool}' non autorise pour cet agent",
        )

    # Injection du XML config pour les taches ORADAD
    if tool in ("oradad", "config-oradad") and parameters.get("config_id"):
        config = db.query(OradadConfig).filter(
            OradadConfig.id == parameters["config_id"],
        ).first()
        if config is None:
            raise HTTPException(status_code=404, detail="Profil de configuration introuvable")
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

    logger.info(
        f"Task dispatched: task_uuid={task.task_uuid}, "
        f"agent={agent_uuid}, tool={tool}, user={current_user_id}"
    )
    return task
