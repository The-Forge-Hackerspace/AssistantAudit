"""Modèles rapport d'audit (brief §7.7)."""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text,
    CheckConstraint, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# Les 25 sections du brief §7.7, avec leur clé machine et leur titre FR
REPORT_SECTIONS = [
    ("cover",              "Page de garde"),
    ("introduction",       "Introduction"),
    ("objectives",         "Objectifs de l'audit"),
    ("scope",              "Périmètre de l'audit"),
    ("locations",          "Descriptif des lieux"),
    ("network_diagram",    "Synoptique réseau"),
    ("server_rooms",       "Descriptif des locaux informatiques"),
    ("ups",                "Onduleurs"),
    ("internet",           "Abonnements internet"),
    ("ip_plan",            "Plan d'adressage IP"),
    ("switches",           "Switches"),
    ("wifi",               "Wi-Fi"),
    ("firewall",           "Firewall"),
    ("servers",            "Analyse des serveurs"),
    ("nas",                "Analyse du NAS"),
    ("active_directory",   "Active Directory"),
    ("backups",            "Sauvegardes"),
    ("documentation",      "Documentation et outils internes"),
    ("antivirus",          "Antivirus / EDR"),
    ("microsoft365",       "Microsoft 365"),
    ("workstations",       "Parc informatique"),
    ("shadow_it",          "Shadow IT"),
    ("strengths",          "Points forts observés"),
    ("quick_wins",         "Quick wins"),
    ("synthesis",          "Synthèse globale"),
]


class AuditReport(Base):
    """Rapport généré pour un audit."""
    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("audits.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Statut du rapport
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft, generating, ready, error
    # Template utilisé
    template_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="complete"
    )  # complete, light, compliance

    # Branding
    consultant_logo_path: Mapped[str | None] = mapped_column(String(500))
    client_logo_path: Mapped[str | None] = mapped_column(String(500))
    consultant_name: Mapped[str | None] = mapped_column(String(200))
    consultant_contact: Mapped[str | None] = mapped_column(Text)

    # Fichiers générés
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    docx_path: Mapped[str | None] = mapped_column(String(500))

    # Metadata
    generated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relations
    sections: Mapped[list["ReportSection"]] = relationship(
        back_populates="report", cascade="all, delete-orphan",
        order_by="ReportSection.order"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'generating', 'ready', 'error')",
            name="ck_report_status"
        ),
        CheckConstraint(
            "template_name IN ('complete', 'light', 'compliance')",
            name="ck_report_template"
        ),
    )

    def __repr__(self):
        return f"<AuditReport audit={self.audit_id} status={self.status}>"


class ReportSection(Base):
    """Section individuelle d'un rapport — activable/désactivable."""
    __tablename__ = "report_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("audit_reports.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Clé machine de la section (ex: "cover", "firewall", "synthesis")
    section_key: Mapped[str] = mapped_column(String(50), nullable=False)
    # Titre affiché (modifiable par l'utilisateur)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Ordre d'affichage (0-24)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    # Section incluse dans le rapport ?
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Contenu personnalisé (override le contenu auto-généré)
    custom_content: Mapped[str | None] = mapped_column(Text)

    # Relations
    report: Mapped["AuditReport"] = relationship(back_populates="sections")

    __table_args__ = (
        UniqueConstraint("report_id", "section_key", name="uq_report_section_key"),
    )

    def __repr__(self):
        return f"<ReportSection {self.section_key} order={self.order}>"
