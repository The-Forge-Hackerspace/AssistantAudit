"""
Collecteur WinRM — Connexion à un serveur Windows via WinRM (pywinrm)
et exécution de commandes PowerShell d'audit système.
"""

import logging
from dataclasses import dataclass, field

import winrm

logger = logging.getLogger(__name__)

WINRM_TIMEOUT = 60


@dataclass
class WinRMCollectResult:
    """Résultat brut de la collecte WinRM."""

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


# ── Commandes PowerShell de collecte Windows ─────────────────
# Chaque commande renvoie du texte structuré qu'on parse ensuite.
WINDOWS_COMMANDS: dict[str, str] = {
    # --- Système ---
    "hostname": "$env:COMPUTERNAME",
    "os_info": (
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object Caption, Version, BuildNumber, OSArchitecture, "
        "LastBootUpTime, InstallDate | Format-List"
    ),
    "domain_info": (
        "(Get-CimInstance Win32_ComputerSystem).Domain + '|' + (Get-CimInstance Win32_ComputerSystem).PartOfDomain"
    ),
    # --- Mises à jour ---
    "installed_updates": (
        "Get-HotFix | Sort-Object InstalledOn -Descending | "
        "Select-Object -First 10 HotFixID, Description, InstalledOn | Format-Table -AutoSize"
    ),
    "last_update_date": (
        "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 1 -ExpandProperty InstalledOn"
    ),
    "wsus_config": (
        "try { "
        "(Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate' "
        "-ErrorAction Stop).WUServer } catch { 'NOT_CONFIGURED' }"
    ),
    # --- Réseau ---
    "ip_config": (
        "Get-NetIPAddress -AddressFamily IPv4 | "
        "Where-Object { $_.IPAddress -ne '127.0.0.1' } | "
        "Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table -AutoSize"
    ),
    "dns_servers": (
        "Get-DnsClientServerAddress -AddressFamily IPv4 | "
        "Where-Object { $_.ServerAddresses } | "
        "Select-Object InterfaceAlias, ServerAddresses | Format-Table -AutoSize"
    ),
    "listening_ports": (
        "Get-NetTCPConnection -State Listen | "
        "Select-Object LocalAddress, LocalPort, OwningProcess | "
        "Sort-Object LocalPort | Format-Table -AutoSize"
    ),
    # --- Pare-feu ---
    "firewall_profiles": (
        "Get-NetFirewallProfile | "
        "Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction | "
        "Format-Table -AutoSize"
    ),
    # --- RDP ---
    "rdp_enabled": (
        "try { "
        "(Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server' "
        "-ErrorAction Stop).fDenyTSConnections } catch { 'UNKNOWN' }"
    ),
    "rdp_nla": (
        "try { "
        "(Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp' "
        "-ErrorAction Stop).UserAuthentication } catch { 'UNKNOWN' }"
    ),
    # --- Comptes ---
    "admin_account": (
        "Get-LocalUser | Where-Object { $_.SID -like '*-500' } | Select-Object Name, Enabled, LastLogon | Format-List"
    ),
    "local_users": (
        "Get-LocalUser | "
        "Select-Object Name, Enabled, LastLogon, PasswordLastSet, PasswordExpires | "
        "Format-Table -AutoSize"
    ),
    "local_admins": (
        "Get-LocalGroupMember -Group 'Administrateurs' -ErrorAction SilentlyContinue | "
        "Select-Object Name, ObjectClass | Format-Table -AutoSize; "
        "Get-LocalGroupMember -Group 'Administrators' -ErrorAction SilentlyContinue | "
        "Select-Object Name, ObjectClass | Format-Table -AutoSize"
    ),
    # --- Politique de mot de passe ---
    "password_policy": "net accounts",
    # --- Verrouillage de compte ---
    "lockout_policy": ("net accounts | Select-String -Pattern 'Lockout|verrouillage'"),
    # --- Rôles & Fonctionnalités ---
    "installed_roles": (
        "try { Get-WindowsFeature | Where-Object Installed | "
        "Select-Object Name, DisplayName | Format-Table -AutoSize } "
        "catch { 'NOT_SERVER_OS' }"
    ),
    # --- Services ---
    "services_running": (
        "Get-Service | Where-Object { $_.Status -eq 'Running' } | "
        "Select-Object Name, DisplayName, StartType | "
        "Sort-Object Name | Format-Table -AutoSize"
    ),
    # --- Journalisation ---
    "event_log_sizes": (
        "Get-WinEvent -ListLog Security, System, Application | "
        "Select-Object LogName, MaximumSizeInBytes, RecordCount, IsEnabled | "
        "Format-Table -AutoSize"
    ),
    "audit_policy": "auditpol /get /category:* 2>&1 | Select-Object -First 40",
    # --- Antivirus / Defender ---
    "defender_status": (
        "try { Get-MpComputerStatus | "
        "Select-Object AMRunningMode, AntivirusEnabled, AntispywareEnabled, "
        "RealTimeProtectionEnabled, AntivirusSignatureLastUpdated | Format-List } "
        "catch { 'NOT_AVAILABLE' }"
    ),
    # --- Stockage ---
    "disk_usage": (
        'Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | '
        "Select-Object DeviceID, "
        "@{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}, "
        "@{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,1)}}, "
        "@{N='UsedPct';E={[math]::Round(($_.Size-$_.FreeSpace)/$_.Size*100,1)}} | "
        "Format-Table -AutoSize"
    ),
}


