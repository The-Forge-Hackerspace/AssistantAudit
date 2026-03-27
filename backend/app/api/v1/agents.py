"""
Routes API pour la gestion des agents et le dispatch de taches.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from ...core.config import get_settings
from ...core.database import get_db
from ...core.deps import get_current_agent, get_current_auditeur
from ...core.security import (
    create_agent_token,
    create_enrollment_token,
    verify_enrollment_token,
)
from ...models.agent import Agent
from ...models.agent_task import AgentTask
from ...models.user import User
from ...schemas.agent import (
    AgentCreateRequest,
    AgentCreateResponse,
    AgentResponse,
    EnrollRequest,
    EnrollResponse,
    HeartbeatRequest,
    TaskDispatchRequest,
    TaskResponse,
    TaskResultSubmit,
    TaskStatusUpdate,
)
from ...services.task_service import dispatch_task

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/agents", tags=["Agents"])


# ── Routes admin/auditeur ────────────────────────────────────────────


@router.post("/create", response_model=AgentCreateResponse, status_code=201)
def create_agent(
    body: AgentCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Cree un agent et genere un code d'enrollment (valide 10 min).
    Admin peut creer pour un autre user via target_user_id."""
    owner_id = current_user.id

    if body.target_user_id is not None:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Seul un admin peut attribuer un agent a un autre utilisateur")
        target_user = db.query(User).filter(User.id == body.target_user_id).first()
        if target_user is None or not target_user.is_active:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        owner_id = target_user.id

    code, code_hash, expiration = create_enrollment_token()

    agent = Agent(
        name=body.name,
        user_id=owner_id,
        allowed_tools=body.allowed_tools,
        enrollment_token_hash=code_hash,
        enrollment_token_expires=expiration,
        status="pending",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    logger.info(f"Agent created: uuid={agent.agent_uuid}, owner={owner_id}, by={current_user.id}")
    return AgentCreateResponse(
        agent_uuid=agent.agent_uuid,
        enrollment_code=code,
        expires_at=expiration,
    )


@router.get("/")
def list_agents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Liste les agents. Admin voit tous les agents, auditeur voit les siens."""
    query = db.query(Agent).options(joinedload(Agent.owner))
    if current_user.role != "admin":
        query = query.filter(Agent.user_id == current_user.id)
    agents = query.all()
    return [
        AgentResponse(
            id=a.id,
            agent_uuid=a.agent_uuid,
            name=a.name,
            status=a.status,
            last_seen=a.last_seen,
            last_ip=a.last_ip,
            allowed_tools=a.allowed_tools,
            os_info=a.os_info,
            agent_version=a.agent_version,
            owner_name=a.owner.full_name if a.owner else None,
            revoked_at=a.revoked_at,
            created_at=a.created_at,
        ).model_dump()
        for a in agents
    ]


@router.delete("/{agent_uuid}", status_code=200)
def revoke_agent(
    agent_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Revoque un agent. Retourne 404 si pas trouve (meme s'il appartient a un autre user)."""
    agent = db.query(Agent).filter(
        Agent.agent_uuid == agent_uuid,
        Agent.user_id == current_user.id,
    ).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent introuvable")

    agent.status = "revoked"
    agent.revoked_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"Agent revoked: uuid={agent_uuid}, user={current_user.id}")
    # TODO: scheduled purge — delete agents where revoked_at < now() - 30 days
    return {"detail": "Agent revoque"}


# ── Routes agent (enrollment, heartbeat, refresh) ─────────────────────


