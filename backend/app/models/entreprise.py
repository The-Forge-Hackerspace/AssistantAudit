"""
Modèles Entreprise & Contact — Gestion des clients.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Entreprise(Base):
    __tablename__ = "entreprises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Informations de base
    nom: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    adresse: Mapped[str | None] = mapped_column(String(500))
    secteur_activite: Mapped[str | None] = mapped_column(String(100))
    siret: Mapped[str | None] = mapped_column(String(14), unique=True)

    # Informations détaillées
    presentation_desc: Mapped[str | None] = mapped_column(Text)
    organigramme_path: Mapped[str | None] = mapped_column(String(500))
    contraintes_reglementaires: Mapped[str | None] = mapped_column(Text)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relations
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="entreprise", cascade="all, delete-orphan", lazy="selectin"
    )
    audits: Mapped[list["Audit"]] = relationship(  # type: ignore[name-defined]
        back_populates="entreprise", cascade="all, delete-orphan", lazy="selectin"
    )
    sites: Mapped[list["Site"]] = relationship(  # type: ignore[name-defined]
        back_populates="entreprise", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Entreprise(id={self.id}, nom='{self.nom}')>"


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(200), index=True)
    telephone: Mapped[str | None] = mapped_column(String(20))
    is_main_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # FK
    entreprise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entreprises.id"), nullable=False
    )
    entreprise: Mapped["Entreprise"] = relationship(back_populates="contacts")

    def __repr__(self) -> str:
        main = " (Principal)" if self.is_main_contact else ""
        return f"<Contact(id={self.id}, nom='{self.nom}'{main})>"
