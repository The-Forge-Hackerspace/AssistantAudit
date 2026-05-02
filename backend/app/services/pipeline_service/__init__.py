"""PipelineService — Orchestration du pipeline multi-étapes (TOS-13 / US009).

Sous-package issu de TOS-85 (split de l'ancien `pipeline_service.py` 911L).
Réexporte l'API publique + les symboles patchés par les tests pour garantir
la compatibilité ascendante (`from app.services.pipeline_service import X`
et `monkeypatch.setattr("app.services.pipeline_service.time.sleep", ...)`).

Sous-modules :
  - ``profile`` : helpers purs de détection (NmapHost, detect_collect_profile)
  - ``prefill`` : pré-remplissage assessment depuis pipeline (TOS-15)
  - ``crud``    : create/get/list pipeline
  - ``notifications`` : WS notify + polling agent task
  - ``phases``  : phase scan + phase équipements
  - ``collects`` : phase collectes (SSH/WinRM)
  - ``lifecycle`` : orchestration top-level execute_pipeline_background
"""

from __future__ import annotations

# `time` est patché par les tests (monkeypatch.setattr(pipeline_service.time, "sleep", ...)),
# il doit donc rester accessible comme attribut module.
import time  # noqa: F401

# Idem `get_db_session` (réexport pour _SessionCounter dans les tests TOS-81).
from ...core.database import get_db_session  # noqa: F401

# Enums modèle utilisés par les tests
from ...models.collect_pipeline import (  # noqa: F401
    CollectPipeline,
    PipelineStatus,
    PipelineStepStatus,
)

# API publique : profil
from .profile import (  # noqa: F401
    AutoCollectProfile,
    NmapHost,
    NmapPort,
    _PROFILE_METHOD,
    _host_signals,
    _matches,
    _normalize_host,
    _open_port_numbers,
    detect_collect_profile,
)

# API publique : pré-remplissage
from .prefill import (  # noqa: F401
    NMAP_CONTROL_MAP,
    prefill_assessment_from_pipeline,
)

# API publique : CRUD
from .crud import (  # noqa: F401
    _utcnow,
    create_pending_pipeline,
    get_pipeline,
    list_pipelines,
)

# API publique : notifications + polling
from .notifications import (  # noqa: F401
    _notify,
    _pipeline_event,
    _poll_agent_task,
)

# API publique : phases
from .phases import (  # noqa: F401
    _run_equipments_phase,
    _run_scan_phase,
)

from .collects import _run_collects_phase  # noqa: F401

# API publique : orchestration top-level
from .lifecycle import execute_pipeline_background  # noqa: F401


__all__ = [
    # types
    "AutoCollectProfile",
    "NmapHost",
    "NmapPort",
    # detection
    "detect_collect_profile",
    # prefill
    "NMAP_CONTROL_MAP",
    "prefill_assessment_from_pipeline",
    # crud
    "create_pending_pipeline",
    "get_pipeline",
    "list_pipelines",
    # orchestration
    "execute_pipeline_background",
]