@router.post("/enroll", response_model=EnrollResponse)
def enroll_agent(
    body: EnrollRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Enrolle un agent avec un code d'enrollment.
    PAS d'auth JWT — l'agent n'en a pas encore.
    """
    # Chercher un agent pending avec un token non utilise
    pending_agents = db.query(Agent).filter(
        Agent.status == "pending",
        Agent.enrollment_used == False,  # noqa: E712
        Agent.enrollment_token_hash.isnot(None),
    ).all()

    matched_agent = None
    for agent in pending_agents:
        if verify_enrollment_token(
            body.enrollment_code,
            agent.enrollment_token_hash,
            agent.enrollment_token_expires,
        ):
            matched_agent = agent
            break

    if matched_agent is None:
        raise HTTPException(
            status_code=400,
            detail="Code d'enrollment invalide ou expire",
        )

    # Generer le certificat client
    cert_pem = b""
    key_pem = b""
    ca_cert_path = Path(settings.CA_CERT_PATH)
    ca_key_path = Path(settings.CA_KEY_PATH)
    if ca_cert_path.exists() and ca_key_path.exists():
        from ...core.cert_manager import CertManager
        mgr = CertManager(ca_cert_path, ca_key_path)
        cert_pem, key_pem = mgr.sign_agent_cert(matched_agent.agent_uuid)

        # Stocker le fingerprint et serial
        matched_agent.cert_fingerprint = CertManager.get_cert_fingerprint(cert_pem)
        matched_agent.cert_serial = CertManager.get_cert_serial(cert_pem)

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
    db.commit()

    logger.info(f"Agent enrolled: uuid={matched_agent.agent_uuid}")
    return EnrollResponse(
        agent_uuid=matched_agent.agent_uuid,
        agent_token=agent_token,
        client_cert_pem=cert_pem.decode("utf-8") if cert_pem else "",
        client_key_pem=key_pem.decode("utf-8") if key_pem else "",
    )


@router.post("/heartbeat", status_code=200)
def agent_heartbeat(
    body: HeartbeatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Met a jour last_seen et les metadonnees de l'agent."""
    current_agent.last_seen = datetime.now(timezone.utc)
    current_agent.last_ip = request.client.host if request.client else None
    if body.agent_version:
        current_agent.agent_version = body.agent_version
    if body.os_info:
        current_agent.os_info = body.os_info
    db.commit()
    return {"detail": "OK"}


@router.post("/refresh")
def refresh_agent_token(
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Genere un nouveau JWT agent si l'agent est toujours actif."""
    new_token = create_agent_token(
        agent_uuid=current_agent.agent_uuid,
        owner_id=current_agent.user_id,
    )
    return {"agent_token": new_token}


# ── Routes taches ─────────────────────────────────────────────────────


@router.post("/tasks/dispatch", response_model=TaskResponse, status_code=201)
async def dispatch_agent_task(
    body: TaskDispatchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """
    Dispatch une tache vers un agent.
    Double verification : audit ownership + agent ownership + tool allowed.
    Notifie l'agent via WebSocket.
    """
    task = dispatch_task(
        db=db,
        agent_uuid=body.agent_uuid,
        tool=body.tool,
        parameters=body.parameters,
        current_user_id=current_user.id,
        audit_id=body.audit_id,
    )

    # Notifier l'agent via WebSocket
    from ...core.websocket_manager import ws_manager
    await ws_manager.send_to_agent(body.agent_uuid, "new_task", {
        "task_uuid": task.task_uuid,
        "tool": task.tool,
        "parameters": task.parameters,
    })

    return task


@router.patch("/tasks/{task_uuid}/status", status_code=200)
async def update_task_status(
    task_uuid: str,
    body: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Met a jour le status/progress d'une tache. Auth agent."""
    task = db.query(AgentTask).filter(
        AgentTask.task_uuid == task_uuid,
        AgentTask.agent_id == current_agent.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Tache introuvable")

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
    db.commit()

    # Notifier le user proprietaire via WebSocket
    from ...core.websocket_manager import ws_manager
    await ws_manager.send_to_user(task.owner_id, "task_status", {
        "task_uuid": task_uuid,
        "status": body.status,
        "progress": task.progress,
    })

    return {"detail": "OK"}


@router.post("/tasks/{task_uuid}/result", status_code=200)
async def submit_task_result(
    task_uuid: str,
    body: TaskResultSubmit,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Soumet les resultats d'une tache. Auth agent."""
    task = db.query(AgentTask).filter(
        AgentTask.task_uuid == task_uuid,
        AgentTask.agent_id == current_agent.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Tache introuvable")

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

    db.commit()

    # Notifier le user
    from ...core.websocket_manager import ws_manager
    await ws_manager.send_to_user(task.owner_id, "task_result", {
        "task_uuid": task_uuid,
        "status": task.status,
        "result_summary": task.result_summary,
    })

    return {"detail": "OK"}
