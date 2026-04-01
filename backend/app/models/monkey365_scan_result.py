"""
Modèle Monkey365ScanResult — Résultat d'un audit Monkey365 sur Microsoft 365 / Azure AD.

Stocke les métadonnées de scan, la configuration snapshot, et les résultats d'audit
pour analyse et suivi des audits Microsoft 365.
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Monkey365ScanStatus(str, PyEnum):
    AUTHENTICATING = "authenticating"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Monkey365ScanResult(Base):
    """Résultat d'un audit Monkey365, lié à une entreprise."""
    __tablename__ = "monkey365_scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entreprise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entreprises.id"), nullable=False, index=True
    )
    status: Mapped[Monkey365ScanStatus] = mapped_column(
        Enum(Monkey365ScanStatus), default=Monkey365ScanStatus.RUNNING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # Identifiant unique du scan
    scan_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Configuration snapshot (provider, tenant info, etc.)
    config_snapshot: Mapped[dict | None] = mapped_column(JSON)

    # Chemin vers les résultats du scan (destination unique : logs, meta et rapports)
    output_path: Mapped[str | None] = mapped_column(String(500))

    # Slug de l'entreprise pour référence rapide
    entreprise_slug: Mapped[str | None] = mapped_column(String(200))

    # Methode d'authentification (device_code, certificate, client_secret)
    auth_method: Mapped[str | None] = mapped_column(String(50))

    # Nombre total de findings
    findings_count: Mapped[int | None] = mapped_column(Integer)

    # Métadonnées temporelles
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Relations
    entreprise: Mapped["Entreprise"] = relationship(backref="monkey365_scans")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<Monkey365ScanResult(id={self.id}, scan_id='{self.scan_id}', "
            f"status='{self.status}', entreprise={self.entreprise_id})>"
        )
