"""
Service Collecte — Orchestration des collectes SSH/WinRM,
analyse des résultats et pré-remplissage des contrôles d'audit.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.assessment import Assessment, ComplianceStatus, ControlResult
from ..models.collect_result import CollectMethod, CollectResult, CollectStatus
from ..models.equipement import Equipement, EquipementServeur
from ..models.site import Site
from ..tools.collectors.ssh_collector import collect_via_ssh
from ..tools.collectors.winrm_collector import collect_via_winrm

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Mappings findings → contrôles d'audit
# ══════════════════════════════════════════════════════════════

# ── Windows Server (WSRV-xxx) ────────────────────────────────
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

# ── Linux Server (LSRV-xxx) ─────────────────────────────────
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


# ── OPNsense Control Map ─────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════
# Fonctions d'évaluation automatique
# ══════════════════════════════════════════════════════════════

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
        desc = ", ".join(
            f"{p['name']}={'On' if p.get('enabled') else 'Off'}" for p in profiles
        ) if profiles else "N/A"
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
                        return False, f"Distribution: {os_info.get('distro')} {version_id} — potentiellement en fin de vie"
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
        if ovpn and ovpn.upper() not in ("", "NONE"): vpns.append("OpenVPN")
        if ipsec and ipsec.upper() not in ("", "NONE"): vpns.append("IPsec")
        if wg and wg.upper() not in ("", "NONE"): vpns.append("WireGuard")
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


# ══════════════════════════════════════════════════════════════
# Analyse des findings
# ══════════════════════════════════════════════════════════════

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
            findings.append({
                "control_ref": mapping["control_ref"],
                "title": f"Non-conformité détectée : {mapping['control_ref']}",
                "description": detail,
                "severity": mapping.get("severity", "medium"),
                "category": "Sécurité",
                "remediation": mapping.get("evidence_fail", ""),
                "status": "non_compliant",
            })

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
            "firewall_rules_count": security.get("firewall_rules_count",
                                                   security.get("filter_rules_count",
                                                                security.get("policy_count", 0))),
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


# ══════════════════════════════════════════════════════════════
# CRUD + Orchestration
# ══════════════════════════════════════════════════════════════

def create_pending_collect(
    db: Session,
    equipement_id: int,
    method: str,
    target_host: str,
    target_port: int,
    username: str,
    device_profile: str = "linux_server",
) -> CollectResult:
    """Crée un enregistrement de collecte en statut 'running'."""
    equipement = db.get(Equipement, equipement_id)
    if not equipement:
        raise ValueError(f"Équipement {equipement_id} introuvable")

    collect = CollectResult(
        equipement_id=equipement_id,
        method=CollectMethod(method),
        status=CollectStatus.RUNNING,
        target_host=target_host,
        target_port=target_port,
        username=username,
        device_profile=device_profile,
    )
    db.add(collect)
    db.flush()
    db.refresh(collect)
    return collect


def execute_collect_background(
    collect_id: int,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
) -> None:
    """
    Exécute la collecte en arrière-plan (appelé dans un thread).
    Met à jour le CollectResult avec les résultats.
    """
    db = SessionLocal()
    try:
        collect = db.get(CollectResult, collect_id)
        if not collect:
            logger.error(f"CollectResult #{collect_id} introuvable")
            return

        start = time.time()

        if collect.method == CollectMethod.SSH:
            raw_result = collect_via_ssh(
                host=collect.target_host,
                port=collect.target_port,
                username=collect.username,
                password=password,
                private_key=private_key,
                passphrase=passphrase,
                device_profile=collect.device_profile or "linux_server",
            )

            if raw_result.success:
                collect.status = CollectStatus.SUCCESS
                collect.hostname_collected = raw_result.hostname
                collect.os_info = raw_result.os_info
                collect.network = raw_result.network
                collect.users = raw_result.users
                collect.services = raw_result.services
                collect.security = raw_result.security
                collect.storage = raw_result.storage
                collect.updates = raw_result.updates
            else:
                collect.status = CollectStatus.FAILED
                collect.error_message = raw_result.error

        elif collect.method == CollectMethod.WINRM:
            raw_result = collect_via_winrm(
                host=collect.target_host,
                username=collect.username,
                password=password or "",
                port=collect.target_port,
                use_ssl=use_ssl,
                transport=transport,
            )

            if raw_result.success:
                collect.status = CollectStatus.SUCCESS
                collect.hostname_collected = raw_result.hostname
                collect.os_info = raw_result.os_info
                collect.network = raw_result.network
                collect.users = raw_result.users
                collect.services = raw_result.services
                collect.security = raw_result.security
                collect.storage = raw_result.storage
                collect.updates = raw_result.updates
            else:
                collect.status = CollectStatus.FAILED
                collect.error_message = raw_result.error

        # Calculer durée
        elapsed = int(time.time() - start)
        collect.duration_seconds = elapsed
        collect.completed_at = datetime.now(timezone.utc)

        # Si succès, analyser les findings
        if collect.status == CollectStatus.SUCCESS:
            findings = _analyze_collect_findings(collect)
            collect.findings = findings
            collect.summary = _generate_summary(collect, findings)

            # Enrichir l'équipement
            eq = db.get(Equipement, collect.equipement_id)
            if eq:
                if collect.hostname_collected and not eq.hostname:
                    eq.hostname = collect.hostname_collected
                os_info = collect.os_info or {}
                if collect.method == CollectMethod.WINRM:
                    os_name = os_info.get("caption", "")
                else:
                    os_name = os_info.get("distro", "")
                if os_name and not eq.os_detected:
                    eq.os_detected = os_name

                # Mettre à jour les infos spécifiques serveur
                if isinstance(eq, EquipementServeur):
                    if collect.method == CollectMethod.WINRM:
                        detail = f"{os_info.get('caption', '')} Build {os_info.get('build', '')}"
                    else:
                        detail = f"{os_info.get('distro', '')} {os_info.get('version_id', '')} (kernel {os_info.get('kernel', '')})"
                    if not eq.os_version_detail:
                        eq.os_version_detail = detail

        db.commit()
        logger.info(
            f"Collecte #{collect_id} terminée: {collect.status.value} "
            f"en {elapsed}s"
        )

    except Exception as e:
        logger.error(f"Erreur collecte #{collect_id}: {e}", exc_info=True)
        try:
            collect = db.get(CollectResult, collect_id)
            if collect:
                collect.status = CollectStatus.FAILED
                collect.error_message = str(e)
                collect.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _check_equip_access(db: Session, equipement_id: int, user_id: int | None, is_admin: bool) -> bool:
    """Verifie l'acces a un equipement via la chaine Equipement → Site → Entreprise."""
    if user_id is None or is_admin:
        return True
    from ..core.helpers import user_has_access_to_entreprise
    equip = db.get(Equipement, equipement_id)
    if not equip:
        return False
    site = db.get(Site, equip.site_id)
    if not site:
        return False
    return user_has_access_to_entreprise(db, site.entreprise_id, user_id)


