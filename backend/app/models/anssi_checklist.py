"""
Modele AnssiCheckpoint - Referentiel des points de controle ANSSI pour l'Active Directory.
Pre-charge en base au deploiement via un script de seed.
Source : https://www.cert.ssi.gouv.fr/uploads/guide-ad.html
"""
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class AnssiCheckpoint(Base):
    __tablename__ = "anssi_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiant ANSSI unique — ex: "vuln1_permissions_naming_context"
    vuln_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Niveau de securite ANSSI (1=critique, 2=lacunes, 3=basique, 4=bon, 5=etat de l'art)
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Titre lisible
    title_fr: Mapped[str] = mapped_column(String(500), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Description de la vulnerabilite
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Recommandation ANSSI
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    # Categorie pour regroupement dans le dashboard
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Attributs LDAP necessaires pour verifier ce point de controle
    required_attributes: Mapped[dict | None] = mapped_column(JSON, nullable=False)

    # Objets AD concernes
    target_object_types: Mapped[dict | None] = mapped_column(JSON, nullable=False)

    # Ce point est-il verifiable automatiquement a partir des donnees ORADAD ?
    auto_checkable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Severite pour le scoring interne (0-100)
    severity_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Reference vers la documentation ANSSI
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<AnssiCheckpoint(vuln_id='{self.vuln_id}', level={self.level})>"
