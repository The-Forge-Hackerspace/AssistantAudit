"""
Modele TaskArtifact — Fichiers resultats uploades par un agent apres l'execution d'une tache.
Chiffres avec envelope encryption (meme pattern que Attachment).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskArtifact(Base):
    """Fichier resultat uploade par un agent pour une tache."""
    __tablename__ = "task_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK vers la tache
    agent_task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Fichier
    file_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Chiffrement envelope
    encrypted_dek: Mapped[bytes | None] = mapped_column(LargeBinary)
    dek_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    kek_version: Mapped[int | None] = mapped_column(Integer, default=1)

    # Metadonnees
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relations
    task: Mapped["AgentTask"] = relationship(back_populates="artifacts")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<TaskArtifact(id={self.id}, filename='{self.original_filename}')>"
