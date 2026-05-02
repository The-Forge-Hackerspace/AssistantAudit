"""Artifacts agent : upload chiffre, listing.

Style B : fonctions module-level (pas de classe statique).
"""

import logging
import uuid as uuid_mod
from pathlib import Path

from sqlalchemy.orm import Session

from ...core.errors import BusinessRuleError, NotFoundError
from ...models.agent_task import AgentTask
from ...models.task_artifact import TaskArtifact

logger = logging.getLogger(__name__)


def _settings():
    """Resolve `settings` via le package parent pour respecter les patchs."""
    from . import settings as _s

    return _s


def upload_artifact(
    db: Session,
    task_uuid: str,
    agent_id: int,
    content: bytes,
    original_filename: str,
    content_type: str,
) -> TaskArtifact:
    """Chiffre et stocke un artifact pour une tache."""
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
    if task.status == "cancelled":
        raise BusinessRuleError("Tache annulee — upload refuse")

    # Chiffrer avec envelope encryption
    from ...core.file_encryption import EnvelopeEncryption

    envelope = EnvelopeEncryption()
    encrypted_data, encrypted_dek, dek_nonce = envelope.encrypt_file(content)

    # Stocker sur disque
    file_uuid = str(uuid_mod.uuid4())
    settings = _settings()
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

    logger.info(f"Artifact uploaded: task={task_uuid}, file={original_filename} ({len(content)} bytes)")
    return artifact


def list_artifacts(
    db: Session,
    task_uuid: str,
    user_id: int,
    is_admin: bool = False,
) -> list[TaskArtifact]:
    """Liste les artifacts d'une tache avec verification ownership."""
    task = db.query(AgentTask).filter(AgentTask.task_uuid == task_uuid).first()
    if task is None:
        raise NotFoundError("Tache introuvable")
    if task.owner_id != user_id and not is_admin:
        raise NotFoundError("Tache introuvable")

    return (
        db.query(TaskArtifact)
        .filter(TaskArtifact.agent_task_id == task.id)
        .order_by(TaskArtifact.uploaded_at.desc())
        .all()
    )
