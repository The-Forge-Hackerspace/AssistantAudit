"""
Modèles Framework (Référentiel) — Le cœur de l'approche CISO-like.

Un Framework contient des catégories, qui contiennent des contrôles (points de vérification).
Les frameworks sont chargés depuis des fichiers YAML et persistés en base pour le suivi.
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ControlSeverity(str, PyEnum):
    """Niveau de sévérité d'un point de contrôle"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CheckType(str, PyEnum):
    """Type de vérification : manuelle, automatique, ou semi-auto"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SEMI_AUTOMATIC = "semi-automatic"


class Framework(Base):
    """
    Référentiel d'audit — équivalent d'un framework CISO Assistant.
    Chaque type d'équipement ou domaine (firewall, M365, AD, etc.)
    possède son propre référentiel de contrôles.
    """
    __tablename__ = "frameworks"
    __table_args__ = (
        UniqueConstraint("ref_id", "version", name="uq_framework_ref_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ref_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    engine: Mapped[str | None] = mapped_column(String(50))  # nmap | monkey365 | ssh | winrm | manual
    engine_config: Mapped[dict | None] = mapped_column(JSON)  # config moteur (auth, plugins...)
    source: Mapped[str | None] = mapped_column(String(500))  # recommandations sur lesquelles le framework est basé
    author: Mapped[str | None] = mapped_column(String(200))  # créateur du framework
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_file: Mapped[str | None] = mapped_column(String(500))  # chemin YAML source
    source_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256 du fichier YAML

    # Versioning
    parent_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("frameworks.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relations
    categories: Mapped[list["FrameworkCategory"]] = relationship(
        back_populates="framework", cascade="all, delete-orphan",
        lazy="selectin", order_by="FrameworkCategory.order"
    )
    parent_version: Mapped["Framework | None"] = relationship(
        remote_side="Framework.id", foreign_keys=[parent_version_id],
    )

    def __repr__(self) -> str:
        return f"<Framework(ref_id='{self.ref_id}', name='{self.name}', v{self.version})>"

    @property
    def total_controls(self) -> int:
        return sum(len(cat.controls) for cat in self.categories)


class FrameworkCategory(Base):
    """Catégorie de contrôles au sein d'un référentiel."""
    __tablename__ = "framework_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # FK
    framework_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("frameworks.id"), nullable=False, index=True
    )

    # Relations
    framework: Mapped["Framework"] = relationship(back_populates="categories")
    controls: Mapped[list["Control"]] = relationship(
        back_populates="category", cascade="all, delete-orphan",
        lazy="selectin", order_by="Control.order"
    )

    def __repr__(self) -> str:
        return f"<FrameworkCategory(id={self.id}, name='{self.name}')>"


class Control(Base):
    """
    Point de contrôle individuel — un check d'audit.
    Chaque contrôle a un ID unique (ex: FW-001), une sévérité,
    et peut être vérifié manuellement ou automatiquement.
    """
    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ref_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[ControlSeverity] = mapped_column(
        Enum(ControlSeverity), default=ControlSeverity.MEDIUM, nullable=False
    )
    check_type: Mapped[CheckType] = mapped_column(
        Enum(CheckType), default=CheckType.MANUAL, nullable=False
    )
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Vérification automatique
    auto_check_function: Mapped[str | None] = mapped_column(String(200))  # nom de la fonction auto
    engine_rule_id: Mapped[str | None] = mapped_column(String(200))  # ID de règle Monkey365, etc.

    # Références externes
    cis_reference: Mapped[str | None] = mapped_column(String(200))
    remediation: Mapped[str | None] = mapped_column(Text)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # FK
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("framework_categories.id"), nullable=False, index=True
    )

    # Relations
    category: Mapped["FrameworkCategory"] = relationship(back_populates="controls")

    def __repr__(self) -> str:
        return f"<Control(ref_id='{self.ref_id}', title='{self.title}', severity={self.severity.value})>"
