"""Operations sur les taches agent : list, delete, get, status, result.

Style B : fonctions module-level (pas de classe statique).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ...core.errors import BusinessRuleError, NotFoundError
from ...models.agent_task import AgentTask
from ...schemas.agent import TaskResultSubmit, TaskStatusUpdate

logger = logging.getLogger(__name__)


def list_tasks(
    db: Session,
    user_id: int,
    is_admin: bool = False,
    tool: str | None = None,
    agent_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """Liste les taches agent avec resolution site/entreprise.

    agent_id : restreint au scope d'un agent (utile pour le detail).
    limit : plafond de resultats (1-500).
    """
    from ...models.entreprise import Entreprise
    from ...models.site import Site
    from ...schemas.agent import TaskResponse

    limit = max(1, min(limit, 500))

    query = db.query(AgentTask)
    if not is_admin:
        query = query.filter(AgentTask.owner_id == user_id)
    if tool:
        query = query.filter(AgentTask.tool == tool)
    if agent_id is not None:
        query = query.filter(AgentTask.agent_id == agent_id)
    tasks = query.order_by(AgentTask.created_at.desc()).limit(limit).all()

    # Batch-resolve site and entreprise names
    site_ids = set()
    for t in tasks:
        sid = (t.parameters or {}).get("site_id")
        if sid:
            site_ids.add(int(sid))
    sites_map: dict[int, tuple[str, int | None]] = {}
    if site_ids:
        for s in db.query(Site).filter(Site.id.in_(site_ids)).all():
            sites_map[s.id] = (s.nom, s.entreprise_id)
    ent_ids = {eid for _, eid in sites_map.values() if eid}
    ent_map: dict[int, str] = {}
    if ent_ids:
        for e in db.query(Entreprise).filter(Entreprise.id.in_(ent_ids)).all():
            ent_map[e.id] = e.nom

    result = []
    for t in tasks:
        d = TaskResponse.model_validate(t).model_dump()
        sid = (t.parameters or {}).get("site_id")
        if sid and int(sid) in sites_map:
            site_name, ent_id = sites_map[int(sid)]
            d["site_name"] = site_name
            d["entreprise_name"] = ent_map.get(ent_id, "") if ent_id else ""
        else:
            d["site_name"] = ""
            d["entreprise_name"] = ""
        result.append(d)
    return result


def delete_task(
    db: Session,
    task_uuid: str,
    user_id: int,
    is_admin: bool = False,
) -> None:
    """Supprime une tache. Verifie ownership."""
    task = db.query(AgentTask).filter(AgentTask.task_uuid == task_uuid).first()
    if task is None:
        raise NotFoundError("Tache introuvable")
    if task.owner_id != user_id and not is_admin:
        raise NotFoundError("Tache introuvable")
    if task.status == "running":
        raise BusinessRuleError("Impossible de supprimer une tache en cours")
    db.delete(task)
    db.flush()


def get_agent_task(db: Session, task_uuid: str, agent_id: int) -> AgentTask:
    """Recupere une tache par UUID pour un agent donne."""
    task = (
        db.query(AgentTask)
        .filter(
            AgentTask.task_uuid == task_uuid,
            AgentTask.agent_id == agent_id,
        )
        .first()
    )
    if task is None:
        raise NotFoundError("Tache introuvable")
    return task


def update_task_status(
    db: Session,
    task_uuid: str,
    agent_id: int,
    body: TaskStatusUpdate,
) -> AgentTask:
    """Met a jour le status/progress d'une tache. Retourne la tache mise a jour."""
    task = (
        db.query(AgentTask)
        .filter(
            AgentTask.task_uuid == task_uuid,
            AgentTask.agent_id == agent_id,
        )
        .first()
    )
    if task is None:
        raise NotFoundError("Tache introuvable")

    now = datetime.now(timezone.utc)
    task.status = body.status
    if body.progress is not None:
        task.progress = body.progress
    if body.error_message is not None:
        task.error_message = body.error_message

    if body.status == "running" and task.started_at is None:
        task.started_at = now
    if body.status in ("completed", "failed", "cancelled"):
        task.completed_at = now
        if body.status == "completed":
            task.progress = 100

    task.status_message = f"Status: {body.status}"
    db.flush()
    return task


def submit_task_result(
    db: Session,
    task_uuid: str,
    agent_id: int,
    body: TaskResultSubmit,
) -> AgentTask:
    """Soumet les resultats d'une tache. Retourne la tache mise a jour."""
    task = (
        db.query(AgentTask)
        .filter(
            AgentTask.task_uuid == task_uuid,
            AgentTask.agent_id == agent_id,
        )
        .first()
    )
    if task is None:
        raise NotFoundError("Tache introuvable")

    task.status = "completed"
    task.progress = 100
    task.completed_at = datetime.now(timezone.utc)
    if body.result_summary is not None:
        task.result_summary = body.result_summary
    if body.result_raw is not None:
        task.result_raw = body.result_raw
    if body.error_message is not None:
        task.error_message = body.error_message
        task.status = "failed"

    db.flush()
    return task
