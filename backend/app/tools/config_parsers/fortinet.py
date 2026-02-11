"""
Config Parser — FortiGate (Fortinet).

Parse les exports de configuration FortiGate (format texte).
Extrait : hostname, firmware, interfaces, règles de filtrage, constats de sécurité.
"""
import re
import logging
from typing import Optional

from .base import ConfigParserBase
from ...schemas.scan import (
    ConfigAnalysisResult,
    InterfaceInfo,
    FirewallRuleInfo,
    SecurityFinding,
)

logger = logging.getLogger(__name__)


class FortinetParser(ConfigParserBase):
    vendor = "fortinet"
    device_type = "firewall"

    def parse(self, content: str) -> ConfigAnalysisResult:
        hostname = self._extract_hostname(content)
        firmware = self._extract_firmware(content)
        serial = self._extract_serial(content)
        interfaces = self._parse_interfaces(content)
        rules = self._parse_firewall_rules(content)
        findings = self._analyze_security(content, interfaces, rules)

        return ConfigAnalysisResult(
            vendor="Fortinet FortiGate",
            device_type="firewall",
            hostname=hostname,
            firmware_version=firmware,
            serial_number=serial,
            interfaces=interfaces,
            firewall_rules=rules,
            findings=findings,
            summary={
                "total_interfaces": len(interfaces),
                "active_interfaces": len([i for i in interfaces if i.status == "up"]),
                "total_rules": len(rules),
                "allow_rules": len([r for r in rules if r.action == "accept"]),
                "deny_rules": len([r for r in rules if r.action == "deny"]),
                "findings_by_severity": self._count_by_severity(findings),
            },
        )

    def _extract_hostname(self, content: str) -> Optional[str]:
        match = re.search(r'set hostname\s+"?([^"\n]+)"?', content)
        return match.group(1).strip() if match else None

    def _extract_firmware(self, content: str) -> Optional[str]:
        match = re.search(r'#config-version=([^\s:]+)', content)
        if match:
            return match.group(1)
        match = re.search(r'set firmware\s+"?([^"\n]+)', content)
        return match.group(1).strip() if match else None

    def _extract_serial(self, content: str) -> Optional[str]:
        match = re.search(r'#conf_file_ver=.*\n#buildno=.*\n#global_vdom=.*\n.*\n.*SN:\s*(\S+)', content)
        if not match:
            match = re.search(r'set serial-number\s+"?(\S+)"?', content)
        return match.group(1) if match else None

    def _parse_interfaces(self, content: str) -> list[InterfaceInfo]:
        """Parse 'config system interface' blocks."""
        interfaces: list[InterfaceInfo] = []
        iface_block = self._extract_block(content, "config system interface")
        if not iface_block:
            return interfaces

        # Split by 'edit' ... 'next'
        for match in re.finditer(
            r'edit\s+"([^"]+)"(.*?)(?=\n\s*edit\s+"|\nend)', iface_block, re.DOTALL
        ):
            name = match.group(1)
            block = match.group(2)

            ip_match = re.search(r'set ip\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)', block)
            ip = ip_match.group(1) if ip_match else None
            netmask = ip_match.group(2) if ip_match else None

            vlan_match = re.search(r'set vlanid\s+(\d+)', block)
            vlan = int(vlan_match.group(1)) if vlan_match else None

            status_match = re.search(r'set status\s+(\w+)', block)
            iface_status = "up"
            if status_match and status_match.group(1) == "down":
                iface_status = "down"

            access_match = re.search(r'set allowaccess\s+(.+)', block)
            allowed = access_match.group(1).strip().split() if access_match else []

            desc_match = re.search(r'set description\s+"([^"]*)"', block)
            description = desc_match.group(1) if desc_match else None

            interfaces.append(InterfaceInfo(
                name=name,
                ip_address=ip,
                netmask=netmask,
                vlan=vlan,
                status=iface_status,
                allowed_access=allowed,
                description=description,
            ))

        return interfaces

    def _parse_firewall_rules(self, content: str) -> list[FirewallRuleInfo]:
        """Parse 'config firewall policy' blocks."""
        rules: list[FirewallRuleInfo] = []
        policy_block = self._extract_block(content, "config firewall policy")
        if not policy_block:
            return rules

        for match in re.finditer(
            r'edit\s+(\d+)(.*?)(?=\n\s*edit\s+\d+|\nend)', policy_block, re.DOTALL
        ):
            rule_id = match.group(1)
            block = match.group(2)

            def get_val(key: str) -> Optional[str]:
                m = re.search(rf'set {key}\s+"?([^"\n]+)"?', block)
                return m.group(1).strip() if m else None

            name = get_val("name")
            srcintf = get_val("srcintf")
            dstintf = get_val("dstintf")
            srcaddr = get_val("srcaddr")
            dstaddr = get_val("dstaddr")
            service = get_val("service")
            action = get_val("action") or "deny"
            schedule = get_val("schedule")

            status_match = re.search(r'set status\s+(\w+)', block)
            enabled = True
            if status_match and status_match.group(1) == "disable":
                enabled = False

            log_match = re.search(r'set logtraffic\s+(\w+)', block)
            log_traffic = log_match is not None and log_match.group(1) != "disable"

            rules.append(FirewallRuleInfo(
                rule_id=rule_id,
                name=name,
                source_interface=srcintf,
                dest_interface=dstintf,
                source_address=srcaddr,
                dest_address=dstaddr,
                service=service,
                action=action,
                schedule=schedule,
                enabled=enabled,
                log_traffic=log_traffic,
            ))

        return rules

    def _analyze_security(
        self,
        content: str,
        interfaces: list[InterfaceInfo],
        rules: list[FirewallRuleInfo],
    ) -> list[SecurityFinding]:
        """Analyse de sécurité automatique sur la configuration."""
        findings: list[SecurityFinding] = []

        # ── 1. Règles any-any ──
        for rule in rules:
            if not rule.enabled:
                continue
            is_any_src = rule.source_address in ("all", "any", "0.0.0.0/0")
            is_any_dst = rule.dest_address in ("all", "any", "0.0.0.0/0")
            is_any_svc = rule.service in ("ALL", "any")

            if is_any_src and is_any_dst and is_any_svc and rule.action == "accept":
                findings.append(SecurityFinding(
                    severity="critical",
                    category="Règles de filtrage",
                    title=f"Règle #{rule.rule_id} : any-any-any ACCEPT",
                    description=(
                        f"La règle '{rule.name or rule.rule_id}' autorise tout "
                        f"le trafic de '{rule.source_interface}' vers '{rule.dest_interface}'. "
                        "Cela désactive effectivement le pare-feu pour ce flux."
                    ),
                    remediation="Restreindre la règle aux services et adresses strictement nécessaires.",
                ))
            elif is_any_svc and rule.action == "accept":
                findings.append(SecurityFinding(
                    severity="high",
                    category="Règles de filtrage",
                    title=f"Règle #{rule.rule_id} : service ALL autorisé",
                    description=(
                        f"La règle '{rule.name or rule.rule_id}' autorise tous les services. "
                        "Cela expose la destination à tous les protocoles."
                    ),
                    remediation="Limiter aux seuls services nécessaires (HTTP, HTTPS, SSH, etc.).",
                ))

        # ── 2. Règles sans log ──
        rules_no_log = [r for r in rules if r.enabled and r.action == "accept" and not r.log_traffic]
        if rules_no_log:
            findings.append(SecurityFinding(
                severity="medium",
                category="Journalisation",
                title=f"{len(rules_no_log)} règle(s) ACCEPT sans journalisation",
                description=(
                    f"Les règles suivantes autorisent du trafic sans le journaliser : "
                    f"{', '.join(r.rule_id for r in rules_no_log[:10])}"
                    f"{'...' if len(rules_no_log) > 10 else ''}. "
                    "Sans logs, il est impossible de tracer les activités suspectes."
                ),
                remediation="Activer 'set logtraffic all' sur les règles critiques.",
            ))

        # ── 3. HTTP sur les interfaces d'administration ──
        for iface in interfaces:
            if "http" in iface.allowed_access and "https" not in iface.allowed_access:
                findings.append(SecurityFinding(
                    severity="high",
                    category="Administration",
                    title=f"Interface '{iface.name}' : accès HTTP non chiffré",
                    description=(
                        f"L'interface '{iface.name}' ({iface.ip_address}) autorise l'accès "
                        "HTTP en clair pour l'administration. Les identifiants transitent sans chiffrement."
                    ),
                    remediation="Supprimer HTTP de 'set allowaccess' et n'autoriser que HTTPS.",
                ))
            if "http" in iface.allowed_access and "https" in iface.allowed_access:
                findings.append(SecurityFinding(
                    severity="medium",
                    category="Administration",
                    title=f"Interface '{iface.name}' : HTTP et HTTPS activés",
                    description=(
                        f"L'interface '{iface.name}' autorise HTTP et HTTPS. "
                        "HTTP devrait être désactivé pour forcer l'usage de HTTPS."
                    ),
                    remediation="Supprimer HTTP de 'set allowaccess'.",
                ))

        # ── 4. Telnet activé ──
        for iface in interfaces:
            if "telnet" in iface.allowed_access:
                findings.append(SecurityFinding(
                    severity="high",
                    category="Administration",
                    title=f"Interface '{iface.name}' : Telnet activé",
                    description=(
                        f"L'interface '{iface.name}' autorise Telnet, un protocole non chiffré. "
                        "Les identifiants et commandes sont visibles sur le réseau."
                    ),
                    remediation="Désactiver Telnet et n'utiliser que SSH.",
                ))

        # ── 5. Ping sur interfaces WAN ──
        for iface in interfaces:
            if "ping" in iface.allowed_access and any(
                kw in iface.name.lower() for kw in ["wan", "internet", "outside", "ext"]
            ):
                findings.append(SecurityFinding(
                    severity="low",
                    category="Réseau",
                    title=f"Interface WAN '{iface.name}' : ICMP (ping) activé",
                    description=(
                        f"L'interface WAN '{iface.name}' répond au ping. "
                        "Cela peut faciliter la reconnaissance réseau."
                    ),
                    remediation="Désactiver le ping sur les interfaces exposées à Internet.",
                ))

        # ── 6. Firmware check via version string ──
        firmware_match = re.search(r'#config-version=FG\w+-(\d+\.\d+\.\d+)', content)
        if firmware_match:
            version = firmware_match.group(1)
            major, minor, patch = [int(x) for x in version.split(".")]
            # Simple heuristic: versions < 7.4 are considered outdated
            if major < 7 or (major == 7 and minor < 4):
                findings.append(SecurityFinding(
                    severity="high",
                    category="Maintenance",
                    title=f"FortiOS {version} possiblement obsolète",
                    description=(
                        f"La version FortiOS {version} peut contenir des vulnérabilités connues. "
                        "FortiGate recommande la mise à jour vers les dernières versions stables."
                    ),
                    remediation="Planifier une mise à jour vers la dernière version stable de FortiOS.",
                    reference="https://docs.fortinet.com/product/fortigate/",
                ))

        # ── 7. VPN settings ──
        if "config vpn ipsec phase1-interface" in content:
            # Check for weak encryption
            weak_crypto = re.findall(
                r'set proposal\s+.*?(des|3des|md5).*?\n', content, re.IGNORECASE
            )
            if weak_crypto:
                findings.append(SecurityFinding(
                    severity="high",
                    category="VPN",
                    title="Algorithmes cryptographiques faibles dans le VPN",
                    description=(
                        "Des algorithmes obsolètes (DES, 3DES, MD5) sont utilisés dans "
                        "la configuration VPN IPsec. Ces algorithmes sont considérés comme cassés."
                    ),
                    remediation="Utiliser AES-256 + SHA-256/SHA-512 pour les tunnels VPN.",
                ))

        # ── 8. SNMP community par défaut ──
        if re.search(r'set name\s+"public"', content):
            findings.append(SecurityFinding(
                severity="high",
                category="SNMP",
                title="Community SNMP 'public' détectée",
                description=(
                    "La community SNMP par défaut 'public' est configurée. "
                    "Cela permet à quiconque de lire les informations SNMP de l'équipement."
                ),
                remediation="Changer la community SNMP et restreindre l'accès par IP source.",
            ))

        return findings

    def _extract_block(self, content: str, block_name: str) -> Optional[str]:
        """Extrait un bloc 'config ... end' de la configuration."""
        pattern = rf'^{re.escape(block_name)}\s*\n(.*?)^end\s*$'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        return match.group(1) if match else None

    def _count_by_severity(self, findings: list[SecurityFinding]) -> dict:
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts
