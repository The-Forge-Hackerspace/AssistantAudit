"""CRUD pipeline : création, lecture, listing (TOS-13)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ...core.audit_logger import log_access_denied
from ...core.errors import NotFoundError
from ...core.helpers import user_has_access_to_entreprise
from ...models.agent import Agent
from ...models.collect_pipeline import CollectPipeline, PipelineStatus
from ...models.site import Site

logger = logging.getLogger(__name__)


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
        raise NotFoundError(f"Site {site_id} introuvable")
    if not is_admin and not user_has_access_to_entreprise(db, site.entreprise_id, created_by):
        log_access_denied(created_by, "Site", site_id, action="launch_pipeline")
        raise NotFoundError(f"Site {site_id} introuvable")

    agent = db.get(Agent, agent_id)
    if agent is None:
        raise NotFoundError(f"Agent {agent_id} introuvable")
    if not is_admin and agent.user_id != created_by:
        log_access_denied(created_by, "Agent", agent_id, action="launch_pipeline")
        raise NotFoundError(f"Agent {agent_id} introuvable")
    if agent.status != "active":
        raise NotFoundError(f"Agent {agent_id} inactif")
    if "nmap" not in (agent.allowed_tools or []):
        raise NotFoundError(f"Agent {agent_id} non autorisé à exécuter nmap")

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
