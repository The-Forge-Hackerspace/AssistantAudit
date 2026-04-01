from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NetworkLink(Base):
    __tablename__ = "network_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    source_equipement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("equipements.id"),
        nullable=False,
        index=True,
    )
    target_equipement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("equipements.id"),
        nullable=False,
        index=True,
    )

    source_interface: Mapped[str | None] = mapped_column(String(100))
    target_interface: Mapped[str | None] = mapped_column(String(100))
    link_type: Mapped[str] = mapped_column(String(50), default="ethernet", nullable=False)
    bandwidth: Mapped[str | None] = mapped_column(String(50))
    vlan: Mapped[str | None] = mapped_column(String(100))
    network_segment: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    site: Mapped["Site"] = relationship(back_populates="network_links")  # type: ignore[name-defined]
    source_equipement: Mapped["Equipement"] = relationship(  # type: ignore[name-defined]
        back_populates="source_links",
        foreign_keys=[source_equipement_id],
    )
    target_equipement: Mapped["Equipement"] = relationship(  # type: ignore[name-defined]
        back_populates="target_links",
        foreign_keys=[target_equipement_id],
    )


class NetworkMapLayout(Base):
    __tablename__ = "network_map_layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    layout_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    site: Mapped["Site"] = relationship(back_populates="network_map_layout")  # type: ignore[name-defined]


class SiteConnection(Base):
    __tablename__ = "site_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entreprise_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("entreprises.id"),
        nullable=False,
        index=True,
    )
    source_site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    target_site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    link_type: Mapped[str] = mapped_column(String(50), default="wan", nullable=False)
    bandwidth: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    source_site: Mapped["Site"] = relationship(  # type: ignore[name-defined]
        back_populates="outbound_site_connections",
        foreign_keys=[source_site_id],
    )
    target_site: Mapped["Site"] = relationship(  # type: ignore[name-defined]
        back_populates="inbound_site_connections",
        foreign_keys=[target_site_id],
    )
    entreprise: Mapped["Entreprise"] = relationship(back_populates="site_connections")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint(
            "entreprise_id",
            "source_site_id",
            "target_site_id",
            "link_type",
            name="uq_site_connection_pair",
        ),
    )
