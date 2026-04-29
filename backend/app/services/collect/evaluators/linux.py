"""Évaluation des contrôles de conformité Linux Server (LSRV-xxx)."""

from ....models.collect_result import CollectResult

LINUX_CONTROL_MAP: list[dict] = [
    # LSRV-001 : Distribution supportée
    {
        "control_ref": "LSRV-001",
        "check": "os_supported",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "La distribution est dans une version LTS supportée.",
        "evidence_fail": "La distribution n'est plus supportée (fin de vie).",
    },
    # LSRV-002 : Mises à jour de sécurité
    {
        "control_ref": "LSRV-002",
        "check": "no_pending_security_updates",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Aucune mise à jour de sécurité en attente.",
        "evidence_fail": "Des mises à jour de sécurité sont en attente.",
    },
    # LSRV-003 : MàJ automatiques (unattended-upgrades)
    {
        "control_ref": "LSRV-003",
        "check": "auto_updates_configured",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Les mises à jour automatiques sont configurées.",
        "evidence_fail": "Les mises à jour automatiques ne sont pas configurées.",
    },
    # LSRV-010 : Root login SSH désactivé
    {
        "control_ref": "LSRV-010",
        "check": "ssh_root_disabled",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "La connexion root directe via SSH est désactivée (PermitRootLogin no).",
        "evidence_fail": "La connexion root via SSH est autorisée — risque de sécurité.",
    },
    # LSRV-011 : Auth SSH par clés (pas mot de passe)
    {
        "control_ref": "LSRV-011",
        "check": "ssh_password_disabled",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "L'authentification SSH par mot de passe est désactivée.",
        "evidence_fail": "L'authentification SSH par mot de passe est activée.",
    },
    # LSRV-013 : PAM configuré
    {
        "control_ref": "LSRV-013",
        "check": "pam_configured",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "PAM est configuré avec des exigences de complexité.",
        "evidence_fail": "PAM n'est pas configuré pour la politique de mot de passe.",
    },
    # LSRV-020 : Firewall activé
    {
        "control_ref": "LSRV-020",
        "check": "firewall_active",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Un pare-feu local est actif.",
        "evidence_fail": "Aucun pare-feu local actif détecté.",
    },
    # LSRV-030 : rsyslog/journald configuré
    {
        "control_ref": "LSRV-030",
        "check": "rsyslog_active",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "rsyslog est actif et fonctionnel.",
        "evidence_fail": "rsyslog n'est pas actif.",
    },
    # LSRV-032 : Auditd configuré
    {
        "control_ref": "LSRV-032",
        "check": "auditd_active",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "auditd est installé et actif.",
        "evidence_fail": "auditd n'est pas actif ou pas installé.",
    },
    # LSRV-041 : Antivirus/EDR installé
    {
        "control_ref": "LSRV-041",
        "check": "antivirus_installed",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Un agent de sécurité (EDR/antivirus) est installé.",
        "evidence_fail": "Aucun agent de sécurité détecté.",
    },
    # LSRV-042 : Permissions fichiers sensibles
    {
        "control_ref": "LSRV-042",
        "check": "file_permissions_ok",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Les permissions des fichiers sensibles sont correctes.",
        "evidence_fail": "Les permissions de /etc/shadow ou /etc/passwd sont trop permissives.",
    },
]


def _evaluate_linux_check(check_name: str, collect: CollectResult) -> tuple[bool, str]:
    """
    Évalue un contrôle Linux à partir des données collectées.
    Returns: (passed: bool, evidence_detail: str)
    """
    security = collect.security or {}
    updates = collect.updates or {}
    os_info = collect.os_info or {}

    if check_name == "os_supported":
        distro = os_info.get("distro", "").lower()
        version_id = os_info.get("version_id", "")
        # Vérifications basiques des versions EOL
        eol_patterns = [
            ("ubuntu", ["14.04", "16.04", "18.04"]),
            ("debian", ["8", "9", "10"]),
            ("centos", ["6", "7"]),  # CentOS 7 EOL juin 2024
            ("rhel", ["6", "7"]),
        ]
        for distro_key, eol_versions in eol_patterns:
            if distro_key in distro:
                for eol_ver in eol_versions:
                    if version_id.startswith(eol_ver):
                        return (
                            False,
                            f"Distribution: {os_info.get('distro')} {version_id} — potentiellement en fin de vie",
                        )
        return True, f"Distribution: {os_info.get('distro', 'N/A')} {version_id}"

    if check_name == "no_pending_security_updates":
        sec_updates = updates.get("security_updates", 0)
        if sec_updates == 0:
            return True, "Aucune mise à jour de sécurité en attente"
        return False, f"{sec_updates} mise(s) à jour de sécurité en attente"

    if check_name == "auto_updates_configured":
        configured = updates.get("auto_updates_configured", False)
        if configured:
            return True, "Mises à jour automatiques configurées"
        return False, "Mises à jour automatiques non configurées"

    if check_name == "ssh_root_disabled":
        ssh_root = security.get("ssh_permit_root_login", "NOT_SET").strip().lower()
        if "no" in ssh_root and "without-password" not in ssh_root:
            return True, f"PermitRootLogin = {ssh_root}"
        if ssh_root in ("not_set", ""):
            return False, "PermitRootLogin non défini explicitement (défaut: yes)"
        return False, f"PermitRootLogin = {ssh_root}"

    if check_name == "ssh_password_disabled":
        ssh_pass = security.get("ssh_password_authentication", "NOT_SET").strip().lower()
        if "no" in ssh_pass:
            return True, "PasswordAuthentication = no"
        return False, f"PasswordAuthentication = {ssh_pass}"

    if check_name == "pam_configured":
        pam = security.get("pam_pwquality", "NOT_CONFIGURED")
        if pam and pam != "NOT_CONFIGURED" and "minlen" in pam.lower():
            return True, "PAM pwquality configuré"
        return False, "PAM pwquality non configuré"

    if check_name == "firewall_active":
        fw = security.get("firewall_status", "none_detected")
        if fw in ("ufw_active", "iptables_active", "nftables_active"):
            return True, f"Pare-feu actif ({fw})"
        return False, f"Aucun pare-feu local actif détecté ({fw})"

    if check_name == "rsyslog_active":
        status = security.get("rsyslog_active", "inactive")
        if status == "active":
            return True, "rsyslog est actif"
        return False, f"rsyslog status: {status}"

    if check_name == "auditd_active":
        status = security.get("auditd_active", "inactive")
        if status == "active":
            return True, "auditd est actif"
        return False, f"auditd status: {status}"

    if check_name == "antivirus_installed":
        av = security.get("antivirus_edr", "NONE")
        if av and av != "NONE":
            return True, f"Agent de sécurité détecté: {av}"
        return False, "Aucun agent de sécurité (EDR/antivirus) détecté"

    if check_name == "file_permissions_ok":
        perms = security.get("passwd_perms", "")
        # /etc/shadow doit être 640 ou 600
        if "/etc/shadow" in perms:
            for line in perms.splitlines():
                if "shadow" in line:
                    parts = line.split()
                    if parts:
                        mode = parts[0]
                        # Mode attendu: -rw-r----- ou -rw-------
                        if "rw-r-----" in mode or "rw-------" in mode:
                            return True, f"Permissions /etc/shadow : {mode}"
                        return False, f"Permissions /etc/shadow trop permissives : {mode}"
        return False, "Impossible de vérifier les permissions"

    return False, f"Vérification '{check_name}' non implémentée"
