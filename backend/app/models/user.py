"""
Modèle User — Authentification et rôles.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(50), default="auditeur")  # admin | auditeur | lecteur
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relations
    agents: Mapped[list["Agent"]] = relationship(  # type: ignore[name-defined]
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
