"""
Service Collecte — Orchestration des collectes SSH/WinRM,
analyse des résultats et pré-remplissage des contrôles d'audit.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.collect_result import CollectResult, CollectMethod, CollectStatus
from ..models.equipement import Equipement, EquipementServeur
from ..models.assessment import Assessment, ControlResult, ComplianceStatus
from ..core.database import SessionLocal
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
        raw = security.get("defender_raw", "")
        if active:
            return True, f"Antivirus/EDR actif"
        return False, f"Aucun antivirus/EDR actif détecté"

    return False, f"Vérification '{check_name}' non implémentée"


def _evaluate_linux_check(check_name: str, collect: CollectResult) -> tuple[bool, str]:
    """
    Évalue un contrôle Linux à partir des données collectées.
    Returns: (passed: bool, evidence_detail: str)
    """
    security = collect.security or {}
    users = collect.users or {}
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
            return True, f"PasswordAuthentication = no"
        return False, f"PasswordAuthentication = {ssh_pass}"

    if check_name == "pam_configured":
        pam = security.get("pam_pwquality", "NOT_CONFIGURED")
        if pam and pam != "NOT_CONFIGURED" and "minlen" in pam.lower():
            return True, f"PAM pwquality configuré"
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


# ══════════════════════════════════════════════════════════════
# Analyse des findings
# ══════════════════════════════════════════════════════════════

def _analyze_collect_findings(collect: CollectResult) -> list[dict]:
    """
    Analyse les données collectées et génère des findings de sécurité.
    """
    findings: list[dict] = []
    is_windows = collect.method == CollectMethod.WINRM
    control_map = WINDOWS_CONTROL_MAP if is_windows else LINUX_CONTROL_MAP

    for mapping in control_map:
        check_name = mapping["check"]
        if is_windows:
            passed, detail = _evaluate_windows_check(check_name, collect)
        else:
            passed, detail = _evaluate_linux_check(check_name, collect)

        if not passed:
            findings.append({
                "control_ref": mapping["control_ref"],
                "title": f"Non-conformité détectée : {mapping['control_ref']}",
                "description": detail,
                "severity": "high" if mapping["control_ref"].endswith(("001", "010", "030", "051")) else "medium",
                "category": "Sécurité",
                "remediation": mapping.get("evidence_fail", ""),
                "status": "non_compliant",
            })

    return findings


def _generate_summary(collect: CollectResult, findings: list[dict]) -> dict:
    """Génère un résumé de la collecte."""
    is_windows = collect.method == CollectMethod.WINRM
    os_info = collect.os_info or {}

    total_checks = len(WINDOWS_CONTROL_MAP if is_windows else LINUX_CONTROL_MAP)
    non_compliant = len(findings)
    compliant = total_checks - non_compliant

    return {
        "os_type": "Windows" if is_windows else "Linux",
        "os_name": os_info.get("caption" if is_windows else "distro", "N/A"),
        "os_version": os_info.get("version" if is_windows else "version_id", ""),
        "hostname": collect.hostname_collected or "",
        "total_checks": total_checks,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "compliance_score": round(compliant / total_checks * 100, 1) if total_checks > 0 else 0,
    }


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
    )
    db.add(collect)
    db.commit()
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


def list_collect_results(
    db: Session,
    equipement_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
) -> list[CollectResult]:
    """Liste les collectes, optionnellement filtrées par équipement, avec pagination."""
    q = db.query(CollectResult)
    if equipement_id:
        q = q.filter(CollectResult.equipement_id == equipement_id)
    return q.order_by(CollectResult.created_at.desc()).offset(skip).limit(limit).all()


def get_collect_result(db: Session, collect_id: int) -> Optional[CollectResult]:
    """Récupère une collecte par ID."""
    return db.get(CollectResult, collect_id)


def delete_collect_result(db: Session, collect_id: int) -> bool:
    """Supprime une collecte."""
    collect = db.get(CollectResult, collect_id)
    if not collect:
        return False
    db.delete(collect)
    db.commit()
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

    db.commit()

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
