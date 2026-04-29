"""
Service Collecte — orchestration des collectes SSH/WinRM,
analyse des résultats et pré-remplissage des contrôles d'audit.

Ce package remplace l'ancien module monolithique ``collect_service.py`` :

- ``dispatcher`` : création, dispatch agent, hydratation, CRUD, pré-remplissage
- ``evaluators.{windows,linux,opnsense}`` : control maps + fonctions d'évaluation par OS
- ``findings`` : analyse des findings et génération de la synthèse

Le module ``collect_service.py`` reste une façade qui ré-exporte cette API
publique pour préserver les imports existants.
"""

from .dispatcher import (
    _check_equip_access,
    create_pending_collect,
    delete_collect_result,
    dispatch_collect_and_commit,
    dispatch_collect_to_agent,
    get_collect_result,
    hydrate_collect_from_agent_result,
    list_collect_results,
    prefill_assessment_from_collect,
)
from .evaluators import (
    LINUX_CONTROL_MAP,
    OPNSENSE_CONTROL_MAP,
    WINDOWS_CONTROL_MAP,
    _evaluate_linux_check,
    _evaluate_opnsense_check,
    _evaluate_windows_check,
)
from .findings import _analyze_collect_findings, _generate_summary

__all__ = [
    # API publique
    "create_pending_collect",
    "dispatch_collect_to_agent",
    "dispatch_collect_and_commit",
    "hydrate_collect_from_agent_result",
    "list_collect_results",
    "get_collect_result",
    "delete_collect_result",
    "prefill_assessment_from_collect",
    # Mappings de contrôles (utiles pour tests / introspection)
    "WINDOWS_CONTROL_MAP",
    "LINUX_CONTROL_MAP",
    "OPNSENSE_CONTROL_MAP",
    # Helpers internes ré-exportés pour compatibilité
    "_evaluate_windows_check",
    "_evaluate_linux_check",
    "_evaluate_opnsense_check",
    "_analyze_collect_findings",
    "_generate_summary",
    "_check_equip_access",
]
