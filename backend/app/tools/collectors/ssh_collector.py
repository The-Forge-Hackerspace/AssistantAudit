"""
Collecteur SSH — Connexion à un serveur Linux ou pare-feu via SSH (paramiko)
et exécution de commandes d'audit système adaptées au profil d'équipement.

Profils supportés :
- linux_server : Serveur Linux (Debian, Ubuntu, RHEL, CentOS…)
- opnsense     : Pare-feu OPNsense (FreeBSD)  – collecte via SFTP config.xml
- stormshield  : Pare-feu Stormshield (SNS)
- fortigate    : Pare-feu FortiGate (FortiOS)
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import defusedxml.ElementTree as ET
import paramiko

logger = logging.getLogger(__name__)

# Timeout de connexion SSH (secondes)
SSH_CONNECT_TIMEOUT = 15
SSH_COMMAND_TIMEOUT = 30

# Profils supportés
SUPPORTED_PROFILES = ("linux_server", "opnsense", "stormshield", "fortigate")


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


# ── Commandes OPNsense (FreeBSD + configd) ──────────────────
OPNSENSE_COMMANDS: dict[str, str] = {
    # --- Système ---
    "hostname": "hostname",
    "os_version": "opnsense-version -v 2>/dev/null || freebsd-version",
    "os_name": "opnsense-version -n 2>/dev/null || echo OPNsense",
    "kernel": "uname -r",
    "uptime": "uptime",
    "arch": "uname -m",

    # --- Mises à jour ---
    "updates_pending": "opnsense-update -c 2>/dev/null; echo EXIT=$?",
    "pkg_audit": "pkg audit -F 2>/dev/null | tail -5 || echo NOT_AVAILABLE",
    "installed_version": "opnsense-version 2>/dev/null",

    # --- Réseau ---
    "interfaces": "ifconfig -a 2>/dev/null | head -100",
    "routes": "netstat -rn 2>/dev/null | head -40",
    "dns": "cat /etc/resolv.conf 2>/dev/null",
    "listening_ports": "sockstat -4 -l 2>/dev/null | head -60",

    # --- Firewall (pf) ---
    "pf_status": "/sbin/pfctl -s info 2>/dev/null || pfctl -s info 2>/dev/null || echo PF_DISABLED",
    "pf_rules_count": "/sbin/pfctl -s rules 2>/dev/null | wc -l | tr -d ' ' || echo 0",
    "pf_rules": "/sbin/pfctl -s rules 2>/dev/null | head -80",
    "pf_nat": "/sbin/pfctl -s nat 2>/dev/null | head -40",
    "pf_states_count": "/sbin/pfctl -s info 2>/dev/null | grep -i 'current entries' || echo N/A",

    # --- Configuration ---
    "config_xml_size": "ls -la /conf/config.xml 2>/dev/null",
    "config_backup_count": "ls /conf/backup/ 2>/dev/null | wc -l | tr -d ' ' || echo 0",
    "aliases": "/sbin/pfctl -t -s Tables 2>/dev/null | head -30 || echo NONE",

    # --- Services ---
    "services": "configctl service list 2>/dev/null || service -e 2>/dev/null",

    # --- VPN ---
    "openvpn_status": "configctl openvpn status 2>/dev/null || sockstat -4 | grep openvpn || echo NOT_RUNNING",
    "ipsec_status": "ipsec statusall 2>/dev/null | head -30 || echo NOT_CONFIGURED",
    "wireguard_status": "wg show 2>/dev/null || echo NOT_INSTALLED",

    # --- Sécurité ---
    "ssh_config": "cat /etc/ssh/sshd_config 2>/dev/null | grep -v '^#' | grep -v '^$'",
    "ssh_root_login": "grep -i '^PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null || echo 'NOT_SET'",
    "users": "cat /etc/passwd 2>/dev/null | grep -v nologin | grep -v '/usr/sbin/nologin'",

    # --- Logs ---
    "clog_filter": "clog /var/log/filter.log 2>/dev/null | tail -20 || echo NO_ACCESS",
    "syslog_remote": "grep -i '@' /usr/local/etc/syslog.conf 2>/dev/null || echo NONE",

    # --- IDS/IPS (Suricata) ---
    "suricata_status": "configctl ids status 2>/dev/null || pgrep suricata > /dev/null && echo RUNNING || echo NOT_RUNNING",

    # --- HA / CARP ---
    "carp_status": "ifconfig | grep -A1 carp 2>/dev/null || echo NO_CARP",
}


# ── Commandes Stormshield (SNS) ─────────────────────────────
# Stormshield utilise des commandes CLI propriétaires (namespace-based)
STORMSHIELD_COMMANDS: dict[str, str] = {
    # --- Système ---
    "system_info": "VERSION",
    "hostname": "CONFIG SYSTEM PROPERTY index=Name",
    "serial": "CONFIG SYSTEM PROPERTY index=SerialNumber",
    "uptime": "SYSTEM UPTIME",
    "license": "CONFIG LICENSE LIST",

    # --- Réseau ---
    "interfaces": "CONFIG NETWORK INTERFACE LIST",
    "routes": "CONFIG NETWORK ROUTE LIST",
    "dns": "CONFIG NETWORK DNS LIST",

    # --- Firewall ---
    "filter_rules_count": "CONFIG FILTER COUNT",
    "filter_rules": "CONFIG FILTER SHOW",
    "nat_rules": "CONFIG NAT SHOW",
    "active_connections": "CONFIG FILTER CONNTRACK list state=established",

    # --- Objets ---
    "objects_host": "CONFIG OBJECT HOST LIST",
    "objects_network": "CONFIG OBJECT NETWORK LIST",
    "objects_group": "CONFIG OBJECT GROUP LIST",

    # --- VPN ---
    "vpn_ipsec_peers": "CONFIG IPSEC PEER LIST",
    "vpn_ipsec_sa": "PKI IPSEC SA LIST",
    "vpn_ssl_status": "CONFIG OPENVPN LIST",

    # --- Sécurité ---
    "admin_accounts": "CONFIG AUTH LOCAL USER LIST",
    "ssh_status": "CONFIG SSH SHOW",
    "antivirus": "CONFIG ANTIVIRUS SHOW",
    "ips_status": "CONFIG ASQ SHOW",

    # --- Logs ---
    "syslog_servers": "CONFIG SYSLOG LIST",
    "alarm_list": "CONFIG ALARM LIST filter=on",

    # --- HA ---
    "ha_status": "HA STATUS",

    # --- Services ---
    "services_status": "SYSTEM SERVICE LIST",

    # --- MàJ ---
    "firmware_version": "VERSION",
    "update_status": "SYSTEM UPDATE STATUS",
}


# ── Commandes FortiGate (FortiOS CLI) ───────────────────────
FORTIGATE_COMMANDS: dict[str, str] = {
    # --- Système ---
    "system_status": "get system status",
    "hostname": "get system global | grep hostname",
    "serial": "get system status | grep Serial",
    "uptime": "get system performance status | grep Uptime",
    "firmware": "get system status | grep Version",
    "license": "get system fortiguard-service status",

    # --- Réseau ---
    "interfaces": "get system interface | grep -A5 '== \\['",
    "interfaces_physical": "diagnose hardware deviceinfo nic",
    "routes": "get router info routing-table all",
    "dns": "get system dns",
    "arp_table": "get system arp | head -40",

    # --- Firewall ---
    "policy_count": "get firewall policy | grep -c 'edit'",
    "policies": "show firewall policy | head -200",
    "policy_summary": "diagnose firewall iprope list 100004 | head -60",
    "vip": "get firewall vip | head -40",
    "address_objects": "get firewall address | head -60",
    "address_groups": "get firewall addrgrp | head -40",

    # --- VPN ---
    "vpn_ipsec_tunnels": "get vpn ipsec tunnel summary",
    "vpn_ssl_status": "get vpn ssl monitor",
    "vpn_ssl_settings": "get vpn ssl settings | head -30",

    # --- Sécurité ---
    "admin_users": "get system admin | grep 'edit\\|accprofile'",
    "admin_settings": "get system global | grep admin",
    "password_policy": "get system password-policy",
    "trusted_hosts": "show system admin | grep trustedhost",
    "antivirus_profile": "get antivirus profile | head -30",
    "ips_settings": "get ips global",
    "webfilter": "get webfilter profile | head -20",

    # --- Logs ---
    "log_settings": "get log setting",
    "log_syslogd": "get log syslogd setting",
    "log_fortianalyzer": "get log fortianalyzer setting",
    "log_disk": "get log disk setting",

    # --- HA ---
    "ha_status": "get system ha status",

    # --- NTP ---
    "ntp": "get system ntp | head -20",

    # --- SNMP ---
    "snmp": "get system snmp sysinfo",

    # --- Sessions ---
    "session_count": "diagnose sys session stat",
}


# Map profile → command set
PROFILE_COMMANDS: dict[str, dict[str, str]] = {
    "linux_server": LINUX_COMMANDS,
    "opnsense": OPNSENSE_COMMANDS,
    "stormshield": STORMSHIELD_COMMANDS,
    "fortigate": FORTIGATE_COMMANDS,
}


def collect_via_ssh(
    host: str,
    port: int = 22,
    username: str = "root",
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    device_profile: str = "linux_server",
) -> SSHCollectResult:
    """
    Se connecte au serveur/pare-feu via SSH et collecte les informations d'audit.

    Args:
        host: Adresse IP ou hostname
        port: Port SSH (défaut 22)
        username: Utilisateur SSH
        password: Mot de passe (si pas de clé)
        private_key: Contenu de la clé privée (PEM)
        passphrase: Passphrase de la clé privée
        device_profile: Profil de collecte (linux_server, opnsense, stormshield, fortigate)

    Returns:
        SSHCollectResult avec toutes les données collectées
    """
    result = SSHCollectResult()
    client = paramiko.SSHClient()

    # Sélectionner les commandes selon le profil
    commands = PROFILE_COMMANDS.get(device_profile, LINUX_COMMANDS)
    logger.info(f"Profil de collecte: {device_profile} ({len(commands)} commandes)")

    # Sécurité : charger les host keys connues du système.
    try:
        client.load_system_host_keys()
    except Exception:
        pass

    client.set_missing_host_key_policy(paramiko.WarningPolicy())

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

        if device_profile == "opnsense":
            # ── OPNsense : SFTP config.xml + shell interactif ────
            # Le shell menu OPNsense bloque exec_command().
            # Stratégie : SFTP pour config.xml, shell interactif en bonus.
            logger.info("OPNsense: collecte via SFTP /conf/config.xml")
            config_data = _collect_opnsense_via_sftp(client)

            if "error" not in config_data:
                # Config.xml OK → essayer les commandes dynamiques en bonus
                logger.info("OPNsense: tentative de commandes dynamiques via shell interactif")
                dynamic_data = _try_opnsense_dynamic_commands(client)
                _build_opnsense_from_config(result, config_data, dynamic_data)
                result.success = True
                logger.info(
                    f"OPNsense collecte OK: hostname={result.hostname}, "
                    f"rules={result.security.get('firewall_rules_count', 0)}, "
                    f"dynamic_cmds={len(dynamic_data)}"
                )
            else:
                # SFTP échoué → fallback exec_command classique
                logger.warning(
                    f"OPNsense SFTP échoué ({config_data.get('error')}), "
                    "fallback sur exec_command..."
                )
                raw_outputs: dict[str, str] = {}
                for cmd_name, cmd in commands.items():
                    try:
                        _, stdout, stderr = client.exec_command(
                            cmd, timeout=SSH_COMMAND_TIMEOUT
                        )
                        output = stdout.read().decode("utf-8", errors="replace").strip()
                        raw_outputs[cmd_name] = output
                    except Exception as e:
                        raw_outputs[cmd_name] = f"ERROR: {e}"
                        logger.debug(f"Commande '{cmd_name}' échouée: {e}")
                result.raw_outputs = raw_outputs
                result.success = True
                _parse_opnsense_results(result, raw_outputs)
        else:
            # ── Autres profils : exec_command classique ──────────
            raw_outputs: dict[str, str] = {}
            for cmd_name, cmd in commands.items():
                try:
                    _, stdout, stderr = client.exec_command(
                        cmd, timeout=SSH_COMMAND_TIMEOUT
                    )
                    output = stdout.read().decode("utf-8", errors="replace").strip()
                    raw_outputs[cmd_name] = output
                except Exception as e:
                    raw_outputs[cmd_name] = f"ERROR: {e}"
                    logger.debug(f"Commande '{cmd_name}' échouée: {e}")

            result.raw_outputs = raw_outputs
            result.success = True

            # Parser les résultats selon le profil
            if device_profile == "linux_server":
                _parse_ssh_results(result, raw_outputs)
            elif device_profile == "stormshield":
                _parse_stormshield_results(result, raw_outputs)
            elif device_profile == "fortigate":
                _parse_fortigate_results(result, raw_outputs)
            else:
                _parse_ssh_results(result, raw_outputs)  # fallback

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
        import traceback
        result.error = f"Erreur de connexion: {e}"
        logger.error(f"Erreur collecte SSH {host}:{port}: {e}")
        logger.error(traceback.format_exc())
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


# ══════════════════════════════════════════════════════════════
# Parsers pare-feu
# ══════════════════════════════════════════════════════════════


# ── OPNsense : collecte via SFTP config.xml ──────────────────
# Le shell menu OPNsense (/usr/local/sbin/opnsense-shell, script PHP)
# ne supporte pas -c, donc exec_command() échoue systématiquement.
# La méthode fiable : SFTP pour télécharger /conf/config.xml et le parser.


def _collect_opnsense_via_sftp(client: paramiko.SSHClient) -> dict:
    """
    Télécharge /conf/config.xml via SFTP et parse le XML pour extraire
    toutes les données d'audit (hostname, firewall, SSH, IDS, VPN, etc.).

    Retourne un dict de données structurées, ou {"error": "..."} en cas d'échec.
    """
    data: dict = {"source": "sftp_config_xml"}

    try:
        sftp = client.open_sftp()
        try:
            # ── Télécharger config.xml ──
            with sftp.open("/conf/config.xml", "r") as f:
                content = f.read().decode("utf-8", errors="replace")

            root = ET.fromstring(content)

            # ── Hostname ──
            hostname = (root.findtext(".//system/hostname") or "").strip()
            domain = (root.findtext(".//system/domain") or "").strip()
            data["hostname"] = f"{hostname}.{domain}" if domain else hostname

            # ── SSH settings ──
            ssh_el = root.find(".//system/ssh")
            if ssh_el is not None:
                permit_root = (root.findtext(".//system/ssh/permitrootlogin") or "").strip()
                passwd_auth = (root.findtext(".//system/ssh/passwordauth") or "").strip()
                ssh_enabled = (root.findtext(".//system/ssh/enabled") or "").strip()

                data["ssh_enabled"] = ssh_enabled == "enabled"
                data["ssh_permit_root_login"] = "yes" if permit_root == "1" else "no"
                data["ssh_password_auth"] = "yes" if passwd_auth == "1" else "no"

                # Construire un pseudo sshd_config pour la compatibilité évaluateur
                data["ssh_config_raw"] = (
                    f"PermitRootLogin {'yes' if permit_root == '1' else 'no'}\n"
                    f"PasswordAuthentication {'yes' if passwd_auth == '1' else 'no'}"
                )
            else:
                data["ssh_permit_root_login"] = "NOT_SET"
                data["ssh_password_auth"] = "NOT_SET"
                data["ssh_config_raw"] = ""

            # ── Firewall rules (pf) ──
            filter_node = root.find(".//filter")
            total_rules = 0
            enabled_rules = 0
            rules_text_lines: list[str] = []

            if filter_node is not None:
                for idx, rule_el in enumerate(filter_node.findall("rule"), 1):
                    total_rules += 1
                    disabled = rule_el.find("disabled") is not None
                    if not disabled:
                        enabled_rules += 1

                    rule_type = (rule_el.findtext("type") or "pass").strip()
                    interface = (rule_el.findtext("interface") or "").strip()
                    descr = (rule_el.findtext("descr") or "").strip()
                    protocol = (rule_el.findtext("protocol") or "any").strip()

                    src = "any" if rule_el.find("source/any") is not None else (
                        (rule_el.findtext("source/network") or "").strip()
                        or (rule_el.findtext("source/address") or "").strip()
                        or "?"
                    )
                    dst = "any" if rule_el.find("destination/any") is not None else (
                        (rule_el.findtext("destination/network") or "").strip()
                        or (rule_el.findtext("destination/address") or "").strip()
                        or "?"
                    )
                    dst_port = (rule_el.findtext("destination/port") or "").strip()
                    status = "disabled" if disabled else "enabled"
                    log_flag = "log" if rule_el.find("log") is not None else ""

                    service = f"{protocol}/{dst_port}" if dst_port else protocol
                    rules_text_lines.append(
                        f"#{idx} [{status}] {rule_type} {interface}: "
                        f"{src} → {dst} {service} {log_flag} {descr}"
                    )

            data["firewall_rules_count"] = enabled_rules
            data["firewall_rules_total"] = total_rules
            data["firewall_rules_text"] = "\n".join(rules_text_lines)
            # OPNsense pf est toujours actif quand le système tourne
            data["firewall_enabled"] = True

            # ── NAT ──
            nat_rules = root.findall(".//nat/rule")
            data["nat_rules_count"] = len(nat_rules)

            # ── Suricata / IDS ──
            ids_enabled = (root.findtext(".//OPNsense/IDS/general/enabled") or "0").strip()
            data["suricata_status"] = "RUNNING" if ids_enabled == "1" else "NOT_RUNNING"

            # ── Syslog remote ──
            remote_hosts: list[str] = []
            for dest in root.findall(".//syslog/destinations/destination"):
                transport = (dest.findtext("transport") or "").strip()
                h = (dest.findtext("hostname") or "").strip()
                port = (dest.findtext("port") or "").strip()
                if h:
                    remote_hosts.append(f"{transport}://{h}:{port}" if port else h)
            # Format legacy
            if not remote_hosts:
                for srv in root.findall(".//syslog/remoteserver"):
                    if srv.text and srv.text.strip():
                        remote_hosts.append(srv.text.strip())
                for srv in root.findall(".//syslog/remoteserver2"):
                    if srv.text and srv.text.strip():
                        remote_hosts.append(srv.text.strip())
                for srv in root.findall(".//syslog/remoteserver3"):
                    if srv.text and srv.text.strip():
                        remote_hosts.append(srv.text.strip())
            data["syslog_remote"] = ", ".join(remote_hosts) if remote_hosts else "NONE"

            # ── VPN ──
            openvpn_srv = root.findall(".//openvpn/openvpn-server")
            openvpn_cli = root.findall(".//openvpn/openvpn-client")
            if openvpn_srv or openvpn_cli:
                data["openvpn_status"] = (
                    f"{len(openvpn_srv)} serveur(s), {len(openvpn_cli)} client(s) OpenVPN"
                )
            else:
                data["openvpn_status"] = ""

            ipsec_ph1 = root.findall(".//ipsec/phase1")
            if ipsec_ph1:
                data["ipsec_status"] = f"{len(ipsec_ph1)} tunnel(s) IPsec configuré(s)"
            else:
                data["ipsec_status"] = ""

            wg_peers = root.findall(".//OPNsense/wireguard/server/servers/server")
            wg_enabled = (root.findtext(".//OPNsense/wireguard/general/enabled") or "0").strip()
            if wg_peers or wg_enabled == "1":
                data["wireguard_status"] = f"{len(wg_peers)} peer(s) WireGuard"
            else:
                data["wireguard_status"] = ""

            # ── CARP / HA ──
            carp_entries: list[str] = []
            for vip in root.findall(".//virtualip/vip"):
                mode = (vip.findtext("mode") or "").strip()
                subnet = (vip.findtext("subnet") or "").strip()
                iface = (vip.findtext("interface") or "").strip()
                descr_vip = (vip.findtext("descr") or "").strip()
                if mode == "carp":
                    carp_entries.append(f"CARP {subnet} on {iface} ({descr_vip})")

            ha_parts: list[str] = []
            hasync = root.find(".//hasync")
            if hasync is not None:
                sync_enabled = (hasync.findtext("pfsyncenabled") or "").strip()
                sync_peer = (hasync.findtext("pfsyncpeerip") or "").strip()
                if sync_enabled:
                    ha_parts.append(f"pfsync → {sync_peer}")

            if carp_entries or ha_parts:
                data["carp_status"] = "; ".join(carp_entries + ha_parts)
            else:
                data["carp_status"] = ""

            # ── Utilisateurs ──
            user_lines: list[str] = []
            for u in root.findall(".//system/user"):
                name = (u.findtext("name") or "").strip()
                shell = (u.findtext("shell") or "").strip()
                uid = (u.findtext("uid") or "").strip()
                if name:
                    user_lines.append(
                        f"{name}:{uid}:{shell or '/usr/local/sbin/opnsense-shell'}"
                    )
            data["users"] = "\n".join(user_lines)

            # ── WebGUI ──
            data["webgui_protocol"] = (
                root.findtext(".//system/webgui/protocol") or "https"
            ).strip()

            # ── DNS ──
            dns_servers = [
                el.text.strip()
                for el in root.findall(".//system/dnsserver")
                if el.text
            ]
            data["dns_servers"] = ", ".join(dns_servers) if dns_servers else ""

            # ── Interfaces ──
            iface_lines: list[str] = []
            iface_node = root.find(".//interfaces")
            if iface_node is not None:
                logger.debug(
                    f"OPNsense interfaces node found, children: "
                    f"{[c.tag for c in iface_node]}"
                )
                for child in iface_node:
                    tag = child.tag
                    # Ignorer les éléments non-interface
                    if tag in ("count", "bridged"):
                        continue
                    descr = (child.findtext("descr") or tag).strip()
                    # Détecter enable : <enable/> ou <enable>1</enable> ou absent
                    enable_el = child.find("enable")
                    if enable_el is not None:
                        status = "up"
                    else:
                        # Certains OPNsense active par défaut (WAN, LAN)
                        status = "down"
                    ipaddr = (child.findtext("ipaddr") or "").strip()
                    subnet = (child.findtext("subnet") or "").strip()
                    if_dev = (child.findtext("if") or "").strip()
                    ip_str = f"{ipaddr}/{subnet}" if ipaddr and subnet else ipaddr or "N/A"
                    iface_lines.append(f"{descr} ({if_dev}): {ip_str} [{status}]")
            else:
                logger.warning("OPNsense: <interfaces> node not found in config.xml")
            data["interfaces_text"] = "\n".join(iface_lines)
            data["interfaces_count"] = len(iface_lines)

            # ── Sauvegardes config (via SFTP) ──
            try:
                backup_files = sftp.listdir("/conf/backup/")
                data["config_backup_count"] = str(len(backup_files))
            except Exception:
                data["config_backup_count"] = "0"

            # ── Taille config.xml ──
            try:
                stat = sftp.stat("/conf/config.xml")
                data["config_xml_size"] = f"{stat.st_size} bytes"
            except Exception:
                data["config_xml_size"] = ""

            # ── Firmware (dans config.xml si présent) ──
            data["firmware_version"] = (
                root.findtext(".//system/firmware/version")
                or root.findtext(".//version")
                or ""
            ).strip()

            # ── Unbound DNS / DNSSEC (inspiré opnDossier) ──
            unbound_enabled = (
                root.findtext(".//OPNsense/unboundplus/general/enabled")
                or root.findtext(".//unbound/enable")
                or "0"
            ).strip()
            dnssec_enabled = (
                root.findtext(".//OPNsense/unboundplus/general/dnssec")
                or root.findtext(".//unbound/dnssec")
                or "0"
            ).strip()
            data["unbound_enabled"] = unbound_enabled == "1"
            data["dnssec_enabled"] = dnssec_enabled == "1"

            # ── WAN bogon/private blocking (inspiré opnDossier) ──
            wan_node = root.find(".//interfaces/wan")
            if wan_node is not None:
                data["wan_blockpriv"] = wan_node.find("blockpriv") is not None
                data["wan_blockbogons"] = wan_node.find("blockbogons") is not None
            else:
                data["wan_blockpriv"] = False
                data["wan_blockbogons"] = False

            # ── IDS mode IPS (inspiré opnDossier) ──
            ids_ips_mode = (
                root.findtext(".//OPNsense/IDS/general/ips") or "0"
            ).strip()
            data["ids_ips_mode"] = ids_ips_mode == "1"

            # ── Analyse avancée des règles firewall (inspiré opnDossier) ──
            any_any_rules: list[str] = []
            rules_without_descr = 0
            rules_with_log = 0
            # Collecter les interfaces référencées dans les règles
            interfaces_in_rules: set[str] = set()

            if filter_node is not None:
                for idx, rule_el in enumerate(filter_node.findall("rule"), 1):
                    disabled = rule_el.find("disabled") is not None
                    if disabled:
                        continue
                    rule_type = (rule_el.findtext("type") or "pass").strip()
                    descr = (rule_el.findtext("descr") or "").strip()
                    iface = (rule_el.findtext("interface") or "").strip()
                    src_any = rule_el.find("source/any") is not None
                    dst_any = rule_el.find("destination/any") is not None
                    has_log = rule_el.find("log") is not None

                    if iface:
                        for if_part in iface.split(","):
                            interfaces_in_rules.add(if_part.strip())

                    if not descr:
                        rules_without_descr += 1
                    if has_log:
                        rules_with_log += 1
                    # Détecter any→any pass (overly permissive) — opnDossier security check
                    if rule_type == "pass" and src_any and dst_any:
                        any_any_rules.append(
                            f"#{idx} {iface}: pass any→any {descr or '(sans description)'}"
                        )

            data["any_any_rules"] = any_any_rules
            data["any_any_rules_count"] = len(any_any_rules)
            data["rules_without_descr"] = rules_without_descr
            data["rules_with_log"] = rules_with_log
            data["rules_log_ratio"] = (
                f"{rules_with_log}/{enabled_rules}"
                if enabled_rules > 0 else "0/0"
            )

            # ── Interfaces inutilisées (inspiré opnDossier) ──
            configured_interfaces: list[str] = []
            if iface_node is not None:
                for child in iface_node:
                    tag = child.tag
                    if tag in ("count", "bridged"):
                        continue
                    enable_el = child.find("enable")
                    if enable_el is not None:
                        configured_interfaces.append(tag)
            unused_interfaces = [
                iface for iface in configured_interfaces
                if iface not in interfaces_in_rules
            ]
            data["unused_interfaces"] = unused_interfaces
            data["unused_interfaces_count"] = len(unused_interfaces)

            # ── NTP (inspiré opnDossier) ──
            ntp_servers: list[str] = []
            # Format OPNsense: <timeservers>0.opnsense.pool.ntp.org 1.opnsense.pool.ntp.org</timeservers>
            ts_raw = (root.findtext(".//system/timeservers") or "").strip()
            if ts_raw:
                ntp_servers = [s.strip() for s in ts_raw.split() if s.strip()]
            data["ntp_servers"] = ntp_servers
            data["ntp_servers_count"] = len(ntp_servers)

            # ── SNMP (inspiré opnDossier) ──
            snmp_community = (
                root.findtext(".//system/snmpd/rocommunity") or ""
            ).strip()
            data["snmp_community"] = snmp_community
            data["snmp_default_community"] = snmp_community.lower() in (
                "public", "private", ""
            ) if snmp_community else False

            logger.info(
                f"OPNsense config.xml parsed: hostname={data.get('hostname')}, "
                f"rules={enabled_rules}/{total_rules}, "
                f"interfaces={len(iface_lines)}, "
                f"any_any={len(any_any_rules)}, "
                f"dnssec={data['dnssec_enabled']}, "
                f"source=SFTP"
            )

        finally:
            sftp.close()

    except Exception as e:
        logger.error(f"Erreur SFTP/XML OPNsense: {e}")
        data["error"] = str(e)

    return data


def _try_opnsense_dynamic_commands(client: paramiko.SSHClient) -> dict:
    """
    Tente d'exécuter des commandes dynamiques sur OPNsense via
    shell interactif (option 8 du menu).

    Ces données ne sont PAS dans config.xml : version runtime, uptime,
    mises à jour en attente, vulnérabilités packages, statut pf runtime.

    Toutes les commandes sont envoyées en UN seul script batch
    pour minimiser le temps total (~12s au lieu de 63s).
    """
    dynamic: dict[str, str] = {}

    # Commandes à exécuter, avec marqueurs intégrés dans un script batch
    DYNAMIC_CMDS = [
        ("os_version", "opnsense-version -v 2>/dev/null || freebsd-version"),
        ("os_name", "opnsense-version -n 2>/dev/null || echo OPNsense"),
        ("installed_version", "opnsense-version 2>/dev/null || echo N/A"),
        ("kernel", "uname -r"),
        ("uptime", "uptime"),
        ("arch", "uname -m"),
        ("updates_pending", "opnsense-update -c 2>/dev/null; echo EXIT=$?"),
        ("pkg_audit", "pkg audit -F 2>/dev/null | tail -5 || echo NOT_AVAILABLE"),
        ("pf_status", "/sbin/pfctl -s info 2>/dev/null | head -5"),
    ]

    try:
        channel = client.invoke_shell(width=200, height=50)
        channel.settimeout(12)
        time.sleep(1.0)

        # Lire le menu initial
        buf = b""
        while channel.recv_ready():
            buf += channel.recv(8192)
        menu_text = buf.decode("utf-8", errors="replace")
        logger.debug(f"OPNsense menu: {menu_text[:200]}")

        # Envoyer option 8 (Shell)
        channel.send("8\n")
        time.sleep(1.0)

        buf = b""
        while channel.recv_ready():
            buf += channel.recv(8192)
        shell_prompt = buf.decode("utf-8", errors="replace")
        logger.debug(f"OPNsense shell: {shell_prompt[:200]}")

        # Vérifier qu'on est bien dans un shell
        if "#" not in shell_prompt and "$" not in shell_prompt and "root@" not in shell_prompt:
            logger.warning("OPNsense: shell interactif non détecté → abandon commandes dynamiques")
            channel.close()
            return dynamic

        # ── Construire UN script batch avec tous les marqueurs ──
        batch_lines: list[str] = []
        for cmd_name, cmd in DYNAMIC_CMDS:
            batch_lines.append(f"echo __MRK_{cmd_name}_S__")
            batch_lines.append(cmd)
            batch_lines.append(f"echo __MRK_{cmd_name}_E__")
        batch_lines.append("echo __ALL_DONE__")
        batch_script = " ; ".join(batch_lines) + "\n"

        channel.send(batch_script)

        # ── Attendre la fin du script (max 12s) ──
        buf = b""
        deadline = time.time() + 12
        while time.time() < deadline:
            if channel.recv_ready():
                chunk = channel.recv(16384)
                buf += chunk
                # Vérifier si le script est terminé
                if b"__ALL_DONE__" in buf:
                    break
            else:
                time.sleep(0.3)

        output = buf.decode("utf-8", errors="replace")

        # ── Parser les résultats entre les marqueurs ──
        for cmd_name, _ in DYNAMIC_CMDS:
            tag_s = f"__MRK_{cmd_name}_S__"
            tag_e = f"__MRK_{cmd_name}_E__"
            if tag_s in output and tag_e in output:
                start = output.index(tag_s) + len(tag_s)
                end = output.index(tag_e)
                value = output[start:end].strip()
                # Filtrer les lignes qui sont juste l'echo de la commande
                clean_lines = [
                    line for line in value.splitlines()
                    if not line.strip().startswith("echo ") and "__MRK_" not in line
                ]
                dynamic[cmd_name] = "\n".join(clean_lines).strip()
                logger.debug(f"OPNsense [{cmd_name}]: {dynamic[cmd_name][:80]}")

        channel.send("exit\n")
        time.sleep(0.3)
        channel.close()

        logger.info(f"OPNsense dynamic commands: {len(dynamic)}/{len(DYNAMIC_CMDS)} récupérées")

    except Exception as e:
        logger.warning(f"OPNsense interactive shell failed: {e}")

    return dynamic


def _build_opnsense_from_config(
    result: SSHCollectResult,
    config: dict,
    dynamic: dict,
) -> None:
    """
    Construit SSHCollectResult à partir des données config.xml (SFTP)
    enrichies par les données dynamiques (shell interactif, optionnel).
    """
    result.hostname = config.get("hostname", "")

    # OS info (préférer les données dynamiques si disponibles)
    result.os_info = {
        "distro": dynamic.get("os_name", "OPNsense").strip(),
        "version": dynamic.get("os_version", config.get("firmware_version", "")).strip(),
        "version_full": dynamic.get("installed_version", "").strip(),
        "kernel": dynamic.get("kernel", "").strip(),
        "arch": dynamic.get("arch", "").strip(),
        "uptime": dynamic.get("uptime", "").strip(),
        "type": "opnsense",
    }

    # Réseau
    result.network = {
        "interfaces": config.get("interfaces_text", ""),
        "routes": "",
        "dns": config.get("dns_servers", ""),
        "listening_ports": "",
    }

    # Sécurité (principalement config.xml)
    pf_status_raw = dynamic.get("pf_status", "")
    pf_enabled = config.get("firewall_enabled", True)
    if pf_status_raw:
        pf_enabled = (
            "enabled" in pf_status_raw.lower()
            or "current entries" in pf_status_raw.lower()
        )

    result.security = {
        "firewall_engine": "pf",
        "firewall_enabled": pf_enabled,
        "firewall_status_raw": pf_status_raw or "Déduit de config.xml (pf actif par défaut)",
        "firewall_rules_count": config.get("firewall_rules_count", 0),
        "firewall_rules": config.get("firewall_rules_text", ""),
        "nat_rules": f"{config.get('nat_rules_count', 0)} règle(s) NAT",
        "states_count": "",
        "aliases": "",
        "ssh_config_raw": config.get("ssh_config_raw", ""),
        "ssh_permit_root_login": config.get("ssh_permit_root_login", "NOT_SET"),
        "suricata_status": config.get("suricata_status", "NOT_RUNNING"),
        "syslog_remote": config.get("syslog_remote", "NONE"),
        "webgui_protocol": config.get("webgui_protocol", "https"),
        # Données enrichies inspirées opnDossier
        "ids_ips_mode": config.get("ids_ips_mode", False),
        "any_any_rules": config.get("any_any_rules", []),
        "any_any_rules_count": config.get("any_any_rules_count", 0),
        "rules_without_descr": config.get("rules_without_descr", 0),
        "rules_with_log": config.get("rules_with_log", 0),
        "rules_log_ratio": config.get("rules_log_ratio", "0/0"),
        "wan_blockpriv": config.get("wan_blockpriv", False),
        "wan_blockbogons": config.get("wan_blockbogons", False),
        "dnssec_enabled": config.get("dnssec_enabled", False),
        "unbound_enabled": config.get("unbound_enabled", False),
        "unused_interfaces": config.get("unused_interfaces", []),
        "unused_interfaces_count": config.get("unused_interfaces_count", 0),
        "ntp_servers": config.get("ntp_servers", []),
        "ntp_servers_count": config.get("ntp_servers_count", 0),
        "snmp_community": config.get("snmp_community", ""),
        "snmp_default_community": config.get("snmp_default_community", False),
        "source": "config.xml" + (" + dynamic" if dynamic else ""),
    }

    # Services / VPN / CARP
    result.services = {
        "services_list": "",
        "openvpn_status": config.get("openvpn_status", ""),
        "ipsec_status": config.get("ipsec_status", ""),
        "wireguard_status": config.get("wireguard_status", ""),
        "carp_status": config.get("carp_status", ""),
    }

    # Utilisateurs
    result.users = {
        "users_with_shell": config.get("users", ""),
    }

    # Mises à jour (données dynamiques uniquement)
    updates_raw = dynamic.get("updates_pending", "")
    has_updates = True  # Default : considérer qu'il y a des MàJ (safe)
    if "EXIT=0" in updates_raw:
        has_updates = False

    result.updates = {
        "update_check_raw": updates_raw or "Non vérifiable (shell menu OPNsense)",
        "updates_available": has_updates if updates_raw else None,
        "pkg_audit": dynamic.get("pkg_audit", "Non vérifiable (shell menu OPNsense)"),
    }

    # Stockage / Config
    result.storage = {
        "config_xml_size": config.get("config_xml_size", ""),
        "config_backup_count": config.get("config_backup_count", "0"),
    }

    # Stocker les données brutes pour evidence / debug
    result.raw_outputs = {
        "_source": "config.xml (SFTP) + shell interactif",
        "_config_hostname": config.get("hostname", ""),
        "_config_rules": str(config.get("firewall_rules_count", 0)),
        "_config_interfaces": config.get("interfaces_text", "")[:300],
        "_config_ssh": config.get("ssh_config_raw", ""),
        "_config_suricata": config.get("suricata_status", ""),
        "_config_syslog": config.get("syslog_remote", ""),
        "_config_carp": config.get("carp_status", ""),
        "_config_any_any": str(config.get("any_any_rules_count", 0)),
        "_config_dnssec": str(config.get("dnssec_enabled", False)),
        "_config_wan_bogons": str(config.get("wan_blockbogons", False)),
        "_config_ntp": str(config.get("ntp_servers_count", 0)),
        "_dynamic_available": str(bool(dynamic)),
    }
    # Ajouter les sorties dynamiques si disponibles
    for k, v in dynamic.items():
        result.raw_outputs[f"dyn_{k}"] = str(v)[:500]


def _parse_opnsense_results(result: SSHCollectResult, raw: dict[str, str]) -> None:
    """Parse les sorties OPNsense en données structurées (fallback exec_command)."""
    result.hostname = raw.get("hostname", "").strip()

    # OS info
    installed_ver = raw.get("installed_version", "")
    result.os_info = {
        "distro": raw.get("os_name", "OPNsense").strip(),
        "version": raw.get("os_version", "").strip(),
        "version_full": installed_ver.strip(),
        "kernel": raw.get("kernel", "").strip(),
        "arch": raw.get("arch", "").strip(),
        "uptime": raw.get("uptime", "").strip(),
        "type": "opnsense",
    }

    # Réseau
    result.network = {
        "interfaces": raw.get("interfaces", ""),
        "routes": raw.get("routes", ""),
        "dns": raw.get("dns", ""),
        "listening_ports": raw.get("listening_ports", ""),
    }

    # Firewall (pf)
    pf_status = raw.get("pf_status", "")
    pf_enabled = ("status: enabled" in pf_status.lower()) if pf_status else False
    # Fallback : si pfctl -s info contient des stats (entries, searches),
    # c'est que pf est actif même si le parsing du mot "Enabled" a échoué
    if not pf_enabled and pf_status and ("current entries" in pf_status.lower() or "searches" in pf_status.lower()):
        pf_enabled = True
    pf_rules = raw.get("pf_rules", "")
    pf_rules_count_raw = raw.get("pf_rules_count", "0").strip()
    # Nettoyer : extraire uniquement les chiffres (wc -l sur FreeBSD retourne "      15")
    pf_rules_count = ''.join(c for c in pf_rules_count_raw if c.isdigit()) or "0"

    result.security = {
        "firewall_engine": "pf",
        "firewall_enabled": pf_enabled,
        "firewall_status_raw": pf_status,
        "firewall_rules_count": int(pf_rules_count) if pf_rules_count.isdigit() else 0,
        "firewall_rules": pf_rules,
        "nat_rules": raw.get("pf_nat", ""),
        "states_count": raw.get("pf_states_count", ""),
        "aliases": raw.get("aliases", ""),
        "ssh_config_raw": raw.get("ssh_config", ""),
        "ssh_permit_root_login": raw.get("ssh_root_login", "NOT_SET").strip(),
        "suricata_status": raw.get("suricata_status", "NOT_RUNNING").strip(),
        "syslog_remote": raw.get("syslog_remote", "NONE"),
    }

    # VPN
    result.services = {
        "services_list": raw.get("services", ""),
        "openvpn_status": raw.get("openvpn_status", ""),
        "ipsec_status": raw.get("ipsec_status", ""),
        "wireguard_status": raw.get("wireguard_status", ""),
        "carp_status": raw.get("carp_status", ""),
    }

    result.users = {
        "users_with_shell": raw.get("users", ""),
    }

    # Mises à jour
    updates_raw = raw.get("updates_pending", "")
    has_updates = "EXIT=0" not in updates_raw  # exit 0 = à jour
    result.updates = {
        "update_check_raw": updates_raw,
        "updates_available": has_updates,
        "pkg_audit": raw.get("pkg_audit", ""),
    }

    # Config
    result.storage = {
        "config_xml_size": raw.get("config_xml_size", ""),
        "config_backup_count": raw.get("config_backup_count", "0").strip(),
    }


def _parse_stormshield_results(result: SSHCollectResult, raw: dict[str, str]) -> None:
    """Parse les sorties Stormshield SNS en données structurées."""
    # Extraire hostname
    hostname_raw = raw.get("hostname", "")
    # FORMAT: "Name=xxx"
    hostname = hostname_raw.split("=", 1)[-1].strip() if "=" in hostname_raw else hostname_raw.strip()
    result.hostname = hostname

    # Version / système
    version_raw = raw.get("system_info", "")
    result.os_info = {
        "distro": "Stormshield SNS",
        "version_raw": version_raw.strip(),
        "serial": raw.get("serial", "").split("=", 1)[-1].strip() if "=" in raw.get("serial", "") else "",
        "uptime": raw.get("uptime", "").strip(),
        "license": raw.get("license", "").strip(),
        "type": "stormshield",
    }

    # Réseau
    result.network = {
        "interfaces": raw.get("interfaces", ""),
        "routes": raw.get("routes", ""),
        "dns": raw.get("dns", ""),
    }

    # Firewall
    filter_count = raw.get("filter_rules_count", "0").strip()
    result.security = {
        "firewall_engine": "stormshield_asq",
        "filter_rules_count": int(filter_count) if filter_count.isdigit() else 0,
        "filter_rules": raw.get("filter_rules", ""),
        "nat_rules": raw.get("nat_rules", ""),
        "active_connections": raw.get("active_connections", ""),
        "admin_accounts": raw.get("admin_accounts", ""),
        "ssh_status": raw.get("ssh_status", ""),
        "antivirus": raw.get("antivirus", ""),
        "ips_status": raw.get("ips_status", ""),
        "alarm_list": raw.get("alarm_list", ""),
        "syslog_servers": raw.get("syslog_servers", ""),
    }

    # Objets
    result.users = {
        "objects_host": raw.get("objects_host", ""),
        "objects_network": raw.get("objects_network", ""),
        "objects_group": raw.get("objects_group", ""),
    }

    # VPN
    result.services = {
        "services_status": raw.get("services_status", ""),
        "vpn_ipsec_peers": raw.get("vpn_ipsec_peers", ""),
        "vpn_ipsec_sa": raw.get("vpn_ipsec_sa", ""),
        "vpn_ssl_status": raw.get("vpn_ssl_status", ""),
        "ha_status": raw.get("ha_status", ""),
    }

    # MàJ
    result.updates = {
        "firmware_version": version_raw.strip(),
        "update_status": raw.get("update_status", ""),
    }

    result.storage = {}


def _parse_fortigate_results(result: SSHCollectResult, raw: dict[str, str]) -> None:
    """Parse les sorties FortiGate (FortiOS) en données structurées."""
    # Hostname
    hostname_raw = raw.get("hostname", "")
    # Format: "hostname : FGT-XXX"
    if ":" in hostname_raw:
        result.hostname = hostname_raw.split(":", 1)[-1].strip()
    else:
        result.hostname = hostname_raw.strip()

    # Version / système
    status_raw = raw.get("system_status", "")
    firmware_raw = raw.get("firmware", "")
    serial_raw = raw.get("serial", "")

    # Extraire version FortiOS
    version = ""
    for line in status_raw.splitlines():
        if "Version" in line:
            version = line.split(":", 1)[-1].strip() if ":" in line else line
            break
    if not version and firmware_raw:
        version = firmware_raw.split(":", 1)[-1].strip() if ":" in firmware_raw else firmware_raw

    serial = ""
    for line in (serial_raw or status_raw).splitlines():
        if "Serial" in line:
            serial = line.split(":", 1)[-1].strip() if ":" in line else line
            break

    result.os_info = {
        "distro": "FortiOS",
        "version": version,
        "serial": serial,
        "uptime": raw.get("uptime", "").strip(),
        "license": raw.get("license", "").strip(),
        "system_status_raw": status_raw,
        "type": "fortigate",
    }

    # Réseau
    result.network = {
        "interfaces": raw.get("interfaces", ""),
        "interfaces_physical": raw.get("interfaces_physical", ""),
        "routes": raw.get("routes", ""),
        "dns": raw.get("dns", ""),
        "arp_table": raw.get("arp_table", ""),
    }

    # Firewall
    policy_count_raw = raw.get("policy_count", "0").strip()
    result.security = {
        "firewall_engine": "fortios",
        "policy_count": int(policy_count_raw) if policy_count_raw.isdigit() else 0,
        "policies": raw.get("policies", ""),
        "policy_summary": raw.get("policy_summary", ""),
        "vip": raw.get("vip", ""),
        "address_objects": raw.get("address_objects", ""),
        "address_groups": raw.get("address_groups", ""),
        "admin_users": raw.get("admin_users", ""),
        "admin_settings": raw.get("admin_settings", ""),
        "password_policy": raw.get("password_policy", ""),
        "trusted_hosts": raw.get("trusted_hosts", ""),
        "antivirus_profile": raw.get("antivirus_profile", ""),
        "ips_settings": raw.get("ips_settings", ""),
        "webfilter": raw.get("webfilter", ""),
        "ntp": raw.get("ntp", ""),
        "snmp": raw.get("snmp", ""),
        "session_count": raw.get("session_count", ""),
    }

    # VPN
    result.services = {
        "vpn_ipsec_tunnels": raw.get("vpn_ipsec_tunnels", ""),
        "vpn_ssl_status": raw.get("vpn_ssl_status", ""),
        "vpn_ssl_settings": raw.get("vpn_ssl_settings", ""),
        "ha_status": raw.get("ha_status", ""),
    }

    result.users = {
        "admin_users": raw.get("admin_users", ""),
    }

    # Logs
    result.updates = {
        "firmware_version": version,
        "log_settings": raw.get("log_settings", ""),
        "log_syslogd": raw.get("log_syslogd", ""),
        "log_fortianalyzer": raw.get("log_fortianalyzer", ""),
        "log_disk": raw.get("log_disk", ""),
    }

    result.storage = {}
