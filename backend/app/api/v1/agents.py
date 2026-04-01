"""
Routes API pour la gestion des agents et le dispatch de taches.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_agent, get_current_auditeur
from ...core.security import create_agent_token
from ...models.agent import Agent
from ...schemas.agent import (
    AgentCreateRequest,
    AgentCreateResponse,
    AgentResponse,
    ArtifactRead,
    ArtifactUploadResponse,
    EnrollRequest,
    EnrollResponse,
    HeartbeatRequest,
    TaskDispatchRequest,
    TaskResponse,
    TaskResultSubmit,
    TaskStatusUpdate,
)
from ...services.agent_service import AgentService
from ...services.task_service import dispatch_task

logger = logging.getLogger(__name__)

MAX_ARTIFACT_SIZE = 100 * 1024 * 1024  # 100 MB

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
    agent, code = AgentService.create_agent(
        db, body, user_id=current_user.id, user_role=current_user.role,
    )
    return AgentCreateResponse(
        agent_uuid=agent.agent_uuid,
        enrollment_code=code,
        expires_at=agent.enrollment_token_expires,
    )


@router.get("/")
def list_agents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Liste les agents. Admin voit tous les agents, auditeur voit les siens."""
    agents = AgentService.list_agents(
        db, user_id=current_user.id, is_admin=current_user.role == "admin",
    )
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
    """Revoque un agent. Admin peut revoquer n'importe quel agent, auditeur seulement les siens."""
    AgentService.revoke_agent(
        db, agent_uuid, user_id=current_user.id, is_admin=current_user.role == "admin",
    )
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
    Rate-limited pour eviter le brute-force sur les codes.
    """
    result = AgentService.enroll_agent(db, body.enrollment_code, request)
    return EnrollResponse(**result)


@router.post("/heartbeat", status_code=200)
def agent_heartbeat(
    body: HeartbeatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Met a jour last_seen et les metadonnees de l'agent."""
    AgentService.update_agent_status(db, current_agent, body, request)
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


@router.get("/tasks")
def list_tasks(
    tool: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Liste les taches agent du user courant (admin voit tout). Filtrable par tool.
    Enrichit chaque tache avec site_name et entreprise_name resolus depuis les parametres."""
    return AgentService.list_tasks(
        db, user_id=current_user.id, is_admin=current_user.role == "admin", tool=tool,
    )


@router.delete("/tasks/{task_uuid}", status_code=200)
def delete_task(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Supprime une tache agent. Ownership verifiee."""
    AgentService.delete_task(
        db, task_uuid, user_id=current_user.id, is_admin=current_user.role == "admin",
    )
    return {"detail": "Tache supprimee"}


# ── Routes taches ─────────────────────────────────────────────────────


@router.post("/tasks/dispatch", response_model=TaskResponse, status_code=201)
def dispatch_agent_task(
    body: TaskDispatchRequest,
    background_tasks: BackgroundTasks,
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

    # Notifier l'agent via WebSocket (en arrière-plan)
    from ...core.websocket_manager import ws_manager
    background_tasks.add_task(
        ws_manager.send_to_agent, body.agent_uuid, "new_task", {
            "task_uuid": task.task_uuid,
            "tool": task.tool,
            "parameters": task.parameters,
        },
    )

    return task


@router.patch("/tasks/{task_uuid}/status", status_code=200)
def update_task_status(
    task_uuid: str,
    body: TaskStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Met a jour le status/progress d'une tache. Auth agent."""
    task = AgentService.update_task_status(db, task_uuid, current_agent.id, body)

    # Notifier le user proprietaire via WebSocket (en arrière-plan)
    from ...core.websocket_manager import ws_manager
    background_tasks.add_task(
        ws_manager.send_to_user, task.owner_id, "task_status", {
            "task_uuid": task_uuid,
            "status": body.status,
            "progress": task.progress,
        },
    )

    return {"detail": "OK"}


@router.post("/tasks/{task_uuid}/result", status_code=200)
def submit_task_result(
    task_uuid: str,
    body: TaskResultSubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Soumet les resultats d'une tache. Auth agent."""
    task = AgentService.submit_task_result(db, task_uuid, current_agent.id, body)

    # Notifier le user (en arrière-plan)
    from ...core.websocket_manager import ws_manager
    background_tasks.add_task(
        ws_manager.send_to_user, task.owner_id, "task_result", {
            "task_uuid": task_uuid,
            "status": task.status,
            "result_summary": task.result_summary,
        },
    )

    return {"detail": "OK"}


# ── Artifacts ─────────────────────────────────────────────────────────


@router.post("/tasks/{task_uuid}/artifacts", response_model=ArtifactUploadResponse, status_code=201)
def upload_artifact(
    task_uuid: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Upload un fichier resultat (artifact) pour une tache.
    Auth agent — l'agent uploade apres execution.
    """
    # Lire le contenu avec limite de taille
    chunks = []
    total_size = 0
    while True:
        chunk = file.file.read(8192)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_ARTIFACT_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Fichier trop volumineux (>{MAX_ARTIFACT_SIZE // (1024*1024)} Mo)",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")

    artifact = AgentService.upload_artifact(
        db,
        task_uuid=task_uuid,
        agent_id=current_agent.id,
        content=content,
        original_filename=file.filename or "artifact",
        content_type=file.content_type or "application/octet-stream",
    )

    logger.info(
        f"Artifact uploaded: task={task_uuid}, file={artifact.original_filename} "
        f"({len(content)} bytes), agent={current_agent.agent_uuid}"
    )
    return ArtifactUploadResponse(
        file_id=artifact.id,
        filename=artifact.original_filename,
        size=len(content),
    )


@router.get("/tasks/{task_uuid}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """
    Liste les artifacts d'une tache.
    Auth auditeur — le technicien consulte les resultats.
    Verifie ownership via agent -> owner_id.
    """
    artifacts = AgentService.list_artifacts(
        db, task_uuid, user_id=current_user.id, is_admin=current_user.role == "admin",
    )
    return [
        ArtifactRead(
            id=a.id,
            file_uuid=a.file_uuid,
            original_filename=a.original_filename,
            mime_type=a.mime_type,
            file_size=a.file_size,
            uploaded_at=a.uploaded_at,
            download_url=f"/api/v1/agents/tasks/{task_uuid}/artifacts/{a.id}/download",
        )
        for a in artifacts
    ]
