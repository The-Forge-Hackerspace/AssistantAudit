"""
Scanner Nmap — outil de découverte réseau intégré.
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)

# ── Whitelist des flags Nmap autorisés ───────────────────────────────────────
# Seuls ces flags (et leurs variantes) sont acceptés en extra_args.
# Les flags dangereux (--script avec chemin arbitraire, -oN/-oG, --interactive,
# --exec, etc.) sont bloqués par défaut.
ALLOWED_NMAP_FLAGS = {
    # Scan types
    "-sS",
    "-sT",
    "-sU",
    "-sA",
    "-sW",
    "-sM",
    "-sN",
    "-sF",
    "-sX",
    "-sV",
    "-sC",
    "-sn",
    "-sP",
    "-sL",
    "-sO",
    # Port specification
    "-p",
    "--top-ports",
    "-F",
    # Timing
    "-T0",
    "-T1",
    "-T2",
    "-T3",
    "-T4",
    "-T5",
    "--min-rate",
    "--max-rate",
    "--min-parallelism",
    "--max-parallelism",
    "--host-timeout",
    "--scan-delay",
    "--max-scan-delay",
    # Detection
    "-O",
    "-A",
    "--osscan-guess",
    "--version-intensity",
    "--version-light",
    "--version-all",
    # Output control (safe ones only — XML stdout already handled)
    "-v",
    "-vv",
    "-d",
    "--reason",
    "--open",
    # Host discovery
    "-Pn",
    "-PS",
    "-PA",
    "-PU",
    "-PY",
    "-PE",
    "-PP",
    "-PM",
    "-PR",
    "--disable-arp-ping",
    "--traceroute",
    # DNS
    "-n",
    "-R",
    "--dns-servers",
    # Misc safe
    "--max-retries",
    "--min-rtt-timeout",
    "--max-rtt-timeout",
    "--initial-rtt-timeout",
    "--defeat-rst-ratelimit",
    "-6",
    "-e",
}

# Regex : un flag Nmap valide commence par "-" et contient [a-zA-Z0-9-]
_FLAG_PATTERN = re.compile(r"^-{1,2}[a-zA-Z][a-zA-Z0-9\-]*$")

# Regex : une valeur d'argument Nmap (numéro, IP, plage de ports, etc.)
_VALUE_PATTERN = re.compile(r"^[a-zA-Z0-9_.:/\-,]+$")

# Flags explicitement interdits (même s'ils matchent le pattern)
BLOCKED_NMAP_FLAGS = {
    "--script",
    "--script-args",
    "--script-args-file",
    "--script-trace",
    "--script-updatedb",
    "--script-help",
    "-oN",
    "-oG",
    "-oX",
    "-oA",
    "-oS",  # output vers fichiers
    "--stylesheet",  # XSLT injection
    "--interactive",
    "--exec",  # exécution arbitraire
    "--datadir",
    "--servicedb",
    "--versiondb",  # chemins arbitraires
    "--resume",  # reprise depuis fichier
    "--iflist",
    "--send-eth",
    "--send-ip",
    "--privileged",
    "--unprivileged",
}


def sanitize_nmap_args(extra_args: Optional[list[str]]) -> list[str]:
    """
    Valide et filtre les arguments Nmap fournis par l'utilisateur.

    Retourne une liste nettoyée. Lève ValueError si un argument est dangereux.
    """
    if not extra_args:
        return []

    sanitized = []
    for arg in extra_args:
        arg = arg.strip()
        if not arg:
            continue

        # Vérifier si c'est un flag
        if arg.startswith("-"):
            # Extraire le flag de base (sans valeur collée, ex: -p80 → -p)
            flag_base = arg
            # Gérer les flags avec valeur collée comme -p80, -T4, -PS80
            for known in sorted(ALLOWED_NMAP_FLAGS, key=len, reverse=True):
                if arg.startswith(known) and len(arg) > len(known):
                    flag_base = known
                    value_part = arg[len(known) :]
                    if not _VALUE_PATTERN.match(value_part):
                        raise ValueError(f"Valeur invalide dans l'argument Nmap : '{arg}'")
                    break

            # Vérifier flags bloqués
            if flag_base in BLOCKED_NMAP_FLAGS:
                raise ValueError(f"Argument Nmap interdit pour raison de sécurité : '{flag_base}'")

            # Vérifier whitelist
            if flag_base in ALLOWED_NMAP_FLAGS:
                sanitized.append(arg)
            elif _FLAG_PATTERN.match(arg):
                # Flag inconnu mais syntaxe valide → bloquer par sécurité
                raise ValueError(
                    f"Argument Nmap non autorisé : '{arg}'. Contactez un administrateur pour l'ajouter à la whitelist."
                )
            else:
                raise ValueError(f"Argument Nmap invalide : '{arg}'")
        else:
            # C'est une valeur (port range, nombre, etc.) — valider le format
            if not _VALUE_PATTERN.match(arg):
                raise ValueError(f"Valeur d'argument Nmap invalide : '{arg}'")
            sanitized.append(arg)

    return sanitized


@dataclass
class DiscoveredPort:
    port_number: int
    protocol: str
    state: str
    service_name: str = ""
    product: str = ""
    version: str = ""


@dataclass
class DiscoveredHost:
    ip_address: str
    hostname: str = ""
    mac_address: str = ""
    vendor: str = ""
    os_guess: str = ""
    status: str = "up"
    ports: list[DiscoveredPort] = field(default_factory=list)


@dataclass
class NmapScanResult:
    success: bool
    target: str
    hosts: list[DiscoveredHost] = field(default_factory=list)
    raw_xml: str = ""
    duration_seconds: int = 0
    error: str = ""


class NmapScanner:
    """Interface vers Nmap pour la découverte réseau."""

    def __init__(self, timeout: int = 600):
        self.timeout = timeout

    def scan(
        self,
        target: str,
        scan_type: str = "discovery",
        extra_args: Optional[list[str]] = None,
    ) -> NmapScanResult:
        """
        Exécute un scan Nmap et retourne les résultats structurés.

        Args:
            target: IP, CIDR, ou hostname à scanner
            scan_type: 'discovery' | 'port_scan' | 'full'
            extra_args: arguments Nmap supplémentaires
        """
        args = self._build_args(target, scan_type, extra_args)
        logger.info(f"Lancement scan Nmap : {' '.join(args)}")

        try:
            process = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if process.returncode != 0 and not process.stdout:
                return NmapScanResult(success=False, target=target, error=process.stderr)

            result = self._parse_xml(process.stdout, target)
            return result

        except ValueError as e:
            logger.warning(f"Arguments Nmap rejetés : {e}")
            return NmapScanResult(success=False, target=target, error=str(e))
        except subprocess.TimeoutExpired:
            return NmapScanResult(success=False, target=target, error=f"Timeout après {self.timeout}s")
        except FileNotFoundError:
            return NmapScanResult(success=False, target=target, error="Nmap non installé ou introuvable dans le PATH")

    def _build_args(self, target: str, scan_type: str, extra_args: Optional[list[str]]) -> list[str]:
        """Construit la ligne de commande Nmap avec validation des arguments.

        Défense en profondeur contre l'injection :
        - `target` validé en amont par une regex stricte (IP / CIDR / hostname)
        - interdiction des préfixes '-' qui seraient interprétés comme options
        - arguments supplémentaires filtrés via `sanitize_nmap_args`
        - `subprocess.run(..., shell=False)` : aucun parsing shell
        """
        # Valider le target AVANT toute construction d'argv (no '-', no space, whitelist stricte).
        if not target or target.startswith("-"):
            raise ValueError("Target Nmap invalide")
        if not re.match(r"^[a-zA-Z0-9._:/\-]+$", target):
            raise ValueError("Target Nmap invalide")
        if len(target) > 255:
            raise ValueError("Target Nmap trop long")

        base = ["nmap", "-oX", "-"]  # sortie XML sur stdout

        type_args = {
            "discovery": ["-sn"],  # Ping scan uniquement
            "port_scan": ["-sV", "--top-ports", "1000"],
            "full": ["-sV", "-sC", "-O", "-p-"],
            "custom": [],  # Pas d'args par défaut, tout vient de extra_args
        }
        base.extend(type_args.get(scan_type, ["-sn"]))

        # Sanitize extra_args : whitelist + validation
        if extra_args:
            safe_args = sanitize_nmap_args(extra_args)
            base.extend(safe_args)

        # Marqueur de fin d'options : tout ce qui suit est traité comme opérande (cible),
        # jamais comme une option, même si la whitelist manquait un cas.
        base.append("--")
        base.append(target)
        return base

    def _parse_xml(self, xml_output: str, target: str) -> NmapScanResult:
        """Parse la sortie XML de Nmap"""
        try:
            root = ET.fromstring(xml_output)
        except Exception as e:
            return NmapScanResult(success=False, target=target, error=f"Erreur parsing XML : {e}")

        hosts = []
        for host_elem in root.findall("host"):
            status = host_elem.find("status")
            if status is not None and status.get("state") != "up":
                continue

            # IP
            addr = host_elem.find("address[@addrtype='ipv4']")
            if addr is None:
                addr = host_elem.find("address[@addrtype='ipv6']")
            ip = addr.get("addr", "") if addr is not None else ""

            # MAC
            mac_elem = host_elem.find("address[@addrtype='mac']")
            mac = mac_elem.get("addr", "") if mac_elem is not None else ""
            vendor = mac_elem.get("vendor", "") if mac_elem is not None else ""

            # Hostname
            hostname = ""
            hostnames_elem = host_elem.find("hostnames/hostname")
            if hostnames_elem is not None:
                hostname = hostnames_elem.get("name", "")

            # OS
            os_guess = ""
            osmatch = host_elem.find("os/osmatch")
            if osmatch is not None:
                os_guess = osmatch.get("name", "")

            # Ports
            ports = []
            for port_elem in host_elem.findall("ports/port"):
                state = port_elem.find("state")
                service = port_elem.find("service")
                ports.append(
                    DiscoveredPort(
                        port_number=int(port_elem.get("portid", 0)),
                        protocol=port_elem.get("protocol", "tcp"),
                        state=state.get("state", "") if state is not None else "",
                        service_name=service.get("name", "") if service is not None else "",
                        product=service.get("product", "") if service is not None else "",
                        version=service.get("version", "") if service is not None else "",
                    )
                )

            hosts.append(
                DiscoveredHost(
                    ip_address=ip,
                    hostname=hostname,
                    mac_address=mac,
                    vendor=vendor,
                    os_guess=os_guess,
                    ports=ports,
                )
            )

        # Durée
        runstats = root.find("runstats/finished")
        duration = 0
        if runstats is not None:
            duration = int(runstats.get("elapsed", "0").split(".")[0])

        return NmapScanResult(
            success=True,
            target=target,
            hosts=hosts,
            raw_xml=xml_output,
            duration_seconds=duration,
        )