def list_collect_results(
    db: Session,
    equipement_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    is_admin: bool = False,
) -> list[CollectResult]:
    """Liste les collectes, optionnellement filtrées par équipement et ownership."""
    q = db.query(CollectResult)
    if equipement_id:
        q = q.filter(CollectResult.equipement_id == equipement_id)
    if user_id is not None and not is_admin:
        from ..models.audit import Audit
        accessible_ent_ids = (
            db.query(Audit.entreprise_id)
            .filter(Audit.owner_id == user_id)
            .distinct()
            .scalar_subquery()
        )
        q = q.join(Equipement, CollectResult.equipement_id == Equipement.id).join(
            Site, Equipement.site_id == Site.id
        ).filter(Site.entreprise_id.in_(accessible_ent_ids))
    return q.order_by(CollectResult.created_at.desc()).offset(skip).limit(limit).all()


def get_collect_result(
    db: Session, collect_id: int,
    user_id: int | None = None, is_admin: bool = False,
) -> Optional[CollectResult]:
    """Récupère une collecte par ID. Vérifie ownership."""
    collect = db.get(CollectResult, collect_id)
    if collect and not _check_equip_access(db, collect.equipement_id, user_id, is_admin):
        return None
    return collect


def delete_collect_result(
    db: Session, collect_id: int,
    user_id: int | None = None, is_admin: bool = False,
) -> bool:
    """Supprime une collecte. Vérifie ownership."""
    collect = db.get(CollectResult, collect_id)
    if not collect:
        return False
    if not _check_equip_access(db, collect.equipement_id, user_id, is_admin):
        return False
    db.delete(collect)
    db.flush()
    return True


