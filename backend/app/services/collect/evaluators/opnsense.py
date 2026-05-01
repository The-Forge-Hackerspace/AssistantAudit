"""Évaluation des contrôles de conformité OPNsense (OPNS-xxx)."""

from ....models.collect_result import CollectResult

OPNSENSE_CONTROL_MAP: list[dict] = [
    # ── Catégorie 1 : Système & Mises à jour ──────────────────
    {
        "control_ref": "OPNS-001",
        "check": "firmware_up_to_date",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le firmware OPNsense est à jour (pas de mise à jour en attente).",
        "evidence_fail": "Des mises à jour OPNsense sont disponibles.",
        "cis_reference": "CIS Controls v8 — 7.3",
    },
    {
        "control_ref": "OPNS-002",
        "check": "no_pkg_vulnerabilities",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Aucune vulnérabilité connue dans les packages installés.",
        "evidence_fail": "Des packages présentent des vulnérabilités connues.",
        "cis_reference": "CIS Controls v8 — 7.4",
    },
    # ── Catégorie 2 : Accès Administration ─────────────────────
    {
        "control_ref": "OPNS-020",
        "check": "ssh_root_disabled",
        "severity": "critical",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "La connexion root via SSH est désactivée (PermitRootLogin no).",
        "evidence_fail": "La connexion root via SSH est autorisée — risque de sécurité.",
        "cis_reference": "CIS FreeBSD 5.2.8",
    },
    {
        "control_ref": "OPNS-021",
        "check": "ssh_password_disabled",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "L'authentification SSH par mot de passe est désactivée.",
        "evidence_fail": "L'authentification SSH par mot de passe est activée.",
        "cis_reference": "CIS FreeBSD 5.2.5",
    },
    {
        "control_ref": "OPNS-025",
        "check": "limited_shell_accounts",
        "severity": "medium",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le nombre de comptes avec shell est limité (≤ 3).",
        "evidence_fail": "Trop de comptes avec un shell interactif (risque de surface d'attaque).",
        "cis_reference": "CIS FreeBSD 6.2.8",
    },
    # ── Catégorie 3 : Filtrage Réseau (pf) ────────────────────
    {
        "control_ref": "OPNS-030",
        "check": "pf_enabled",
        "severity": "critical",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le moteur pf (Packet Filter) est actif.",
        "evidence_fail": "Le moteur pf est désactivé — aucun filtrage en cours.",
        "cis_reference": "CIS Controls v8 — 4.4",
    },
    {
        "control_ref": "OPNS-031",
        "check": "pf_rules_defined",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Des règles de filtrage pf sont définies.",
        "evidence_fail": "Aucune règle de filtrage pf détectée.",
        "cis_reference": "NIST SP 800-41 — 4.1",
    },
    # ── Catégorie 4 : Détection d'intrusion (IDS/IPS) ────────
    {
        "control_ref": "OPNS-040",
        "check": "suricata_active",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Suricata IDS/IPS est actif.",
        "evidence_fail": "Suricata IDS/IPS n'est pas actif — pas de détection d'intrusion.",
        "cis_reference": "CIS Controls v8 — 13.3",
    },
    # ── Catégorie 5 : Journalisation & Audit ──────────────────
    {
        "control_ref": "OPNS-050",
        "check": "syslog_remote_configured",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Un syslog distant est configuré pour la centralisation des logs.",
        "evidence_fail": "Aucun syslog distant configuré — les logs ne sont pas centralisés.",
        "cis_reference": "CIS FreeBSD 4.2.1",
    },
    # ── Catégorie 6 : VPN & Cryptographie ─────────────────────
    {
        "control_ref": "OPNS-060",
        "check": "vpn_configured",
        "severity": "low",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Au moins un tunnel VPN est configuré.",
        "evidence_fail": "Aucun VPN configuré (optionnel selon architecture).",
        "cis_reference": "CIS Controls v8 — 3.10",
    },
    # ── Catégorie 7 : Haute Disponibilité & Sauvegarde ────────
    {
        "control_ref": "OPNS-070",
        "check": "carp_ha_configured",
        "severity": "low",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "La haute disponibilité CARP est configurée.",
        "evidence_fail": "Aucune configuration CARP/HA détectée (optionnel selon architecture).",
        "cis_reference": "CIS Controls v8 — 11.1",
    },
    {
        "control_ref": "OPNS-071",
        "check": "config_backups_exist",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Des sauvegardes de la configuration existent.",
        "evidence_fail": "Aucune sauvegarde de configuration détectée.",
        "cis_reference": "CIS Controls v8 — 11.2",
    },
    # ── Catégorie 2 bis : WebGUI HTTPS (inspiré opnDossier) ──
    {
        "control_ref": "OPNS-010",
        "check": "webgui_https",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "L'interface WebGUI est configurée en HTTPS.",
        "evidence_fail": "L'interface WebGUI n'utilise PAS HTTPS — risque d'interception.",
        "cis_reference": "CIS Controls v8 — 3.10",
    },
    # ── Catégorie 3 bis : Règles any→any (inspiré opnDossier dead-rule detection) ──
    {
        "control_ref": "OPNS-033",
        "check": "no_any_any_rules",
        "severity": "critical",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Aucune règle pass any→any détectée.",
        "evidence_fail": "Des règles pass any→any excessivement permissives sont présentes.",
        "cis_reference": "CIS Controls v8 — 4.5",
    },
    {
        "control_ref": "OPNS-035",
        "check": "rules_documented",
        "severity": "low",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Toutes les règles de filtrage ont une description.",
        "evidence_fail": "Des règles de filtrage n'ont pas de description.",
        "cis_reference": "CIS Controls v8 — 4.1",
    },
    # ── Catégorie 4 bis : Mode IPS (inspiré opnDossier IDS analysis) ──
    {
        "control_ref": "OPNS-042",
        "check": "ids_ips_mode",
        "severity": "medium",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Suricata fonctionne en mode IPS (prévention inline).",
        "evidence_fail": "Suricata fonctionne en mode IDS seul (détection uniquement, pas de blocage).",
        "cis_reference": "CIS Controls v8 — 13.4",
    },
    # ── Catégorie 5 bis : Journalisation firewall + NTP ──
    {
        "control_ref": "OPNS-051",
        "check": "firewall_logging",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "La majorité des règles firewall ont la journalisation activée.",
        "evidence_fail": "Trop peu de règles firewall ont la journalisation activée.",
        "cis_reference": "CIS Controls v8 — 8.2",
    },
    {
        "control_ref": "OPNS-053",
        "check": "ntp_configured",
        "severity": "medium",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "NTP est configuré avec au moins 2 serveurs de temps.",
        "evidence_fail": "NTP n'est pas configuré ou n'a qu'un seul serveur.",
        "cis_reference": "CIS FreeBSD 2.2.1",
    },
    # ── Catégorie 8 : Réseau & Durcissement (inspiré opnDossier) ──
    {
        "control_ref": "OPNS-080",
        "check": "dnssec_enabled",
        "severity": "medium",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "DNSSEC est activé sur le résolveur DNS Unbound.",
        "evidence_fail": "DNSSEC n'est pas activé — pas de validation d'intégrité DNS.",
        "cis_reference": "CIS Controls v8 — 9.2",
    },
    {
        "control_ref": "OPNS-081",
        "check": "no_unused_interfaces",
        "severity": "medium",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Toutes les interfaces actives sont référencées dans les règles firewall.",
        "evidence_fail": "Des interfaces actives ne sont référencées dans aucune règle firewall.",
        "cis_reference": "CIS FreeBSD 3.4",
    },
    {
        "control_ref": "OPNS-082",
        "check": "wan_bogon_blocked",
        "severity": "high",
        "on_pass": "compliant",
        "on_fail": "non_compliant",
        "evidence_pass": "Le blocage des réseaux bogon et privés est activé sur WAN.",
        "evidence_fail": "Le blocage bogon/privé n'est pas activé sur WAN — risque de spoofing.",
        "cis_reference": "NIST SP 800-41 — 4.2.2",
    },
]


