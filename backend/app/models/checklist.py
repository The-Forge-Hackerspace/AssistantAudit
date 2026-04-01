"""Modèles checklist terrain (brief §4.2, §7.2)."""

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ChecklistTemplate(Base):
    """Template de checklist réutilisable (ex: Checklist LAN, Salle serveur)."""
    __tablename__ = "checklist_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    # "lan", "server_room", "documentation", "departure", "custom"
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    is_predefined: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    sections: Mapped[list["ChecklistSection"]] = relationship(
        back_populates="template", cascade="all, delete-orphan",
        order_by="ChecklistSection.order"
    )

    def __repr__(self):
        return f"<ChecklistTemplate {self.name}>"


class ChecklistSection(Base):
    """Section dans un template (ex: 'Architecture réseau', 'Équipements')."""
    __tablename__ = "checklist_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checklist_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    template: Mapped["ChecklistTemplate"] = relationship(back_populates="sections")
    items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="section", cascade="all, delete-orphan",
        order_by="ChecklistItem.order"
    )

    def __repr__(self):
        return f"<ChecklistSection {self.name}>"


class ChecklistItem(Base):
    """Point de contrôle individuel dans une section."""
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checklist_sections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Indice pour identifier l'item dans les rapports (ex: "1.3")
    ref_code: Mapped[str | None] = mapped_column(String(20))

    section: Mapped["ChecklistSection"] = relationship(back_populates="items")

    def __repr__(self):
        return f"<ChecklistItem {self.ref_code}: {self.label[:40]}>"


class ChecklistInstance(Base):
    """Instance d'une checklist liée à un audit (une checklist remplie)."""
    __tablename__ = "checklist_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checklist_templates.id"), nullable=False, index=True
    )
    audit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optionnel : lié à un site spécifique (multi-sites)
    site_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sites.id", ondelete="SET NULL"), index=True
    )
    filled_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft, in_progress, completed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    responses: Mapped[list["ChecklistResponse"]] = relationship(
        back_populates="instance", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Un template par audit+site (pas de doublon)
        UniqueConstraint("template_id", "audit_id", "site_id", name="uq_checklist_instance"),
        # Index partiel pour le cas sans site (site_id IS NULL) : SQLite ne considère pas
        # deux NULL comme égaux dans une contrainte UNIQUE multi-colonnes
        Index(
            "uix_checklist_instance_no_site",
            "template_id", "audit_id",
            unique=True,
            sqlite_where=text("site_id IS NULL"),
            postgresql_where=text("site_id IS NULL"),
        ),
        CheckConstraint("status IN ('draft', 'in_progress', 'completed')", name="ck_checklist_status"),
    )

    def __repr__(self):
        return f"<ChecklistInstance template={self.template_id} audit={self.audit_id}>"


class ChecklistResponse(Base):
    """Réponse à un item de checklist (statut + note + preuves)."""
    __tablename__ = "checklist_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checklist_instances.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checklist_items.id"), nullable=False, index=True
    )
    # OK, NOK, NA (non applicable), UNCHECKED (non vérifié)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="UNCHECKED"
    )
    note: Mapped[str | None] = mapped_column(Text)
    responded_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id")
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    instance: Mapped["ChecklistInstance"] = relationship(back_populates="responses")

    __table_args__ = (
        # Une seule réponse par item par instance
        UniqueConstraint("instance_id", "item_id", name="uq_checklist_response"),
        CheckConstraint(
            "status IN ('OK', 'NOK', 'NA', 'UNCHECKED')",
            name="ck_checklist_response_status"
        ),
    )

    def __repr__(self):
        return f"<ChecklistResponse item={self.item_id} status={self.status}>"
