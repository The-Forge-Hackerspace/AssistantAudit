"""
Modele AgentTask — Tache dispatchee vers un agent local.
Represente une execution d'outil (nmap, oradad, ad_collector) par un agent.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=_new_uuid
    )

    # Qui
    agent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agents.id"), nullable=False, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    audit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("audits.id"), index=True
    )

    # Quoi
    tool: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Statut : pending, dispatched, running, completed, failed, cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    status_message: Mapped[str | None] = mapped_column(String(500))

    # Resultats
    result_summary: Mapped[dict | None] = mapped_column(JSON)
    result_raw: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relations
    agent: Mapped["Agent"] = relationship(back_populates="tasks")  # type: ignore[name-defined]
    owner: Mapped["User"] = relationship()  # type: ignore[name-defined]
    audit: Mapped["Audit"] = relationship()  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<AgentTask(id={self.id}, tool='{self.tool}', status='{self.status}')>"
