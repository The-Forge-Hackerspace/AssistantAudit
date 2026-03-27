"""
Modele Agent — Daemon Windows enregistre aupres du serveur.
Un agent est lie a un technicien (User) et execute des outils locaux.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Liaison au technicien — 1:N (un tech peut avoir plusieurs agents)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # Securite mTLS
    cert_fingerprint: Mapped[str | None] = mapped_column(
        String(64), unique=True
    )  # SHA-256 du cert client
    cert_serial: Mapped[str | None] = mapped_column(
        String(64)
    )  # serial number du certificat pour revocation

    # Enrollment
    enrollment_token_hash: Mapped[str | None] = mapped_column(
        String(128)
    )  # SHA-256 du token d'enrollment
    enrollment_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    enrollment_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Statut : pending (cree, pas encore enrolle), active, revoked, offline
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ip: Mapped[str | None] = mapped_column(String(45))  # IPv4 ou IPv6

    # Outils autorises
    allowed_tools: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: ["nmap", "oradad", "ad_collector"]
    )

    # Metadonnees
    os_info: Mapped[str | None] = mapped_column(String(255))  # "Windows 11 Pro 23H2"
    agent_version: Mapped[str | None] = mapped_column(String(20))  # "1.0.0"

    # Revocation
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=_utcnow
    )

    # Relations
    owner: Mapped["User"] = relationship(back_populates="agents")  # type: ignore[name-defined]
    tasks: Mapped[list["AgentTask"]] = relationship(  # type: ignore[name-defined]
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', status='{self.status}')>"
