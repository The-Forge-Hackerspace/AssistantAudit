"""
Collecteur SSH — Connexion à un serveur Linux via SSH (paramiko)
et exécution de commandes d'audit système.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)

# Timeout de connexion SSH (secondes)
SSH_CONNECT_TIMEOUT = 15
SSH_COMMAND_TIMEOUT = 30


@dataclass
class SSHCollectResult:
    """Résultat brut de la collecte SSH."""
    success: bool = False
    error: str | None = None
    hostname: str = ""
    os_info: dict = field(default_factory=dict)
    network: dict = field(default_factory=dict)
    users: dict = field(default_factory=dict)
    services: dict = field(default_factory=dict)
    security: dict = field(default_factory=dict)
    storage: dict = field(default_factory=dict)
    updates: dict = field(default_factory=dict)
    raw_outputs: dict = field(default_factory=dict)


# ── Commandes de collecte Linux ──────────────────────────────
# Chaque commande retourne une sortie texte qu'on parse ensuite.
LINUX_COMMANDS: dict[str, str] = {
    # --- Système ---
    "hostname": "hostname -f 2>/dev/null || hostname",
    "os_release": "cat /etc/os-release 2>/dev/null",
    "kernel": "uname -r",
    "uptime": "uptime -p 2>/dev/null || uptime",
    "arch": "uname -m",

    # --- Mises à jour ---
    # Debian/Ubuntu
    "apt_updates": (
        "apt list --upgradable 2>/dev/null | grep -c upgradable || echo 0"
    ),
    "apt_security": (
        "apt list --upgradable 2>/dev/null | grep -i security | wc -l || echo 0"
    ),
    # RHEL/CentOS
    "yum_updates": "yum check-update --quiet 2>/dev/null | grep -c '\\.' || echo 0",
    "unattended_upgrades": (
        "dpkg -l unattended-upgrades 2>/dev/null | grep -c '^ii' || "
        "systemctl is-enabled dnf-automatic.timer 2>/dev/null || echo 0"
    ),

    # --- Réseau ---
    "ip_addresses": "ip -4 addr show 2>/dev/null || ifconfig 2>/dev/null",
    "routes": "ip route show 2>/dev/null || route -n 2>/dev/null",
    "dns": "cat /etc/resolv.conf 2>/dev/null",
    "listening_ports": "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null",

    # --- Firewall ---
    "ufw_status": "ufw status verbose 2>/dev/null || echo NOT_INSTALLED",
    "iptables_rules": "iptables -L -n --line-numbers 2>/dev/null | head -80 || echo NO_ACCESS",
    "nftables_rules": "nft list ruleset 2>/dev/null | head -80 || echo NOT_INSTALLED",

    # --- SSH ---
    "sshd_config": "cat /etc/ssh/sshd_config 2>/dev/null | grep -v '^#' | grep -v '^$'",
    "ssh_root_login": (
        "grep -i '^PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null || echo 'NOT_SET'"
    ),
    "ssh_password_auth": (
        "grep -i '^PasswordAuthentication' /etc/ssh/sshd_config 2>/dev/null || echo 'NOT_SET'"
    ),

    # --- Utilisateurs ---
    "users_with_shell": (
        "cat /etc/passwd | grep -v '/nologin' | grep -v '/false' | "
        "awk -F: '{print $1\":\"$3\":\"$7}'"
    ),
    "sudoers": "cat /etc/sudoers 2>/dev/null | grep -v '^#' | grep -v '^$' | head -30 || echo NO_ACCESS",
    "last_logins": "last -n 10 2>/dev/null",

    # --- Services ---
    "services_running": "systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -60",
    "services_enabled": "systemctl list-unit-files --type=service --state=enabled --no-pager 2>/dev/null | head -60",

    # --- Journalisation ---
    "rsyslog_active": "systemctl is-active rsyslog 2>/dev/null || echo inactive",
    "journald_config": "cat /etc/systemd/journald.conf 2>/dev/null | grep -v '^#' | grep -v '^$'",
    "auditd_active": "systemctl is-active auditd 2>/dev/null || echo inactive",
    "auditd_rules": "auditctl -l 2>/dev/null | head -30 || echo NO_ACCESS",

    # --- Stockage ---
    "disk_usage": "df -h 2>/dev/null",
    "mount_points": "mount 2>/dev/null | grep -v tmpfs | grep -v cgroup",

    # --- Sécurité ---
    "passwd_perms": "ls -la /etc/passwd /etc/shadow 2>/dev/null",
    "selinux": "getenforce 2>/dev/null || echo NOT_INSTALLED",
    "apparmor": "apparmor_status 2>/dev/null | head -5 || echo NOT_INSTALLED",
    "antivirus": (
        "systemctl is-active clamav-daemon 2>/dev/null && echo clamav || "
        "systemctl is-active falcon-sensor 2>/dev/null && echo crowdstrike || "
        "systemctl is-active mdatp 2>/dev/null && echo defender || "
        "echo NONE"
    ),

    # --- PAM ---
    "pam_pwquality": (
        "cat /etc/security/pwquality.conf 2>/dev/null | grep -v '^#' | grep -v '^$' || echo NOT_CONFIGURED"
    ),
}


def collect_via_ssh(
    host: str,
    port: int = 22,
    username: str = "root",
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
) -> SSHCollectResult:
    """
    Se connecte au serveur Linux via SSH et collecte les informations d'audit.

    Args:
        host: Adresse IP ou hostname du serveur
        port: Port SSH (défaut 22)
        username: Utilisateur SSH
        password: Mot de passe (si pas de clé)
        private_key: Contenu de la clé privée (PEM)
        passphrase: Passphrase de la clé privée

    Returns:
        SSHCollectResult avec toutes les données collectées
    """
    result = SSHCollectResult()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Préparer les paramètres de connexion
        connect_kwargs: dict = {
            "hostname": host,
            "port": port,
            "username": username,
            "timeout": SSH_CONNECT_TIMEOUT,
            "allow_agent": False,
            "look_for_keys": False,
        }

        if private_key:
            import io
            pkey = paramiko.RSAKey.from_private_key(
                io.StringIO(private_key),
                password=passphrase,
            )
            connect_kwargs["pkey"] = pkey
        elif password:
            connect_kwargs["password"] = password
        else:
            # Essayer l'agent SSH ou les clés locales
            connect_kwargs["allow_agent"] = True
            connect_kwargs["look_for_keys"] = True

        logger.info(f"Connexion SSH vers {host}:{port} en tant que {username}...")
        client.connect(**connect_kwargs)
        logger.info(f"Connexion SSH établie vers {host}:{port}")

        # Exécuter toutes les commandes
        raw_outputs: dict[str, str] = {}
        for cmd_name, cmd in LINUX_COMMANDS.items():
            try:
                _, stdout, stderr = client.exec_command(cmd, timeout=SSH_COMMAND_TIMEOUT)
                output = stdout.read().decode("utf-8", errors="replace").strip()
                raw_outputs[cmd_name] = output
            except Exception as e:
                raw_outputs[cmd_name] = f"ERROR: {e}"
                logger.debug(f"Commande '{cmd_name}' échouée: {e}")

        result.raw_outputs = raw_outputs
        result.success = True

        # Parser les résultats
        _parse_ssh_results(result, raw_outputs)

    except paramiko.AuthenticationException:
        result.error = "Échec d'authentification SSH"
        logger.error(f"Auth SSH échouée pour {username}@{host}:{port}")
    except paramiko.SSHException as e:
        result.error = f"Erreur SSH: {e}"
        logger.error(f"Erreur SSH vers {host}:{port}: {e}")
    except TimeoutError:
        result.error = f"Timeout de connexion SSH vers {host}:{port}"
        logger.error(f"Timeout SSH vers {host}:{port}")
    except Exception as e:
        result.error = f"Erreur de connexion: {e}"
        logger.error(f"Erreur collecte SSH {host}:{port}: {e}")
    finally:
        client.close()

    return result


def _parse_ssh_results(result: SSHCollectResult, raw: dict[str, str]) -> None:
    """Parse les sorties brutes des commandes en données structurées."""

    # ── Hostname ──
    result.hostname = raw.get("hostname", "").strip()

    # ── OS Info ──
    os_info: dict = {}
    os_release = raw.get("os_release", "")
    for line in os_release.splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            os_info[key.strip()] = val.strip().strip('"')
    os_info["kernel"] = raw.get("kernel", "")
    os_info["arch"] = raw.get("arch", "")
    os_info["uptime"] = raw.get("uptime", "")

    distro_name = os_info.get("PRETTY_NAME", os_info.get("NAME", "Linux"))
    os_info["distro"] = distro_name
    os_info["version_id"] = os_info.get("VERSION_ID", "")
    result.os_info = os_info

    # ── Réseau ──
    network: dict = {
        "ip_addresses": raw.get("ip_addresses", ""),
        "routes": raw.get("routes", ""),
        "dns": raw.get("dns", ""),
        "listening_ports": raw.get("listening_ports", ""),
    }
    # Extraire les ports en écoute
    ports_list = []
    for line in raw.get("listening_ports", "").splitlines():
        if "LISTEN" in line:
            ports_list.append(line.strip())
    network["listening_ports_parsed"] = ports_list
    result.network = network

    # ── Firewall ──
    fw_status = "unknown"
    ufw = raw.get("ufw_status", "")
    iptables = raw.get("iptables_rules", "")
    nftables = raw.get("nftables_rules", "")

    if "Status: active" in ufw:
        fw_status = "ufw_active"
    elif "NOT_INSTALLED" not in ufw and "inactive" not in ufw.lower():
        fw_status = "ufw_inactive"
    elif "NOT_INSTALLED" not in nftables and nftables.strip():
        fw_status = "nftables_active"
    elif "Chain" in iptables and "NO_ACCESS" not in iptables:
        fw_status = "iptables_active"
    else:
        fw_status = "none_detected"

    security: dict = {
        "firewall_status": fw_status,
        "firewall_details": ufw if "Status:" in ufw else (nftables if nftables.strip() else iptables),
    }

    # ── SSH config ──
    ssh_root = raw.get("ssh_root_login", "NOT_SET").strip()
    ssh_pass = raw.get("ssh_password_auth", "NOT_SET").strip()
    security["ssh_permit_root_login"] = ssh_root
    security["ssh_password_authentication"] = ssh_pass
    security["sshd_config_raw"] = raw.get("sshd_config", "")

    # ── SELinux / AppArmor ──
    security["selinux"] = raw.get("selinux", "NOT_INSTALLED").strip()
    security["apparmor"] = raw.get("apparmor", "NOT_INSTALLED").strip()

    # ── Permissions fichiers sensibles ──
    security["passwd_perms"] = raw.get("passwd_perms", "")

    # ── Antivirus / EDR ──
    av = raw.get("antivirus", "NONE").strip()
    security["antivirus_edr"] = av

    # ── PAM ──
    security["pam_pwquality"] = raw.get("pam_pwquality", "NOT_CONFIGURED")

    result.security = security

    # ── Utilisateurs ──
    users_raw = raw.get("users_with_shell", "")
    users_list = []
    for line in users_raw.splitlines():
        parts = line.split(":")
        if len(parts) >= 3:
            users_list.append({
                "username": parts[0],
                "uid": parts[1],
                "shell": parts[2],
            })
    result.users = {
        "users_with_shell": users_list,
        "sudoers_raw": raw.get("sudoers", ""),
        "last_logins": raw.get("last_logins", ""),
    }

    # ── Services ──
    result.services = {
        "running": raw.get("services_running", ""),
        "enabled": raw.get("services_enabled", ""),
    }

    # ── Journalisation ──
    result.security["rsyslog_active"] = raw.get("rsyslog_active", "inactive").strip()
    result.security["auditd_active"] = raw.get("auditd_active", "inactive").strip()
    result.security["auditd_rules"] = raw.get("auditd_rules", "")
    result.security["journald_config"] = raw.get("journald_config", "")

    # ── Mises à jour ──
    apt_updates = raw.get("apt_updates", "0").strip()
    apt_security = raw.get("apt_security", "0").strip()
    yum_updates = raw.get("yum_updates", "0").strip()
    unattended = raw.get("unattended_upgrades", "0").strip()

    try:
        pending = int(apt_updates) if apt_updates.isdigit() else int(yum_updates) if yum_updates.isdigit() else 0
    except ValueError:
        pending = 0

    try:
        sec_pending = int(apt_security) if apt_security.isdigit() else 0
    except ValueError:
        sec_pending = 0

    result.updates = {
        "pending_updates": pending,
        "security_updates": sec_pending,
        "auto_updates_configured": "1" in unattended or "enabled" in unattended.lower(),
    }

    # ── Stockage ──
    result.storage = {
        "disk_usage": raw.get("disk_usage", ""),
        "mount_points": raw.get("mount_points", ""),
    }
