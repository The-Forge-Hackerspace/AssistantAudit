"""
Service Monkey365 — Simulation de scan pour développement et tests.
Le flux de scan réel utilise Monkey365ScanService (monkey365_scan_service.py).
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from ..services.assessment_service import AssessmentService
from ..tools.monkey365_runner.mapper import Monkey365Mapper
from ..tools.monkey365_runner.parser import Monkey365Parser

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Résultat complet d'un scan + mapping"""

    scan_id: str
    status: str  # success | error | timeout
    findings_count: int = 0
    mapped_count: int = 0
    unmapped_count: int = 0
    error: Optional[str] = None
    mapping_details: list[dict] = field(default_factory=list)
    manual_controls: list[dict] = field(default_factory=list)


class Monkey365Service:
    """
    Service de simulation Monkey365 pour développement et tests.
    Pour le flux de scan réel, utiliser Monkey365ScanService.
    """

    @staticmethod
    def simulate_scan(
        db: Session,
        assessment_id: int,
        simulated_findings: list[dict],
    ) -> ScanResult:
        """
        Mode simulation / test : injecte des findings manuellement
        sans exécuter Monkey365 (utile pour le développement).
        """
        scan_id = f"sim_{uuid.uuid4().hex[:8]}"

        assessment = AssessmentService.get_assessment(db, assessment_id)
        if not assessment:
            return ScanResult(scan_id=scan_id, status="error", error=f"Assessment {assessment_id} introuvable")

        findings = Monkey365Parser.parse_raw_results(simulated_findings)

        mapping_results = Monkey365Mapper.map_findings_to_assessment(db, assessment, findings, assessed_by="simulation")
        db.commit()
        manual_controls = Monkey365Mapper.get_unmapped_controls(assessment)

        return ScanResult(
            scan_id=scan_id,
            status="success",
            findings_count=len(findings),
            mapped_count=len(mapping_results),
            unmapped_count=len(findings) - len(mapping_results),
            mapping_details=[
                {
                    "control_ref_id": m.control_ref_id,
                    "rule_id": m.monkey365_rule_id,
                    "status": m.new_status,
                }
                for m in mapping_results
            ],
            manual_controls=manual_controls,
        )
