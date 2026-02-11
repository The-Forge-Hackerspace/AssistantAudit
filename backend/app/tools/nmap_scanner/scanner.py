"""
Scanner Nmap — outil de découverte réseau intégré.
"""
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Optional

import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)


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
                return NmapScanResult(
                    success=False, target=target, error=process.stderr
                )

            result = self._parse_xml(process.stdout, target)
            return result

        except subprocess.TimeoutExpired:
            return NmapScanResult(
                success=False, target=target, error=f"Timeout après {self.timeout}s"
            )
        except FileNotFoundError:
            return NmapScanResult(
                success=False, target=target, error="Nmap non installé ou introuvable dans le PATH"
            )

    def _build_args(
        self, target: str, scan_type: str, extra_args: Optional[list[str]]
    ) -> list[str]:
        """Construit la ligne de commande Nmap"""
        base = ["nmap", "-oX", "-"]  # sortie XML sur stdout

        type_args = {
            "discovery": ["-sn"],  # Ping scan uniquement
            "port_scan": ["-sV", "--top-ports", "1000"],
            "full": ["-sV", "-sC", "-O", "-p-"],
            "custom": [],  # Pas d'args par défaut, tout vient de extra_args
        }
        base.extend(type_args.get(scan_type, ["-sn"]))

        if extra_args:
            base.extend(extra_args)

        base.append(target)
        return base

    def _parse_xml(self, xml_output: str, target: str) -> NmapScanResult:
        """Parse la sortie XML de Nmap"""
        try:
            root = ET.fromstring(xml_output)
        except Exception as e:
            return NmapScanResult(
                success=False, target=target, error=f"Erreur parsing XML : {e}"
            )

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
                ports.append(DiscoveredPort(
                    port_number=int(port_elem.get("portid", 0)),
                    protocol=port_elem.get("protocol", "tcp"),
                    state=state.get("state", "") if state is not None else "",
                    service_name=service.get("name", "") if service is not None else "",
                    product=service.get("product", "") if service is not None else "",
                    version=service.get("version", "") if service is not None else "",
                ))

            hosts.append(DiscoveredHost(
                ip_address=ip,
                hostname=hostname,
                mac_address=mac,
                vendor=vendor,
                os_guess=os_guess,
                ports=ports,
            ))

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
