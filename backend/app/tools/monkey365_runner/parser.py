"""
Monkey365 Result Parser — Parse les résultats JSON de Monkey365
et les convertit en structure normalisée pour AssistantAudit.
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Monkey365Finding:
    """Résultat normalisé d'un check Monkey365"""
    rule_id: str                         # identifiant de la règle Monkey365
    title: str
    description: str = ""
    level: str = "info"                   # Good | Warning | Fail | Info | Manual
    severity: str = "medium"              # critical | high | medium | low | info
    status_text: str = ""                 # texte brut du statut
    output: str = ""                      # sortie brute du check
    affected_resources: list[str] = field(default_factory=list)
    remediation: str = ""
    rationale: str = ""
    cis_reference: Optional[str] = None
    raw: dict = field(default_factory=dict)


class Monkey365Parser:
    """
    Parse les fichiers JSON générés par Monkey365 et retourne
    une liste de Monkey365Finding normalisés.
    """

    # Mapping du niveau Monkey365 → statut normalisé
    LEVEL_MAP = {
        "Good": "compliant",
        "Pass": "compliant",
        "PASS": "compliant",
        "Warning": "partially_compliant",
        "WARN": "partially_compliant",
        "Fail": "non_compliant",
        "FAIL": "non_compliant",
        "Info": "info",
        "INFO": "info",
        "Manual": "not_assessed",
        "MANUAL": "not_assessed",
    }

    @classmethod
    def parse_output_directory(cls, output_dir: str | Path) -> list[Monkey365Finding]:
        """Parse tous les JSON d'un répertoire de sortie Monkey365"""
        output_dir = Path(output_dir)
        findings: list[Monkey365Finding] = []

        if not output_dir.exists():
            logger.warning(f"Répertoire de sortie Monkey365 inexistant : {output_dir}")
            return findings

        for json_file in output_dir.rglob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                parsed = cls._parse_json_data(data, source_file=json_file.name)
                findings.extend(parsed)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Erreur parsing {json_file.name}: {e}")
                continue

        logger.info(f"Monkey365 parser : {len(findings)} findings extraits de {output_dir}")
        return findings

    @classmethod
    def parse_json_file(cls, json_path: str | Path) -> list[Monkey365Finding]:
        """Parse un seul fichier JSON Monkey365"""
        json_path = Path(json_path)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return cls._parse_json_data(data, source_file=json_path.name)

    @classmethod
    def parse_raw_results(cls, raw_results: list[dict]) -> list[Monkey365Finding]:
        """Parse une liste brute de résultats (depuis l'executor)"""
        findings = []
        for item in raw_results:
            finding = cls._parse_single_finding(item)
            if finding:
                findings.append(finding)
        return findings

    @classmethod
    def _parse_json_data(cls, data, source_file: str = "") -> list[Monkey365Finding]:
        """Parse une structure JSON (list ou dict)"""
        findings = []

        if isinstance(data, list):
            for item in data:
                f = cls._parse_single_finding(item)
                if f:
                    findings.append(f)
        elif isinstance(data, dict):
            # Monkey365 peut produire un dict avec une clé englobante
            if "rules" in data:
                for item in data["rules"]:
                    f = cls._parse_single_finding(item)
                    if f:
                        findings.append(f)
            elif "findings" in data:
                for item in data["findings"]:
                    f = cls._parse_single_finding(item)
                    if f:
                        findings.append(f)
            else:
                f = cls._parse_single_finding(data)
                if f:
                    findings.append(f)

        return findings

    @classmethod
    def _parse_single_finding(cls, item: dict) -> Optional[Monkey365Finding]:
        """Parse un résultat individuel Monkey365"""
        if not isinstance(item, dict):
            return None

        # Monkey365 utilise plusieurs schémas de clés selon la version
        rule_id = (
            item.get("idSuffix")
            or item.get("ruleId")
            or item.get("id")
            or item.get("checkName")
            or ""
        )
        if not rule_id:
            return None

        title = (
            item.get("title")
            or item.get("checkName")
            or item.get("displayName")
            or rule_id
        )

        level = (
            item.get("level")
            or item.get("status")
            or item.get("result")
            or "Info"
        )

        severity = item.get("severity", "medium")
        if isinstance(severity, dict):
            severity = severity.get("level", "medium")

        # Ressources affectées
        resources = (
            item.get("affectedResources")
            or item.get("resources")
            or item.get("resourceName")
            or []
        )
        if isinstance(resources, str):
            resources = [resources]

        # Références CIS
        refs = item.get("references", {})
        cis_ref = None
        if isinstance(refs, dict):
            cis_ref = refs.get("cis") or refs.get("CIS")
        elif isinstance(refs, str):
            cis_ref = refs if "CIS" in refs.upper() else None

        # Output / evidence
        output = item.get("output") or item.get("rawData") or item.get("details") or ""
        if isinstance(output, (dict, list)):
            output = json.dumps(output, indent=2, default=str)

        return Monkey365Finding(
            rule_id=rule_id,
            title=title,
            description=item.get("description", ""),
            level=level,
            severity=str(severity).lower(),
            status_text=cls.LEVEL_MAP.get(level, "not_assessed"),
            output=str(output)[:5000],  # limiter la taille
            affected_resources=resources[:50],
            remediation=item.get("remediation", item.get("rationale", "")),
            rationale=item.get("rationale", ""),
            cis_reference=cis_ref,
            raw=item,
        )

    @classmethod
    def normalize_status(cls, level: str) -> str:
        """Convertit un niveau Monkey365 en ComplianceStatus"""
        return cls.LEVEL_MAP.get(level, "not_assessed")
