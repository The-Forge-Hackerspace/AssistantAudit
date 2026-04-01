"""
Config Parser — Classe de base pour l'analyse de configurations réseau.
"""
from abc import ABC, abstractmethod

from ...schemas.scan import ConfigAnalysisResult


class ConfigParserBase(ABC):
    """Classe de base pour les parsers de configuration d'équipements réseau."""

    vendor: str = "unknown"
    device_type: str = "unknown"

    @abstractmethod
    def parse(self, content: str) -> ConfigAnalysisResult:
        """
        Analyse le contenu textuel d'une configuration.

        Args:
            content: Contenu de la configuration (texte brut ou XML)

        Returns:
            ConfigAnalysisResult avec les informations extraites
        """
        ...

    @classmethod
    def detect_vendor(cls, content: str) -> str | None:
        """
        Détecte le vendeur d'après le contenu de la config.
        Retourne None si non reconnu.
        """
        content_lower = content[:5000].lower()

        if "#config-version=" in content_lower or "config system global" in content_lower:
            return "fortinet"
        if "<opnsense>" in content_lower:
            return "opnsense"
        if "hostname" in content_lower and ("interface" in content_lower) and ("ip address" in content_lower):
            if "cisco" in content_lower or "ios" in content_lower:
                return "cisco"
        if "set system host-name" in content_lower or "set interfaces" in content_lower:
            return "juniper"

        return None
