"""
Service Agent : CRUD agents, enrollment, heartbeat, operations sur taches/artifacts.

Sous-package compose en modules cohesifs (Style B, fonctions module-level) :
- crud           : list/get/create/revoke/update_allowed_tools
- lifecycle      : update_agent_status, mark_agent_offline_and_fail_tasks, enroll_agent
- tasks          : list/delete/get/update_status/submit_result
- artifacts      : upload/list
- websocket_ops  : ws_* helpers (sessions auto-gerees)

Compatibilite ascendante : la classe `AgentService` (facade) reexpose toutes les
fonctions sous forme de staticmethods, afin que les anciens appels
`from app.services.agent_service import AgentService` continuent de marcher.
"""

import logging

from ...core.config import get_settings
from .artifacts import list_artifacts, upload_artifact
from .crud import (
    create_agent,
    get_agent,
    list_agents,
    revoke_agent,
    update_allowed_tools,
)
from .lifecycle import (
    enroll_agent,
    mark_agent_offline_and_fail_tasks,
    update_agent_status,
)
from .tasks import (
    delete_task,
    get_agent_task,
    list_tasks,
    submit_task_result,
    update_task_status,
)
from .websocket_ops import (
    ws_handle_disconnect,
    ws_persist_task_result,
    ws_persist_task_status_or_progress,
    ws_record_heartbeat,
    ws_resolve_and_activate,
)

# Re-exports utilises par tests (ex. patch("app.services.agent_service.settings"))
logger = logging.getLogger(__name__)
settings = get_settings()


class AgentService:
    """Facade retro-compatible : delegue aux fonctions module-level.

    Conservee pour ne pas casser les appels existants
    `AgentService.method(...)`. Les nouveaux appelants doivent importer
    directement les fonctions module-level.
    """

    # CRUD
    list_agents = staticmethod(list_agents)
    get_agent = staticmethod(get_agent)
    create_agent = staticmethod(create_agent)
    revoke_agent = staticmethod(revoke_agent)
    update_allowed_tools = staticmethod(update_allowed_tools)

    # Lifecycle
    update_agent_status = staticmethod(update_agent_status)
    mark_agent_offline_and_fail_tasks = staticmethod(mark_agent_offline_and_fail_tasks)
    enroll_agent = staticmethod(enroll_agent)

    # Tasks
    list_tasks = staticmethod(list_tasks)
    delete_task = staticmethod(delete_task)
    get_agent_task = staticmethod(get_agent_task)
    update_task_status = staticmethod(update_task_status)
    submit_task_result = staticmethod(submit_task_result)

    # Artifacts
    upload_artifact = staticmethod(upload_artifact)
    list_artifacts = staticmethod(list_artifacts)

    # WebSocket helpers
    ws_resolve_and_activate = staticmethod(ws_resolve_and_activate)
    ws_record_heartbeat = staticmethod(ws_record_heartbeat)
    ws_persist_task_status_or_progress = staticmethod(ws_persist_task_status_or_progress)
    ws_persist_task_result = staticmethod(ws_persist_task_result)
    ws_handle_disconnect = staticmethod(ws_handle_disconnect)


__all__ = [
    "AgentService",
    "settings",
    # CRUD
    "list_agents",
    "get_agent",
    "create_agent",
    "revoke_agent",
    "update_allowed_tools",
    # Lifecycle
    "update_agent_status",
    "mark_agent_offline_and_fail_tasks",
    "enroll_agent",
    # Tasks
    "list_tasks",
    "delete_task",
    "get_agent_task",
    "update_task_status",
    "submit_task_result",
    # Artifacts
    "upload_artifact",
    "list_artifacts",
    # WebSocket helpers
    "ws_resolve_and_activate",
    "ws_record_heartbeat",
    "ws_persist_task_status_or_progress",
    "ws_persist_task_result",
    "ws_handle_disconnect",
]
