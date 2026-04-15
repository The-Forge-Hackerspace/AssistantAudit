"""
Modèle CollectPipeline — Pipeline de collecte multi-étapes (TOS-13 / US009).

Un pipeline enchaîne :
  1. un scan Nmap de découverte sur un sous-réseau,
  2. la création/déduplication d'équipements à partir des hôtes découverts,
  3. une collecte SSH/WinRM sur chaque équipement selon le profil détecté.

Les compteurs par étape permettent de restituer la progression au frontend
sans recalculer à partir des tables filles (scan_hosts, collect_results).
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PipelineStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStepStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CollectPipeline(Base):
    """Pipeline orchestrant scan → équipements → collectes sur un sous-réseau."""

    __tablename__ = "collect_pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Cible du pipeline (CIDR, plage, IP…)
    target: Mapped[str] = mapped_column(String(255), nullable=False)

    # Statut global du pipeline
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus), default=PipelineStatus.PENDING, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # Étape 1 — Scan Nmap
    scan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scans_reseau.id"), index=True)
    scan_status: Mapped[PipelineStepStatus] = mapped_column(
        Enum(PipelineStepStatus), default=PipelineStepStatus.PENDING, nullable=False
    )
    hosts_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Étape 2 — Création d'équipements (dédupliqués)
    equipments_status: Mapped[PipelineStepStatus] = mapped_column(
        Enum(PipelineStepStatus), default=PipelineStepStatus.PENDING, nullable=False
    )
    equipments_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hosts_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Étape 3 — Collectes SSH/WinRM par équipement
    collects_status: Mapped[PipelineStepStatus] = mapped_column(
        Enum(PipelineStepStatus), default=PipelineStepStatus.PENDING, nullable=False
    )
    collects_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collects_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collects_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Horodatage
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relations
    scan: Mapped["ScanReseau | None"] = relationship()  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<CollectPipeline(id={self.id}, site_id={self.site_id}, "
            f"target='{self.target}', status='{self.status}')>"
        )
