"""
Service Agent : CRUD agents, enrollment, heartbeat, operations sur taches/artifacts.
"""
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from ..core.config import get_settings
from ..core.rate_limit import enroll_rate_limiter
from ..core.security import (
    create_agent_token,
    create_enrollment_token,
)
from ..models.agent import Agent
from ..models.agent_task import AgentTask
from ..models.task_artifact import TaskArtifact
from ..models.user import User
from ..schemas.agent import (
    AgentCreateRequest,
    HeartbeatRequest,
    TaskResultSubmit,
    TaskStatusUpdate,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentService:

    # ── CRUD Agent ───────────────────────────────────────────────────────

    @staticmethod
    def list_agents(db: Session, user_id: int, is_admin: bool = False) -> list[Agent]:
        """Liste les agents. Admin voit tout, auditeur voit les siens."""
        query = db.query(Agent).options(joinedload(Agent.owner))
        if not is_admin:
            query = query.filter(Agent.user_id == user_id)
        return query.all()

    @staticmethod
    def get_agent(
        db: Session, agent_id: int, user_id: int, is_admin: bool = False,
    ) -> Agent:
        """Recupere un agent par ID avec verification ownership."""
        query = db.query(Agent).filter(Agent.id == agent_id)
        if not is_admin:
            query = query.filter(Agent.user_id == user_id)
        agent = query.first()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent introuvable")
        return agent

    @staticmethod
    def create_agent(
        db: Session, data: AgentCreateRequest, user_id: int, user_role: str,
    ) -> tuple[Agent, str]:
        """Cree un agent et genere le code d'enrollment. Retourne (agent, code_clair)."""
        owner_id = user_id

        if data.target_user_id is not None:
            if user_role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Seul un admin peut attribuer un agent a un autre utilisateur",
                )
            target_user = db.query(User).filter(User.id == data.target_user_id).first()
            if target_user is None or not target_user.is_active:
                raise HTTPException(status_code=404, detail="Utilisateur introuvable")
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

        logger.info(
            f"Agent created: uuid={agent.agent_uuid}, owner={owner_id}, by={user_id}"
        )
        return agent, code

    @staticmethod
    def revoke_agent(
        db: Session, agent_uuid: str, user_id: int, is_admin: bool = False,
    ) -> Agent:
        """Revoque un agent. Admin peut revoquer n'importe lequel."""
        query = db.query(Agent).filter(Agent.agent_uuid == agent_uuid)
        if not is_admin:
            query = query.filter(Agent.user_id == user_id)
        agent = query.first()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent introuvable")

        agent.status = "revoked"
        agent.revoked_at = datetime.now(timezone.utc)
        db.flush()

        # Regenerer la CRL avec tous les agents revoques
        ca_cert_path = Path(settings.CA_CERT_PATH)
        ca_key_path = Path(settings.CA_KEY_PATH)
        if ca_cert_path.exists() and ca_key_path.exists():
            from ..core.cert_manager import CertManager
            revoked_agents = db.query(Agent).filter(
                Agent.status == "revoked",
                Agent.cert_serial.isnot(None),
            ).all()
            revoked_serials = [
                (int(a.cert_serial, 16), a.revoked_at or datetime.now(timezone.utc))
                for a in revoked_agents
            ]
            if revoked_serials:
                mgr = CertManager(ca_cert_path, ca_key_path)
                mgr.generate_crl(revoked_serials, Path(settings.CRL_PATH))

        logger.info(f"Agent revoked: uuid={agent_uuid}, user={user_id}")
        return agent

    @staticmethod
    def update_agent_status(
        db: Session, agent: Agent, body: HeartbeatRequest, request: Request,
    ) -> None:
        """Met a jour last_seen et metadonnees d'un agent (heartbeat)."""
        agent.last_seen = datetime.now(timezone.utc)
        agent.last_ip = request.client.host if request.client else None
        if body.agent_version:
            agent.agent_version = body.agent_version
        if body.os_info:
            agent.os_info = body.os_info
        db.flush()

    @staticmethod
    def enroll_agent(db: Session, enrollment_code: str, request: Request) -> dict:
        """
        Enrolle un agent avec un code d'enrollment.
        Valide le code, signe le cert, retourne {agent_uuid, agent_token, certs}.
        """
        enroll_rate_limiter.check(request)
        enroll_rate_limiter.record_attempt(request)

        code_hash = hashlib.sha256(enrollment_code.encode()).hexdigest()
        matched_agent = db.query(Agent).filter(
            Agent.status == "pending",
            Agent.enrollment_used == False,  # noqa: E712
            Agent.enrollment_token_hash == code_hash,
        ).with_for_update().first()

        if matched_agent is None:
            raise HTTPException(
                status_code=400,
                detail="Code d'enrollment invalide ou expire",
            )

        # Vérifier expiration
        now = datetime.now(timezone.utc)
        exp = matched_agent.enrollment_token_expires
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
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
            from ..core.cert_manager import CertManager
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
        if ca_cert_path.exists():
            ca_cert_pem = ca_cert_path.read_text(encoding="utf-8")

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

    # ── Operations sur taches ────────────────────────────────────────────

    @staticmethod
    def list_tasks(
        db: Session, user_id: int, is_admin: bool = False, tool: str | None = None,
    ) -> list[dict]:
        """Liste les taches agent avec resolution site/entreprise."""
        from ..models.entreprise import Entreprise
        from ..models.site import Site
        from ..schemas.agent import TaskResponse

        query = db.query(AgentTask)
        if not is_admin:
            query = query.filter(AgentTask.owner_id == user_id)
        if tool:
            query = query.filter(AgentTask.tool == tool)
        tasks = query.order_by(AgentTask.created_at.desc()).limit(100).all()

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

    @staticmethod
    def delete_task(
        db: Session, task_uuid: str, user_id: int, is_admin: bool = False,
    ) -> None:
        """Supprime une tache. Verifie ownership."""
        task = db.query(AgentTask).filter(AgentTask.task_uuid == task_uuid).first()
        if task is None:
            raise HTTPException(status_code=404, detail="Tache introuvable")
        if task.owner_id != user_id and not is_admin:
            raise HTTPException(status_code=404, detail="Tache introuvable")
        if task.status == "running":
            raise HTTPException(status_code=400, detail="Impossible de supprimer une tache en cours")
        db.delete(task)
        db.flush()

    @staticmethod
    def get_agent_task(db: Session, task_uuid: str, agent_id: int) -> AgentTask:
        """Recupere une tache par UUID pour un agent donne."""
        task = db.query(AgentTask).filter(
            AgentTask.task_uuid == task_uuid,
            AgentTask.agent_id == agent_id,
        ).first()
        if task is None:
            raise HTTPException(status_code=404, detail="Tache introuvable")
        return task

    @staticmethod
    def update_task_status(
        db: Session, task_uuid: str, agent_id: int, body: TaskStatusUpdate,
    ) -> AgentTask:
        """Met a jour le status/progress d'une tache. Retourne la tache mise a jour."""
        task = db.query(AgentTask).filter(
            AgentTask.task_uuid == task_uuid,
            AgentTask.agent_id == agent_id,
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
        db.flush()
        return task

    @staticmethod
    def submit_task_result(
        db: Session, task_uuid: str, agent_id: int, body: TaskResultSubmit,
    ) -> AgentTask:
        """Soumet les resultats d'une tache. Retourne la tache mise a jour."""
        task = db.query(AgentTask).filter(
            AgentTask.task_uuid == task_uuid,
            AgentTask.agent_id == agent_id,
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

        db.flush()
        return task

    @staticmethod
    def upload_artifact(
        db: Session,
        task_uuid: str,
        agent_id: int,
        content: bytes,
        original_filename: str,
        content_type: str,
    ) -> TaskArtifact:
        """Chiffre et stocke un artifact pour une tache."""
        task = db.query(AgentTask).filter(
            AgentTask.task_uuid == task_uuid,
            AgentTask.agent_id == agent_id,
        ).first()
        if task is None:
            raise HTTPException(status_code=404, detail="Tache introuvable")
        if task.status == "cancelled":
            raise HTTPException(status_code=400, detail="Tache annulee — upload refuse")

        # Chiffrer avec envelope encryption
        from ..core.file_encryption import EnvelopeEncryption
        envelope = EnvelopeEncryption()
        encrypted_data, encrypted_dek, dek_nonce = envelope.encrypt_file(content)

        # Stocker sur disque
        import uuid as uuid_mod
        file_uuid = str(uuid_mod.uuid4())
        blobs_dir = Path(settings.DATA_DIR) / "blobs"
        blobs_dir.mkdir(parents=True, exist_ok=True)
        file_path = blobs_dir / f"{file_uuid}.enc"
        file_path.write_bytes(encrypted_data)

        artifact = TaskArtifact(
            agent_task_id=task.id,
            file_uuid=file_uuid,
            original_filename=original_filename,
            stored_filename=f"{file_uuid}.enc",
            mime_type=content_type,
            file_size=len(content),
            encrypted_dek=encrypted_dek if encrypted_dek else None,
            dek_nonce=dek_nonce if dek_nonce else None,
            kek_version=1 if envelope.enabled else None,
        )
        db.add(artifact)
        db.flush()
        db.refresh(artifact)

        logger.info(
            f"Artifact uploaded: task={task_uuid}, file={original_filename} "
            f"({len(content)} bytes)"
        )
        return artifact

    @staticmethod
    def list_artifacts(
        db: Session, task_uuid: str, user_id: int, is_admin: bool = False,
    ) -> list[TaskArtifact]:
        """Liste les artifacts d'une tache avec verification ownership."""
        task = db.query(AgentTask).filter(AgentTask.task_uuid == task_uuid).first()
        if task is None:
            raise HTTPException(status_code=404, detail="Tache introuvable")
        if task.owner_id != user_id and not is_admin:
            raise HTTPException(status_code=404, detail="Tache introuvable")

        return (
            db.query(TaskArtifact)
            .filter(TaskArtifact.agent_task_id == task.id)
            .order_by(TaskArtifact.uploaded_at.desc())
            .all()
        )
