"""
Monkey365 Mapper — Mappe les findings Monkey365 vers les contrôles
du référentiel AssistantAudit pour pré-remplir les résultats d'audit.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from ...models.assessment import Assessment, ControlResult, ComplianceStatus
from ...models.framework import Control
from .parser import Monkey365Finding

logger = logging.getLogger(__name__)


@dataclass
class MappingResult:
    """Résultat du mapping d'un finding Monkey365 vers un ControlResult"""
    control_result_id: int
    control_ref_id: str
    monkey365_rule_id: str
    old_status: str
    new_status: str
    evidence: str
    mapped: bool = True


class Monkey365Mapper:
    """
    Mappe les findings Monkey365 vers les ControlResult d'un Assessment.

    Le mapping se fait via le champ `engine_rule_id` des contrôles du framework,
    qui correspond au `rule_id` des findings Monkey365.
    """

    # Mapping statut Monkey365 → ComplianceStatus
    STATUS_MAP = {
        "compliant": ComplianceStatus.COMPLIANT,
        "non_compliant": ComplianceStatus.NON_COMPLIANT,
        "partially_compliant": ComplianceStatus.PARTIALLY_COMPLIANT,
        "not_assessed": ComplianceStatus.NOT_ASSESSED,
        "info": ComplianceStatus.NOT_ASSESSED,
    }

    @classmethod
    def map_findings_to_assessment(
        cls,
        db: Session,
        assessment: Assessment,
        findings: list[Monkey365Finding],
        assessed_by: str = "monkey365",
    ) -> list[MappingResult]:
        """
        Mappe les findings Monkey365 → ControlResult pour un assessment.

        Pour chaque finding :
        1. Cherche le ControlResult dont `control.engine_rule_id` == `finding.rule_id`
        2. Met à jour le statut, l'evidence, et marque comme auto-assessed
        """
        from datetime import datetime, timezone

        # Construire l'index rule_id → ControlResult
        rule_index: dict[str, ControlResult] = {}
        for result in assessment.results:
            if result.control and result.control.engine_rule_id:
                rule_index[result.control.engine_rule_id] = result

        mapping_results: list[MappingResult] = []
        mapped_count = 0
        unmapped_rules: list[str] = []
        now = datetime.now(timezone.utc)

        for finding in findings:
            control_result = rule_index.get(finding.rule_id)

            if not control_result:
                unmapped_rules.append(finding.rule_id)
                continue

            old_status = control_result.status.value
            new_status_enum = cls.STATUS_MAP.get(
                finding.status_text, ComplianceStatus.NOT_ASSESSED
            )

            # Construire l'evidence avec les détails
            evidence_parts = []
            if finding.output:
                evidence_parts.append(f"[Auto] {finding.output}")
            if finding.affected_resources:
                resources_str = ", ".join(finding.affected_resources[:10])
                evidence_parts.append(f"Ressources: {resources_str}")
            if finding.remediation:
                evidence_parts.append(f"Remediation: {finding.remediation}")

            evidence = "\n".join(evidence_parts) if evidence_parts else f"[Auto] {finding.level}"

            # Mettre à jour le ControlResult
            control_result.status = new_status_enum
            control_result.evidence = evidence[:4000]  # limiter la taille
            control_result.auto_result = finding.output[:2000] if finding.output else None
            control_result.is_auto_assessed = True
            control_result.assessed_by = assessed_by
            control_result.assessed_at = now

            if finding.remediation and new_status_enum != ComplianceStatus.COMPLIANT:
                control_result.remediation_note = finding.remediation[:2000]

            mapping_results.append(MappingResult(
                control_result_id=control_result.id,
                control_ref_id=control_result.control.ref_id if control_result.control else "?",
                monkey365_rule_id=finding.rule_id,
                old_status=old_status,
                new_status=new_status_enum.value,
                evidence=evidence[:200],
            ))
            mapped_count += 1

        db.commit()

        logger.info(
            f"Monkey365 Mapper : {mapped_count}/{len(findings)} findings mappés "
            f"sur assessment #{assessment.id}"
        )
        if unmapped_rules:
            logger.warning(
                f"  Règles non mappées ({len(unmapped_rules)}) : "
                f"{', '.join(unmapped_rules[:10])}"
            )

        return mapping_results

    @classmethod
    def get_unmapped_controls(cls, assessment: Assessment) -> list[dict]:
        """
        Retourne la liste des contrôles du framework qui n'ont pas de
        mapping engine_rule_id (contrôles manuels à remplir par l'auditeur).
        """
        unmapped = []
        for result in assessment.results:
            if result.control and not result.control.engine_rule_id:
                unmapped.append({
                    "control_result_id": result.id,
                    "control_ref_id": result.control.ref_id,
                    "control_title": result.control.title,
                    "check_type": result.control.check_type.value,
                    "status": result.status.value,
                })
        return unmapped
