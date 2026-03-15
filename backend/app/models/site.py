"""
Modèle Site — Emplacements physiques d'une entreprise.
"""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    adresse: Mapped[str | None] = mapped_column(String(500))

    # FK
    entreprise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entreprises.id"), nullable=False, index=True
    )

    # Relations
    entreprise: Mapped["Entreprise"] = relationship(back_populates="sites")  # type: ignore[name-defined]
    equipements: Mapped[list["Equipement"]] = relationship(  # type: ignore[name-defined]
        back_populates="site", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def equipement_count(self) -> int:
        return len(self.equipements) if self.equipements else 0

    scans: Mapped[list["ScanReseau"]] = relationship(  # type: ignore[name-defined]
        back_populates="site", cascade="all, delete-orphan", lazy="selectin"
    )
    network_links: Mapped[list["NetworkLink"]] = relationship(  # type: ignore[name-defined]
        back_populates="site",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    network_map_layout: Mapped["NetworkMapLayout | None"] = relationship(  # type: ignore[name-defined]
        back_populates="site",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    outbound_site_connections: Mapped[list["SiteConnection"]] = relationship(  # type: ignore[name-defined]
        back_populates="source_site",
        foreign_keys="SiteConnection.source_site_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    inbound_site_connections: Mapped[list["SiteConnection"]] = relationship(  # type: ignore[name-defined]
        back_populates="target_site",
        foreign_keys="SiteConnection.target_site_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Site(id={self.id}, nom='{self.nom}')>"
