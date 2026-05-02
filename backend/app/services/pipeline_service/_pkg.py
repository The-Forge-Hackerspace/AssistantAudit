"""Référence au package parent pour late-binding (TOS-85).

Permet aux sous-modules de résoudre `get_db_session`, `_run_scan_phase`,
`_notify`, etc. au moment de l'appel via les attributs du package
``pipeline_service``. C'est nécessaire pour que les tests qui patchent
``pipeline_service.get_db_session`` ou ``pipeline_service._run_scan_phase``
voient leur monkeypatch effectif depuis l'intérieur du code de production.

Usage : ``from . import _pkg`` puis ``_pkg.get().get_db_session()``.
"""

from __future__ import annotations

import sys
from types import ModuleType


def get() -> ModuleType:
    """Retourne le module package courant (`app.services.pipeline_service`)."""
    return sys.modules[__name__.rsplit(".", 1)[0]]
