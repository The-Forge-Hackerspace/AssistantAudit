"""
Service Collecte — façade.

Ce module préserve l'API publique historique (`from app.services.collect_service import …`)
en ré-exportant les symboles depuis le package ``app.services.collect``.

Voir ``app.services.collect`` pour l'implémentation découpée en sous-modules
(``dispatcher``, ``evaluators.{windows,linux,opnsense}``, ``findings``).
"""

from .collect import (
    LINUX_CONTROL_MAP,
    OPNSENSE_CONTROL_MAP,
    WINDOWS_CONTROL_MAP,
    _analyze_collect_findings,
    _check_equip_access,
    _evaluate_linux_check,
    _evaluate_opnsense_check,
    _evaluate_windows_check,
    _generate_summary,
    create_pending_collect,
    delete_collect_result,
    dispatch_collect_and_commit,
    dispatch_collect_to_agent,
    get_collect_result,
    hydrate_collect_from_agent_result,
    list_collect_results,
    prefill_assessment_from_collect,
)

__all__ = [
    "create_pending_collect",
    "dispatch_collect_to_agent",
    "dispatch_collect_and_commit",
    "hydrate_collect_from_agent_result",
    "list_collect_results",
    "get_collect_result",
    "delete_collect_result",
    "prefill_assessment_from_collect",
    "WINDOWS_CONTROL_MAP",
    "LINUX_CONTROL_MAP",
    "OPNSENSE_CONTROL_MAP",
    "_evaluate_windows_check",
    "_evaluate_linux_check",
    "_evaluate_opnsense_check",
    "_analyze_collect_findings",
    "_generate_summary",
    "_check_equip_access",
]
