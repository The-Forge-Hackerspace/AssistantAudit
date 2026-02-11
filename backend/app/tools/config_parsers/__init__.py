"""
Package config_parsers : analyse de fichiers de configuration exportés.
(Fortinet, OPNsense, etc.)
"""

from .base import ConfigParserBase
from .fortinet import FortinetParser
from .opnsense import OPNsenseParser

__all__ = ["ConfigParserBase", "FortinetParser", "OPNsenseParser"]


def get_parser(content: str) -> ConfigParserBase | None:
    """Détecte le vendor et retourne le parser approprié, ou None."""
    vendor = ConfigParserBase.detect_vendor(content)
    parsers = {
        "fortinet": FortinetParser,
        "opnsense": OPNsenseParser,
    }
    parser_cls = parsers.get(vendor)
    return parser_cls() if parser_cls else None
