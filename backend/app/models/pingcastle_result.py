"""
Modèle PingCastleResult — Résultat d'un audit PingCastle sur un domaine AD.

Stocke les scores de risque, les règles violées et les données PingCastle
pour analyse et pré-remplissage des contrôles d'audit Active Directory.
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PingCastleStatus(str, PyEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class PingCastleResult(Base):
    """Résultat d'un audit PingCastle, lié à un équipement (DC) optionnel."""
    __tablename__ = "pingcastle_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipement_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("equipements.id"), nullable=True, index=True
    )
    status: Mapped[PingCastleStatus] = mapped_column(
        Enum(PingCastleStatus), default=PingCastleStatus.RUNNING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # Connexion
    target_host: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)

    # Scores PingCastle (0-100, 0 = meilleur)
    global_score: Mapped[int | None] = mapped_column(Integer)
    stale_objects_score: Mapped[int | None] = mapped_column(Integer)
    privileged_accounts_score: Mapped[int | None] = mapped_column(Integer)
    trust_score: Mapped[int | None] = mapped_column(Integer)
    anomaly_score: Mapped[int | None] = mapped_column(Integer)
    maturity_level: Mapped[int | None] = mapped_column(Integer)

    # Données PingCastle détaillées (JSON)
    risk_rules: Mapped[list | None] = mapped_column(JSON)  # [{category, severity, rule_id, rationale, points}, ...]
    domain_info: Mapped[dict | None] = mapped_column(JSON)  # infos domaine (functional level, DC count, etc.)
    raw_report: Mapped[dict | None] = mapped_column(JSON)   # dump complet du XML parsé

    # Findings (constats d'audit standardisés)
    findings: Mapped[list | None] = mapped_column(JSON)
    summary: Mapped[dict | None] = mapped_column(JSON)

    # Chemin vers le rapport HTML généré par PingCastle
    report_html_path: Mapped[str | None] = mapped_column(String(500))

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Relations
    equipement: Mapped["Equipement"] = relationship(back_populates="pingcastle_results")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<PingCastleResult(id={self.id}, domain='{self.domain}', "
            f"score={self.global_score}, status='{self.status}', "
            f"equip={self.equipement_id})>"
        )
