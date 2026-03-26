"""
Modèle Attachment — Pièces jointes (captures d'écran, configs, etc.)
liées à un résultat de contrôle (ControlResult).

Le fichier physique est stocké dans :
  data/{entreprise_nom}/{site_nom}/{equipement_hostname_or_ip}/

La base de données ne stocke que le chemin relatif.
"""
from datetime import datetime, timezone

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Attachment(Base):
    """Pièce jointe uploadée pour un résultat de contrôle."""
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK vers le résultat de contrôle
    control_result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("control_results.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Fichier
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # chemin relatif dans data/
    mime_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # en octets

    # Description optionnelle
    description: Mapped[str | None] = mapped_column(Text)

    # Chiffrement envelope (fichiers sur disque)
    file_uuid: Mapped[str | None] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4())
    )  # Nom du fichier chiffre sur disque : {file_uuid}.enc dans data/blobs/
    encrypted_dek: Mapped[bytes | None] = mapped_column(LargeBinary)
    dek_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    kek_version: Mapped[int | None] = mapped_column(Integer, default=1)

    # Métadonnées
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    # TODO: Migrer uploaded_by vers Integer FK users.id dans une etape ulterieure
    uploaded_by: Mapped[str | None] = mapped_column(String(200))

    # Relations
    control_result: Mapped["ControlResult"] = relationship(  # type: ignore[name-defined]
        back_populates="attachments"
    )

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, filename='{self.original_filename}')>"