def collect_via_winrm(
    host: str,
    username: str,
    password: str,
    port: int = 5985,
    use_ssl: bool = False,
    transport: str = "ntlm",
) -> WinRMCollectResult:
    """
    Se connecte au serveur Windows via WinRM et collecte les informations d'audit.

    Args:
        host: Adresse IP ou hostname du serveur
        username: Utilisateur Windows (DOMAIN\\user ou user)
        password: Mot de passe
        port: Port WinRM (5985 HTTP / 5986 HTTPS)
        use_ssl: Utiliser HTTPS (port 5986)
        transport: Méthode d'auth (ntlm, kerberos, basic)

    Returns:
        WinRMCollectResult avec toutes les données collectées
    """
    result = WinRMCollectResult()

    scheme = "https" if use_ssl else "http"
    endpoint = f"{scheme}://{host}:{port}/wsman"

    try:
        logger.info(f"Connexion WinRM vers {endpoint} en tant que {username}...")

        cert_validation = "validate"
        if use_ssl:
            # En mode SSL, la validation est désactivée car les serveurs
            # internes utilisent souvent des certificats auto-signés.
            # TODO (production) : configurer un CA bundle + validation stricte
            logger.warning(
                f"[SECURITE] WinRM SSL vers {host} : validation du certificat "
                f"désactivée. Risque MITM sur réseaux non sûrs."
            )
            cert_validation = "ignore"

        session = winrm.Session(
            endpoint,
            auth=(username, password),
            transport=transport,
            server_cert_validation=cert_validation,
            operation_timeout_sec=WINRM_TIMEOUT,
            read_timeout_sec=WINRM_TIMEOUT + 10,
        )

        # Test de connexion
        test = session.run_ps("$env:COMPUTERNAME")
        if test.status_code != 0:
            result.error = f"Échec de connexion WinRM: {test.std_err.decode('utf-8', errors='replace')}"
            return result

        logger.info(f"Connexion WinRM établie vers {host}")

        # Exécuter toutes les commandes PowerShell
        raw_outputs: dict[str, str] = {}
        for cmd_name, cmd in WINDOWS_COMMANDS.items():
            try:
                resp = session.run_ps(cmd)
                output = resp.std_out.decode("utf-8", errors="replace").strip()
                if resp.status_code != 0:
                    err = resp.std_err.decode("utf-8", errors="replace").strip()
                    if err:
                        output = f"ERROR: {err}"
                raw_outputs[cmd_name] = output
            except Exception as e:
                raw_outputs[cmd_name] = f"ERROR: {e}"
                logger.debug(f"Commande '{cmd_name}' échouée: {e}")

        result.raw_outputs = raw_outputs
        result.success = True

        # Parser les résultats
        _parse_winrm_results(result, raw_outputs)

    except winrm.exceptions.InvalidCredentialsError:
        result.error = "Échec d'authentification WinRM (identifiants invalides)"
        logger.error(f"Auth WinRM échouée pour {username}@{host}")
    except winrm.exceptions.WinRMTransportError as e:
        result.error = f"Erreur de transport WinRM: {e}"
        logger.error(f"Transport WinRM échoué vers {host}: {e}")
    except Exception as e:
        result.error = f"Erreur de connexion WinRM: {e}"
        logger.error(f"Erreur collecte WinRM {host}: {e}")

    return result


