"""
Config Parser — OPNsense.

Parse les exports de configuration OPNsense (format XML).
Extrait : hostname, firmware, interfaces, règles de filtrage, constats de sécurité.
"""
import logging
from typing import Optional
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET

from ...schemas.scan import (
    ConfigAnalysisResult,
    FirewallRuleInfo,
    InterfaceInfo,
    SecurityFinding,
)
from .base import ConfigParserBase

logger = logging.getLogger(__name__)


class OPNsenseParser(ConfigParserBase):
    vendor = "opnsense"
    device_type = "firewall"

    def parse(self, content: str) -> ConfigAnalysisResult:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            logger.error("Erreur de parsing XML OPNsense: %s", exc)
            return ConfigAnalysisResult(
                vendor="OPNsense",
                device_type="firewall",
                hostname=None,
                firmware_version=None,
                serial_number=None,
                interfaces=[],
                firewall_rules=[],
                findings=[SecurityFinding(
                    severity="critical",
                    category="Parsing",
                    title="Fichier XML invalide",
                    description=f"Le fichier de configuration n'a pas pu être parsé : {exc}",
                    remediation="Vérifier que le fichier exporté est bien au format XML OPNsense.",
                )],
                summary={},
            )

        hostname = self._get_text(root, ".//system/hostname")
        domain = self._get_text(root, ".//system/domain")
        firmware = self._get_text(root, ".//system/firmware/version")
        if not firmware:
            firmware = self._get_text(root, ".//version")

        interfaces = self._parse_interfaces(root)
        rules = self._parse_firewall_rules(root)
        findings = self._analyze_security(root, interfaces, rules)

        full_hostname = hostname
        if hostname and domain:
            full_hostname = f"{hostname}.{domain}"

        return ConfigAnalysisResult(
            vendor="OPNsense",
            device_type="firewall",
            hostname=full_hostname,
            firmware_version=firmware,
            serial_number=None,
            interfaces=interfaces,
            firewall_rules=rules,
            findings=findings,
            summary={
                "total_interfaces": len(interfaces),
                "active_interfaces": len([i for i in interfaces if i.status == "up"]),
                "total_rules": len(rules),
                "allow_rules": len([r for r in rules if r.action == "pass"]),
                "block_rules": len([r for r in rules if r.action in ("block", "reject")]),
                "findings_by_severity": self._count_by_severity(findings),
            },
        )

    def _parse_interfaces(self, root: Element) -> list[InterfaceInfo]:
        """Parse la section <interfaces>."""
        interfaces: list[InterfaceInfo] = []
        iface_node = root.find(".//interfaces")
        if iface_node is None:
            return interfaces

        for child in iface_node:
            name = child.tag  # e.g. "lan", "wan", "opt1"
            descr = self._get_text(child, "descr") or name
            enable = child.find("enable")
            iface_status = "up" if enable is not None else "down"

            ip = self._get_text(child, "ipaddr")
            subnet_bits = self._get_text(child, "subnet")
            netmask = self._cidr_to_netmask(int(subnet_bits)) if subnet_bits and subnet_bits.isdigit() else None

            interfaces.append(InterfaceInfo(
                name=descr or name,
                ip_address=ip,
                netmask=netmask,
                vlan=None,
                status=iface_status,
                allowed_access=[],
                description=f"Interface {name}",
            ))

        return interfaces

    def _parse_firewall_rules(self, root: Element) -> list[FirewallRuleInfo]:
        """Parse la section <filter> dans <rules>."""
        rules: list[FirewallRuleInfo] = []
        filter_node = root.find(".//filter")
        if filter_node is None:
            return rules

        for idx, rule_el in enumerate(filter_node.findall("rule"), 1):
            rule_type = self._get_text(rule_el, "type") or "pass"
            disabled = rule_el.find("disabled") is not None

            src = self._get_text(rule_el, "source/any")
            if src is not None:
                src_addr = "any"
            else:
                src_addr = (
                    self._get_text(rule_el, "source/network")
                    or self._get_text(rule_el, "source/address")
                    or "?"
                )

            dst = self._get_text(rule_el, "destination/any")
            if dst is not None:
                dst_addr = "any"
            else:
                dst_addr = (
                    self._get_text(rule_el, "destination/network")
                    or self._get_text(rule_el, "destination/address")
                    or "?"
                )

            protocol = self._get_text(rule_el, "protocol") or "any"
            dst_port = self._get_text(rule_el, "destination/port")
            interface = self._get_text(rule_el, "interface")
            descr = self._get_text(rule_el, "descr")
            log = rule_el.find("log") is not None

            service = protocol
            if dst_port:
                service = f"{protocol}/{dst_port}"

            rules.append(FirewallRuleInfo(
                rule_id=str(idx),
                name=descr,
                source_interface=interface,
                dest_interface=None,
                source_address=src_addr,
                dest_address=dst_addr,
                service=service,
                action=rule_type,
                schedule=None,
                enabled=not disabled,
                log_traffic=log,
            ))

        return rules

    def _analyze_security(
        self,
        root: Element,
        interfaces: list[InterfaceInfo],
        rules: list[FirewallRuleInfo],
    ) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []

        # ── 1. Règles any-any ──
        for rule in rules:
            if not rule.enabled or rule.action != "pass":
                continue
            if rule.source_address == "any" and rule.dest_address == "any":
                svc = rule.service or "any"
                if svc in ("any", "any/any"):
                    findings.append(SecurityFinding(
                        severity="critical",
                        category="Règles de filtrage",
                        title=f"Règle #{rule.rule_id} : any→any PASS",
                        description=(
                            f"La règle '{rule.name or rule.rule_id}' autorise tout le trafic. "
                            "Cela désactive le filtrage pour ce flux."
                        ),
                        remediation="Restreindre la règle aux services et adresses nécessaires.",
                    ))

        # ── 2. Règles sans journalisation ──
        rules_no_log = [r for r in rules if r.enabled and r.action == "pass" and not r.log_traffic]
        if rules_no_log:
            findings.append(SecurityFinding(
                severity="medium",
                category="Journalisation",
                title=f"{len(rules_no_log)} règle(s) PASS sans journalisation",
                description=(
                    f"Règles concernées : "
                    f"{', '.join(r.rule_id for r in rules_no_log[:10])}"
                    f"{'...' if len(rules_no_log) > 10 else ''}."
                ),
                remediation="Activer la journalisation sur les règles critiques.",
            ))

        # ── 3. SSH admin désactivé → pas un finding, mais si Telnet/HTTP dans webgui ──
        webgui = root.find(".//system/webgui")
        if webgui is not None:
            protocol = self._get_text(webgui, "protocol")
            if protocol and protocol.lower() == "http":
                findings.append(SecurityFinding(
                    severity="high",
                    category="Administration",
                    title="Interface web en HTTP (non chiffré)",
                    description=(
                        "L'interface d'administration OPNsense est configurée en HTTP. "
                        "Les identifiants transitent en clair."
                    ),
                    remediation="Configurer HTTPS pour l'interface d'administration.",
                ))

        # ── 4. DNS resolver ──
        dns_servers = root.findall(".//system/dnsserver")
        if not dns_servers:
            findings.append(SecurityFinding(
                severity="low",
                category="Réseau",
                title="Aucun serveur DNS configuré",
                description="Aucun serveur DNS n'est configuré dans la configuration système.",
                remediation="Configurer au moins deux serveurs DNS fiables.",
            ))

        # ── 5. Utilisateur admin par défaut ──
        for user in root.findall(".//system/user"):
            username = self._get_text(user, "name")
            if username == "root":
                findings.append(SecurityFinding(
                    severity="medium",
                    category="Authentification",
                    title="Utilisateur 'root' présent",
                    description=(
                        "Le compte root par défaut est toujours actif. "
                        "Il est recommandé de créer des comptes nominatifs."
                    ),
                    remediation="Créer des comptes nominatifs et limiter l'usage de root.",
                ))
                break

        return findings

    @staticmethod
    def _get_text(element: Element, path: str) -> Optional[str]:
        node = element.find(path)
        if node is not None and node.text:
            return node.text.strip()
        return None

    @staticmethod
    def _cidr_to_netmask(bits: int) -> str:
        mask = (0xFFFFFFFF >> (32 - bits)) << (32 - bits)
        return f"{(mask >> 24) & 0xFF}.{(mask >> 16) & 0xFF}.{(mask >> 8) & 0xFF}.{mask & 0xFF}"

    def _count_by_severity(self, findings: list[SecurityFinding]) -> dict:
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts
