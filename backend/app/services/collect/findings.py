"""Analyse des findings de sécurité et génération de la synthèse de collecte."""

from ...models.collect_result import CollectMethod, CollectResult
from .evaluators import (
    LINUX_CONTROL_MAP,
    OPNSENSE_CONTROL_MAP,
    WINDOWS_CONTROL_MAP,
    _evaluate_linux_check,
    _evaluate_opnsense_check,
    _evaluate_windows_check,
)


def _analyze_collect_findings(collect: CollectResult) -> list[dict]:
    """
    Analyse les données collectées et génère des findings de sécurité.
    Dispatche sur le device_profile pour choisir le bon référentiel.
    """
    findings: list[dict] = []
    profile = collect.device_profile or ("windows_server" if collect.method == CollectMethod.WINRM else "linux_server")

    # Sélectionner le control map et la fonction d'évaluation
    if profile == "opnsense":
        control_map = OPNSENSE_CONTROL_MAP
        evaluate_fn = _evaluate_opnsense_check
    elif profile in ("stormshield", "fortigate"):
        # Pas encore de control map → pas de findings
        return []
    elif collect.method == CollectMethod.WINRM:
        control_map = WINDOWS_CONTROL_MAP
        evaluate_fn = _evaluate_windows_check
    else:
        control_map = LINUX_CONTROL_MAP
        evaluate_fn = _evaluate_linux_check

    for mapping in control_map:
        check_name = mapping["check"]
        passed, detail = evaluate_fn(check_name, collect)

        if not passed:
            findings.append(
                {
                    "control_ref": mapping["control_ref"],
                    "title": f"Non-conformité détectée : {mapping['control_ref']}",
                    "description": detail,
                    "severity": mapping.get("severity", "medium"),
                    "category": "Sécurité",
                    "remediation": mapping.get("evidence_fail", ""),
                    "status": "non_compliant",
                }
            )

    return findings


def _generate_summary(collect: CollectResult, findings: list[dict]) -> dict:
    """Génère un résumé de la collecte."""
    is_windows = collect.method == CollectMethod.WINRM
    os_info = collect.os_info or {}
    profile = collect.device_profile or ("windows_server" if is_windows else "linux_server")

    # Sélectionner le bon control map pour le calcul
    if profile == "opnsense":
        control_map_ref = OPNSENSE_CONTROL_MAP
    elif profile in ("stormshield", "fortigate"):
        # Pas encore de control map → résumé simplifié
        security = collect.security or {}
        return {
            "os_type": profile,
            "os_name": os_info.get("distro", profile.capitalize()),
            "os_version": os_info.get("version", os_info.get("version_raw", "")),
            "hostname": collect.hostname_collected or "",
            "device_profile": profile,
            "total_checks": 0,
            "compliant": 0,
            "non_compliant": 0,
            "compliance_score": None,
            "firewall_rules_count": security.get(
                "firewall_rules_count", security.get("filter_rules_count", security.get("policy_count", 0))
            ),
        }
    elif is_windows:
        control_map_ref = WINDOWS_CONTROL_MAP
    else:
        control_map_ref = LINUX_CONTROL_MAP

    total_checks = len(control_map_ref)
    non_compliant = len(findings)
    compliant = total_checks - non_compliant

    # OS type label
    if profile == "opnsense":
        os_type = "OPNsense"
        os_name = os_info.get("distro", "OPNsense")
        os_version = os_info.get("version", "")
    elif is_windows:
        os_type = "Windows"
        os_name = os_info.get("caption", "N/A")
        os_version = os_info.get("version", "")
    else:
        os_type = "Linux"
        os_name = os_info.get("distro", "N/A")
        os_version = os_info.get("version_id", "")

    summary = {
        "os_type": os_type,
        "os_name": os_name,
        "os_version": os_version,
        "hostname": collect.hostname_collected or "",
        "device_profile": profile,
        "total_checks": total_checks,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "compliance_score": round(compliant / total_checks * 100, 1) if total_checks > 0 else 0,
    }

    # Ajouter firewall_rules_count pour les profils pare-feu
    if profile == "opnsense":
        security = collect.security or {}
        summary["firewall_rules_count"] = security.get("firewall_rules_count", 0)

    return summary