def _parse_winrm_results(result: WinRMCollectResult, raw: dict[str, str]) -> None:
    """Parse les sorties brutes des commandes PowerShell en données structurées."""

    # ── Hostname ──
    result.hostname = raw.get("hostname", "").strip()

    # ── OS Info ──
    os_raw = raw.get("os_info", "")
    os_info: dict = {"raw": os_raw}
    for line in os_raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            os_info[key.strip()] = val.strip()

    domain_raw = raw.get("domain_info", "")
    parts = domain_raw.split("|")
    if len(parts) >= 2:
        os_info["domain"] = parts[0].strip()
        os_info["is_domain_joined"] = parts[1].strip().lower() == "true"

    os_info["caption"] = os_info.get("Caption", "Windows Server")
    os_info["version"] = os_info.get("Version", "")
    os_info["build"] = os_info.get("BuildNumber", "")
    result.os_info = os_info

    # ── Réseau ──
    result.network = {
        "ip_config": raw.get("ip_config", ""),
        "dns_servers": raw.get("dns_servers", ""),
        "listening_ports": raw.get("listening_ports", ""),
    }

    # ── Firewall ──
    fw_raw = raw.get("firewall_profiles", "")
    fw_profiles: list[dict] = []
    all_enabled = True
    for line in fw_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("Name"):
            continue
        parts = line.split()
        if len(parts) >= 4:
            enabled = parts[1].strip().lower() == "true"
            if not enabled:
                all_enabled = False
            fw_profiles.append(
                {
                    "name": parts[0],
                    "enabled": enabled,
                    "default_inbound": parts[2],
                    "default_outbound": parts[3],
                }
            )

    security: dict = {
        "firewall_profiles": fw_profiles,
        "firewall_all_enabled": all_enabled,
        "firewall_raw": fw_raw,
    }

    # ── RDP ──
    rdp_deny = raw.get("rdp_enabled", "UNKNOWN").strip()
    rdp_nla = raw.get("rdp_nla", "UNKNOWN").strip()
    security["rdp_enabled"] = rdp_deny == "0"  # 0 = enabled, 1 = disabled
    security["rdp_nla_enabled"] = rdp_nla == "1"  # 1 = NLA required
    security["rdp_raw_deny"] = rdp_deny
    security["rdp_raw_nla"] = rdp_nla

    # ── Comptes ──
    admin_raw = raw.get("admin_account", "")
    admin_renamed = True  # Suppose renommé
    for line in admin_raw.splitlines():
        if "Name" in line and ":" in line:
            name = line.split(":")[1].strip().lower()
            if name in ("administrator", "administrateur"):
                admin_renamed = False

    users: dict = {
        "admin_account_raw": admin_raw,
        "admin_renamed": admin_renamed,
        "local_users": raw.get("local_users", ""),
        "local_admins": raw.get("local_admins", ""),
    }

    # ── Politique de mot de passe ──
    pwd_policy_raw = raw.get("password_policy", "")
    pwd_policy: dict = {"raw": pwd_policy_raw}
    for line in pwd_policy_raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            pwd_policy[key.strip()] = val.strip()

    # Vérifier complexité et longueur min
    min_length_str = pwd_policy.get("Minimum password length", pwd_policy.get("Longueur minimale du mot de passe", "0"))
    try:
        min_length = int(min_length_str.strip())
    except (ValueError, AttributeError):
        min_length = 0
    pwd_policy["min_length_value"] = min_length
    pwd_policy["meets_12_chars"] = min_length >= 12

    users["password_policy"] = pwd_policy

    # ── Verrouillage ──
    lockout_threshold_str = pwd_policy.get("Lockout threshold", pwd_policy.get("Seuil de verrouillage du compte", "0"))
    try:
        lockout_threshold = int(lockout_threshold_str.strip())
    except (ValueError, AttributeError):
        lockout_threshold = 0
    users["lockout_configured"] = lockout_threshold > 0
    users["lockout_threshold"] = lockout_threshold

    result.users = users
    security["password_policy"] = pwd_policy

    # ── Rôles ──
    result.services = {
        "installed_roles": raw.get("installed_roles", ""),
        "services_running": raw.get("services_running", ""),
    }

    # ── Journalisation ──
    event_logs_raw = raw.get("event_log_sizes", "")
    logs: list[dict] = []
    for line in event_logs_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("LogName"):
            continue
        parts = line.split()
        if len(parts) >= 4:
            try:
                size_bytes = int(parts[1])
                size_mb = round(size_bytes / (1024 * 1024), 1)
            except (ValueError, IndexError):
                size_mb = 0
            logs.append(
                {
                    "name": parts[0],
                    "max_size_mb": size_mb,
                    "record_count": parts[2] if len(parts) > 2 else "0",
                    "enabled": parts[3] if len(parts) > 3 else "Unknown",
                }
            )

    security["event_logs"] = logs
    security["event_logs_raw"] = event_logs_raw
    security["audit_policy"] = raw.get("audit_policy", "")

    # Vérifier si les logs >= 100 MB
    min_log_size = min((l.get("max_size_mb", 0) for l in logs), default=0) if logs else 0
    security["logs_min_100mb"] = min_log_size >= 100

    # ── Antivirus / Defender ──
    defender = raw.get("defender_status", "NOT_AVAILABLE")
    av_active = False
    if "NOT_AVAILABLE" not in defender and "ERROR" not in defender:
        av_active = "True" in defender  # AntivirusEnabled : True
    security["defender_raw"] = defender
    security["antivirus_active"] = av_active

    result.security = security

    # ── Mises à jour ──
    last_update = raw.get("last_update_date", "").strip()
    wsus = raw.get("wsus_config", "NOT_CONFIGURED").strip()
    result.updates = {
        "installed_updates_raw": raw.get("installed_updates", ""),
        "last_update_date": last_update,
        "wsus_configured": wsus != "NOT_CONFIGURED" and "ERROR" not in wsus,
        "wsus_server": wsus if wsus != "NOT_CONFIGURED" else None,
    }

    # ── Stockage ──
    result.storage = {
        "disk_usage": raw.get("disk_usage", ""),
    }