def _evaluate_opnsense_check(check_name: str, collect: CollectResult) -> tuple[bool, str]:
    """
    Évalue un contrôle OPNsense à partir des données collectées.
    Returns: (passed: bool, evidence_detail: str)
    """
    security = collect.security or {}
    services = collect.services or {}
    updates = collect.updates or {}
    storage = collect.storage or {}
    users = collect.users or {}

    if check_name == "firmware_up_to_date":
        has_updates = updates.get("updates_available")
        if has_updates is None:
            # Données dynamiques non disponibles (shell menu OPNsense)
            return False, "Vérification impossible (shell menu OPNsense) — vérifier manuellement"
        if not has_updates:
            return True, "OPNsense est à jour (aucune mise à jour en attente)"
        raw = updates.get("update_check_raw", "")
        return False, f"Des mises à jour sont disponibles : {raw[:120]}" if raw else "Des mises à jour sont disponibles"

    if check_name == "no_pkg_vulnerabilities":
        audit = updates.get("pkg_audit", "") or ""
        if "non vérifiable" in audit.lower() or "not_available" in audit.lower():
            return False, "Vérification impossible (shell menu OPNsense) — vérifier manuellement"
        if not audit or "0 problem" in audit.lower() or "is not vulnerable" in audit.lower():
            return True, "Aucune vulnérabilité connue dans les packages"
        vuln_count = sum(1 for line in audit.splitlines() if "is vulnerable" in line.lower())
        return False, f"{vuln_count} package(s) vulnérable(s) détecté(s)"

    if check_name == "pf_enabled":
        enabled = security.get("firewall_enabled", False)
        if enabled:
            return True, "pf (Packet Filter) est actif"
        return False, "pf est désactivé — le pare-feu ne filtre pas le trafic"

    if check_name == "pf_rules_defined":
        count = security.get("firewall_rules_count", 0)
        if isinstance(count, str):
            count = int(count) if count.isdigit() else 0
        if count > 0:
            return True, f"{count} règle(s) de filtrage pf définies"
        return False, "Aucune règle de filtrage pf détectée"

    if check_name == "ssh_root_disabled":
        root_login = security.get("ssh_permit_root_login", "NOT_SET").strip().lower()
        if root_login == "no":
            return True, "PermitRootLogin = no"
        if root_login in ("not_set", ""):
            # FreeBSD default: PermitRootLogin no  → OK par défaut
            ssh_raw = security.get("ssh_config_raw", "")
            if "permitrootlogin" not in ssh_raw.lower():
                return True, "PermitRootLogin non défini (défaut FreeBSD : no)"
            return False, "PermitRootLogin non défini explicitement"
        return False, f"PermitRootLogin = {root_login}"

    if check_name == "ssh_password_disabled":
        ssh_raw = security.get("ssh_config_raw", "")
        for line in ssh_raw.splitlines():
            stripped = line.strip().lower()
            if stripped.startswith("passwordauthentication"):
                val = stripped.split()[-1] if stripped.split() else ""
                if val == "no":
                    return True, "PasswordAuthentication = no"
                return False, f"PasswordAuthentication = {val}"
        # Pas défini → FreeBSD default = yes
        return False, "PasswordAuthentication non défini (défaut : yes)"

    if check_name == "suricata_active":
        status = security.get("suricata_status", "NOT_RUNNING").strip()
        if status and status.upper() not in ("NOT_RUNNING", "NOT_INSTALLED", "", "NONE"):
            return True, f"Suricata IDS/IPS actif : {status[:80]}"
        return False, "Suricata IDS/IPS n'est pas actif"

    if check_name == "syslog_remote_configured":
        syslog = security.get("syslog_remote", "NONE").strip()
        if syslog and syslog.upper() not in ("NONE", ""):
            return True, f"Syslog distant configuré : {syslog[:80]}"
        return False, "Aucun syslog distant configuré"

    if check_name == "carp_ha_configured":
        carp = services.get("carp_status", "").strip()
        if carp and "master" in carp.lower() or "backup" in carp.lower():
            return True, f"CARP HA configuré : {carp[:80]}"
        if carp and carp.upper() not in ("", "NONE", "NOT_CONFIGURED"):
            return True, f"CARP détecté : {carp[:80]}"
        return False, "Aucune configuration CARP/HA détectée"

    if check_name == "vpn_configured":
        ovpn = services.get("openvpn_status", "").strip()
        ipsec = services.get("ipsec_status", "").strip()
        wg = services.get("wireguard_status", "").strip()
        vpns = []
        if ovpn and ovpn.upper() not in ("", "NONE"):
            vpns.append("OpenVPN")
        if ipsec and ipsec.upper() not in ("", "NONE"):
            vpns.append("IPsec")
        if wg and wg.upper() not in ("", "NONE"):
            vpns.append("WireGuard")
        if vpns:
            return True, f"VPN configuré : {', '.join(vpns)}"
        return False, "Aucun VPN configuré"

    if check_name == "config_backups_exist":
        count = storage.get("config_backup_count", "0").strip()
        if isinstance(count, str):
            count = int(count) if count.isdigit() else 0
        if count > 0:
            return True, f"{count} sauvegarde(s) de configuration trouvée(s)"
        return False, "Aucune sauvegarde de configuration détectée"

    if check_name == "limited_shell_accounts":
        users_raw = users.get("users_with_shell", "")
        if isinstance(users_raw, str):
            lines = [l.strip() for l in users_raw.splitlines() if l.strip()]
        elif isinstance(users_raw, list):
            lines = users_raw
        else:
            lines = []
        if len(lines) <= 3:
            return True, f"{len(lines)} compte(s) avec shell interactif"
        return False, f"{len(lines)} comptes avec shell interactif (recommandé : ≤ 3)"

    # ── Nouveaux contrôles inspirés opnDossier ──────────────────

    if check_name == "webgui_https":
        protocol = security.get("webgui_protocol", "https").strip().lower()
        if protocol == "https":
            return True, "WebGUI configuré en HTTPS"
        return False, f"WebGUI configuré en {protocol.upper()} — risque d'interception"

    if check_name == "no_any_any_rules":
        count = security.get("any_any_rules_count", 0)
        rules_list = security.get("any_any_rules", [])
        if count == 0:
            return True, "Aucune règle pass any→any détectée"
        details = "; ".join(rules_list[:3])
        return False, f"{count} règle(s) pass any→any permissive(s) : {details}"

    if check_name == "rules_documented":
        undoc = security.get("rules_without_descr", 0)
        total = security.get("firewall_rules_count", 0)
        if isinstance(total, str):
            total = int(total) if total.isdigit() else 0
        if undoc == 0:
            return True, f"Toutes les {total} règles ont une description"
        return False, f"{undoc}/{total} règle(s) active(s) sans description"

    if check_name == "ids_ips_mode":
        suricata = security.get("suricata_status", "NOT_RUNNING").strip().upper()
        ips_mode = security.get("ids_ips_mode", False)
        if suricata in ("NOT_RUNNING", "NOT_INSTALLED", "", "NONE"):
            return False, "Suricata non actif — mode IPS non applicable"
        if ips_mode:
            return True, "Suricata en mode IPS (prévention inline)"
        return False, "Suricata en mode IDS seulement (détection, pas de blocage)"

    if check_name == "firewall_logging":
        with_log = security.get("rules_with_log", 0)
        total = security.get("firewall_rules_count", 0)
        if isinstance(total, str):
            total = int(total) if total.isdigit() else 0
        if total == 0:
            return False, "Aucune règle firewall pour évaluer le logging"
        ratio = with_log / total if total > 0 else 0
        ratio_str = security.get("rules_log_ratio", f"{with_log}/{total}")
        if ratio >= 0.5:
            return True, f"Logging activé sur {ratio_str} règles ({ratio:.0%})"
        return False, f"Logging activé sur seulement {ratio_str} règles ({ratio:.0%}) — recommandé ≥ 50%"

    if check_name == "ntp_configured":
        ntp_count = security.get("ntp_servers_count", 0)
        ntp_list = security.get("ntp_servers", [])
        if ntp_count >= 2:
            return True, f"{ntp_count} serveurs NTP configurés : {', '.join(ntp_list[:3])}"
        if ntp_count == 1:
            return False, f"1 seul serveur NTP configuré ({ntp_list[0]}) — recommandé ≥ 2"
        return False, "Aucun serveur NTP configuré"

    if check_name == "dnssec_enabled":
        dnssec = security.get("dnssec_enabled", False)
        unbound = security.get("unbound_enabled", False)
        if dnssec:
            return True, "DNSSEC activé sur Unbound DNS"
        if not unbound:
            return False, "Unbound DNS non actif — DNSSEC non applicable"
        return False, "Unbound DNS actif mais DNSSEC désactivé"

    if check_name == "no_unused_interfaces":
        unused = security.get("unused_interfaces", [])
        count = security.get("unused_interfaces_count", 0)
        if count == 0:
            return True, "Toutes les interfaces actives sont référencées dans les règles"
        return False, f"{count} interface(s) active(s) non référencée(s) : {', '.join(unused[:5])}"

    if check_name == "wan_bogon_blocked":
        blockpriv = security.get("wan_blockpriv", False)
        blockbogons = security.get("wan_blockbogons", False)
        parts = []
        if blockpriv:
            parts.append("réseaux privés")
        if blockbogons:
            parts.append("bogons")
        if blockpriv and blockbogons:
            return True, f"WAN bloque les {' et '.join(parts)}"
        missing = []
        if not blockpriv:
            missing.append("réseaux privés (RFC1918)")
        if not blockbogons:
            missing.append("réseaux bogon")
        return False, f"WAN ne bloque pas : {', '.join(missing)}"

    return False, f"Vérification '{check_name}' non implémentée"
