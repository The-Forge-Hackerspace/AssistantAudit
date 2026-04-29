"""Évaluation des contrôles de conformité Windows Server (WSRV-xxx)."""

from datetime import datetime

from ....models.collect_result import CollectResult

WINDOWS_CONTROL_MAP: list[dict] = [
    # WSRV-001 : OS supporté
    {
        "control_ref": "WSRV-001",
        "check": "os_supported",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le système d'exploitation est dans une version supportée.",
        "evidence_fail": "Le système d'exploitation n'est plus supporté par Microsoft.",
    },
    # WSRV-002 : Mises à jour installées (< 30 jours)
    {
        "control_ref": "WSRV-002",
        "check": "updates_recent",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Les mises à jour sont récentes (< 30 jours).",
        "evidence_fail": "Les mises à jour datent de plus de 30 jours.",
    },
    # WSRV-003 : Politique WSUS
    {
        "control_ref": "WSRV-003",
        "check": "wsus_configured",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le serveur est rattaché à un serveur WSUS.",
        "evidence_fail": "Aucune politique WSUS/Windows Update configurée.",
    },
    # WSRV-010 : Compte admin renommé
    {
        "control_ref": "WSRV-010",
        "check": "admin_renamed",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le compte Administrateur local a été renommé.",
        "evidence_fail": "Le compte Administrator/Administrateur n'a pas été renommé.",
    },
    # WSRV-011 : Politique de mot de passe (complexité + 12 chars)
    {
        "control_ref": "WSRV-011",
        "check": "password_policy_ok",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "La politique de mot de passe impose 12 caractères minimum.",
        "evidence_fail": "La politique de mot de passe ne respecte pas les exigences (< 12 caractères).",
    },
    # WSRV-012 : Verrouillage de compte
    {
        "control_ref": "WSRV-012",
        "check": "lockout_configured",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le verrouillage de compte est configuré.",
        "evidence_fail": "Aucun verrouillage de compte configuré.",
    },
    # WSRV-030 : Pare-feu Windows activé
    {
        "control_ref": "WSRV-030",
        "check": "firewall_all_enabled",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le pare-feu Windows est activé sur tous les profils.",
        "evidence_fail": "Le pare-feu Windows n'est pas activé sur tous les profils.",
    },
    # WSRV-031 : RDP sécurisé (NLA activé)
    {
        "control_ref": "WSRV-031",
        "check": "rdp_nla",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "RDP est sécurisé avec NLA (Network Level Authentication).",
        "evidence_fail": "RDP est actif sans NLA — risque de sécurité.",
    },
    # WSRV-040 : Audit des événements
    {
        "control_ref": "WSRV-040",
        "check": "audit_policy_configured",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "La stratégie d'audit des événements est configurée.",
        "evidence_fail": "La stratégie d'audit n'est pas configurée correctement.",
    },
    # WSRV-041 : Taille des journaux >= 100 MB
    {
        "control_ref": "WSRV-041",
        "check": "logs_min_100mb",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Les journaux d'événements ont une taille >= 100 MB.",
        "evidence_fail": "Les journaux d'événements sont inférieurs à 100 MB.",
    },
    # WSRV-051 : Antivirus/EDR installé
    {
        "control_ref": "WSRV-051",
        "check": "antivirus_active",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Un antivirus/EDR est actif et à jour.",
        "evidence_fail": "Aucun antivirus/EDR actif détecté.",
    },
]


