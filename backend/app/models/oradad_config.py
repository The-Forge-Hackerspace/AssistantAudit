"""
Modele OradadConfig — Profil de configuration pour ORADAD (ANSSI).
Stocke les parametres du fichier config-oradad.xml.
Les domaines explicites (avec credentials) sont chiffres via EncryptedText.
"""
import json
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from ..core.encryption import EncryptedText


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Filtre SYSVOL par defaut (identique au XML ANSSI de reference)
DEFAULT_SYSVOL_FILTER = (
    "*.bat;*.vbs;*.ps1;*.psm1;*.psd1;*.cmd;*.js;*.wsf;*.wsh;"
    "*.inf;*.ini;*.cfg;*.conf;*.config;*.xml;*.pol;"
    "*.admx;*.adml;*.reg;*.msi;*.msp;*.mst;*.sct;"
    "*.htm;*.html;*.hta;*.asp;*.aspx;*.php;*.exe;*.dll;*.ocx;*.com;"
    "*.lnk;*.url;*.rdp;*.ica;*.pif;*.scr;*.cpl;*.sys;*.drv"
)


class OradadConfig(Base):
    __tablename__ = "oradad_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # Parametres de collecte — auto-detect OFF par defaut (technicien hors domaine)
    auto_get_domain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_get_trusts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    confidential: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # SYSVOL
    process_sysvol: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sysvol_filter: Mapped[str | None] = mapped_column(Text, default=DEFAULT_SYSVOL_FILTER)

    # Sortie
    output_files: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    output_mla: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Performance
    sleep_time: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Domaines explicites — chiffre car contient les credentials
    # Format JSON : [{server, port, domain_name, username, user_domain, password}]
    explicit_domains: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=_utcnow
    )

    # Relations
    owner: Mapped["User"] = relationship()  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<OradadConfig(id={self.id}, name='{self.name}')>"

    def get_domains_list(self) -> list[dict]:
        """Parse le champ explicit_domains (JSON string chiffre) en liste de dicts."""
        if not self.explicit_domains:
            return []
        if isinstance(self.explicit_domains, list):
            return self.explicit_domains
        try:
            return json.loads(self.explicit_domains)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_domains_list(self, domains: list[dict] | None) -> None:
        """Serialise la liste de domaines en JSON string pour stockage chiffre."""
        if not domains:
            self.explicit_domains = None
        else:
            self.explicit_domains = json.dumps(domains, ensure_ascii=False)

    def get_domains_masked(self) -> list[dict]:
        """Retourne les domaines sans mot de passe (pour API responses)."""
        domains = self.get_domains_list()
        return [
            {
                "server": d.get("server", ""),
                "port": d.get("port", 389),
                "domain_name": d.get("domain_name", ""),
                "username": d.get("username", ""),
                "user_domain": d.get("user_domain", ""),
            }
            for d in domains
        ]

    def to_xml(self) -> str:
        """Genere le contenu XML config-oradad.xml avec credentials en clair."""
        domains = self.get_domains_list()
        domains_xml = ""
        if domains:
            for d in domains:
                server = xml_escape(d.get("server", ""))
                port = int(d.get("port", 389))
                domain_name = xml_escape(d.get("domain_name", ""))
                username = xml_escape(d.get("username", ""))
                user_domain = xml_escape(d.get("user_domain", ""))
                password = xml_escape(d.get("password", ""))
                domains_xml += f"""
      <Domain>
        <Server>{server}</Server>
        <Port>{port}</Port>
        <DomainName>{domain_name}</DomainName>
        <User>{username}</User>
        <UserDomain>{user_domain}</UserDomain>
        <Password>{password}</Password>
      </Domain>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<ORADAD>
  <General>
    <AutoGetDomain>{str(self.auto_get_domain).lower()}</AutoGetDomain>
    <AutoGetTrusts>{str(self.auto_get_trusts).lower()}</AutoGetTrusts>
    <Level>{self.level}</Level>
    <Confidential>{self.confidential}</Confidential>
    <SleepTime>{self.sleep_time}</SleepTime>
  </General>
  <SYSVOL>
    <Process>{str(self.process_sysvol).lower()}</Process>
    <Filter>{xml_escape(self.sysvol_filter or DEFAULT_SYSVOL_FILTER)}</Filter>
  </SYSVOL>
  <Output>
    <Files>{str(self.output_files).lower()}</Files>
    <MLA>{str(self.output_mla).lower()}</MLA>
  </Output>
  <Domains>{domains_xml}
  </Domains>
</ORADAD>"""
