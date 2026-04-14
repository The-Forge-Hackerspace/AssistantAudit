"""Modèle Tag et TagAssociation — système de tags transversal (brief §5)."""

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Tag(Base):
    """Tag réutilisable avec nom, couleur, scope."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#6B7280")
    # scope: "global" = visible par tous, "audit" = lié à un audit spécifique
    scope: Mapped[str] = mapped_column(String(10), nullable=False, default="global")
    # audit_id null si scope=global, rempli si scope=audit
    audit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relations
    associations: Mapped[list["TagAssociation"]] = relationship(back_populates="tag", cascade="all, delete-orphan")

    __table_args__ = (
        # Un tag global a un nom unique ; un tag d'audit est unique par audit
        UniqueConstraint("name", "scope", "audit_id", name="uq_tag_name_scope_audit"),
        CheckConstraint("scope IN ('global', 'audit')", name="ck_tag_scope"),
        # Index partiel : unicité des noms de tags globaux (audit_id IS NULL)
        # Nécessaire car les NULL ne sont pas considérés égaux dans UNIQUE multi-colonnes
        Index(
            "uix_global_tag_name",
            "name",
            unique=True,
            sqlite_where=text("scope = 'global' AND audit_id IS NULL"),
            postgresql_where=text("scope = 'global' AND audit_id IS NULL"),
        ),
    )

    def __repr__(self):
        return f"<Tag {self.name} ({self.scope})>"


class TagAssociation(Base):
    """Liaison polymorphe tag ↔ entité (équipement, finding, checklist, etc.)."""

    __tablename__ = "tag_associations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    # Type de l'entité taggée : "equipement", "control_result", "checklist_response", etc.
    taggable_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # ID de l'entité taggée
    taggable_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relations
    tag: Mapped["Tag"] = relationship(back_populates="associations")

    __table_args__ = (
        # Pas de double tag sur la même entité
        UniqueConstraint("tag_id", "taggable_type", "taggable_id", name="uq_tag_assoc"),
        Index("ix_tag_assoc_entity", "taggable_type", "taggable_id"),
    )

    def __repr__(self):
        return f"<TagAssociation tag={self.tag_id} → {self.taggable_type}:{self.taggable_id}>"