def _evaluate_windows_check(check_name: str, collect: CollectResult) -> tuple[bool, str]:
    """
    Évalue un contrôle Windows à partir des données collectées.
    Returns: (passed: bool, evidence_detail: str)
    """
    security = collect.security or {}
    users = collect.users or {}
    updates = collect.updates or {}
    os_info = collect.os_info or {}

    if check_name == "os_supported":
        caption = os_info.get("caption", "").lower()
        # Windows Server 2012/2012R2 → fin de support
        unsupported = ["2008", "2003", "2000", "2012"]
        for ver in unsupported:
            if ver in caption:
                return False, f"OS: {os_info.get('caption', 'N/A')} — version obsolète"
        return True, f"OS: {os_info.get('caption', 'N/A')}"

    if check_name == "updates_recent":
        last = updates.get("last_update_date", "")
        if not last or "ERROR" in last:
            return False, "Impossible de déterminer la date de dernière mise à jour"
        try:
            # Tenter le parsing de la date
            from dateutil import parser as dateparser

            last_dt = dateparser.parse(last)
            if last_dt:
                diff = (datetime.now() - last_dt.replace(tzinfo=None)).days
                if diff <= 30:
                    return True, f"Dernière mise à jour il y a {diff} jours ({last})"
                return False, f"Dernière mise à jour il y a {diff} jours ({last})"
        except Exception:
            pass
        return False, f"Date dernière MàJ: {last}"

    if check_name == "wsus_configured":
        wsus = updates.get("wsus_configured", False)
        server = updates.get("wsus_server", "")
        if wsus:
            return True, f"WSUS configuré : {server}"
        return False, "Aucun serveur WSUS configuré"

    if check_name == "admin_renamed":
        renamed = users.get("admin_renamed", False)
        if renamed:
            return True, "Le compte admin SID-500 a été renommé"
        return False, "Le compte Administrator/Administrateur n'est pas renommé"

    if check_name == "password_policy_ok":
        pwd_policy = users.get("password_policy", {})
        meets = pwd_policy.get("meets_12_chars", False)
        min_len = pwd_policy.get("min_length_value", 0)
        if meets:
            return True, f"Longueur min. mot de passe : {min_len} caractères"
        return False, f"Longueur min. mot de passe : {min_len} caractères (< 12)"

    if check_name == "lockout_configured":
        configured = users.get("lockout_configured", False)
        threshold = users.get("lockout_threshold", 0)
        if configured:
            return True, f"Verrouillage après {threshold} tentatives"
        return False, "Verrouillage de compte non configuré (seuil = 0)"

    if check_name == "firewall_all_enabled":
        enabled = security.get("firewall_all_enabled", False)
        profiles = security.get("firewall_profiles", [])
        desc = ", ".join(f"{p['name']}={'On' if p.get('enabled') else 'Off'}" for p in profiles) if profiles else "N/A"
        if enabled:
            return True, f"Pare-feu actif sur tous les profils ({desc})"
        return False, f"Pare-feu non actif sur tous les profils ({desc})"

    if check_name == "rdp_nla":
        rdp_enabled = security.get("rdp_enabled", False)
        nla = security.get("rdp_nla_enabled", False)
        if not rdp_enabled:
            return True, "RDP est désactivé"
        if nla:
            return True, "RDP actif avec NLA activé"
        return False, "RDP actif sans NLA (Network Level Authentication)"

    if check_name == "audit_policy_configured":
        audit_raw = security.get("audit_policy", "")
        if audit_raw and "Success" in audit_raw and "Failure" in audit_raw:
            return True, "Stratégie d'audit configurée (succès + échecs)"
        if audit_raw and "Success" in audit_raw:
            return True, "Stratégie d'audit configurée (succès uniquement)"
        return False, "Stratégie d'audit non configurée ou incomplète"

    if check_name == "logs_min_100mb":
        ok = security.get("logs_min_100mb", False)
        logs = security.get("event_logs", [])
        desc = ", ".join(f"{l['name']}={l['max_size_mb']}MB" for l in logs) if logs else "N/A"
        if ok:
            return True, f"Journaux >= 100 MB ({desc})"
        return False, f"Journaux < 100 MB ({desc})"

    if check_name == "antivirus_active":
        active = security.get("antivirus_active", False)
        if active:
            return True, "Antivirus/EDR actif"
        return False, "Aucun antivirus/EDR actif détecté"

    return False, f"Vérification '{check_name}' non implémentée"