def prefill_assessment_from_collect(
    db: Session,
    collect_id: int,
    assessment_id: int,
) -> dict:
    """
    Pré-remplit les contrôles d'un assessment à partir d'une collecte.

    Logique :
    - Pour chaque mapping (check → control_ref), on évalue le check
    - Si passe → compliant
    - Si échoue → non_compliant avec preuve détaillée
    """
    collect = db.get(CollectResult, collect_id)
    if not collect:
        raise ValueError(f"Collecte #{collect_id} introuvable")
    if collect.status != CollectStatus.SUCCESS:
        raise ValueError(f"Collecte #{collect_id} n'est pas en succès (status={collect.status.value})")

    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise ValueError(f"Assessment #{assessment_id} introuvable")

    # Déterminer le jeu de mappings
    is_windows = collect.method == CollectMethod.WINRM
    control_map = WINDOWS_CONTROL_MAP if is_windows else LINUX_CONTROL_MAP

    # Récupérer les control_results de l'assessment
    control_results = (
        db.query(ControlResult)
        .filter(ControlResult.assessment_id == assessment_id)
        .all()
    )
    ref_to_result: dict[str, ControlResult] = {}
    for cr in control_results:
        if cr.control and cr.control.ref_id:
            ref_to_result[cr.control.ref_id] = cr

    prefilled = 0
    compliant_count = 0
    non_compliant_count = 0
    details = []

    for mapping in control_map:
        control_ref = mapping["control_ref"]
        cr = ref_to_result.get(control_ref)
        if not cr:
            continue

        check_name = mapping["check"]
        if is_windows:
            passed, detail = _evaluate_windows_check(check_name, collect)
        else:
            passed, detail = _evaluate_linux_check(check_name, collect)

        source = "WinRM" if is_windows else "SSH"

        if passed:
            cr.status = ComplianceStatus.COMPLIANT
            cr.evidence = f"[Collecte {source}] {mapping['evidence_pass']}\n\nDétail : {detail}"
            cr.auto_result = f"Collecte {source}: conforme"
            compliant_count += 1
            status_label = "compliant"
        else:
            cr.status = ComplianceStatus.NON_COMPLIANT
            cr.evidence = f"[Collecte {source}] {mapping['evidence_fail']}\n\nDétail : {detail}"
            cr.auto_result = f"Collecte {source}: non conforme"
            non_compliant_count += 1
            status_label = "non_compliant"

        cr.is_auto_assessed = True
        cr.assessed_at = datetime.now(timezone.utc)
        cr.assessed_by = f"collect_{source.lower()}"
        prefilled += 1

        details.append({
            "control_ref": control_ref,
            "control_title": cr.control.title if cr.control else "",
            "status": status_label,
            "findings_count": 0 if passed else 1,
        })

    db.flush()
    logger.info(
        f"Pré-remplissage collecte #{collect_id}: {prefilled} contrôles "
        f"({compliant_count} conformes, {non_compliant_count} non-conformes)"
    )

    return {
        "controls_prefilled": prefilled,
        "controls_compliant": compliant_count,
        "controls_non_compliant": non_compliant_count,
        "controls_partial": 0,
        "details": details,
    }
