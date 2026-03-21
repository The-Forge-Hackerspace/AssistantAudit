"""
Service Monkey365 — Orchestre le cycle complet :
  1. Lancer un scan Monkey365
  2. Parser les résultats JSON
  3. Mapper les findings vers les ControlResults d'un assessment
"""
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from ..models.assessment import Assessment
from ..services.assessment_service import AssessmentService
from ..tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor
from ..tools.monkey365_runner.config import Monkey365AuthMode, M365Provider
from ..tools.monkey365_runner.parser import Monkey365Parser, Monkey365Finding
from ..tools.monkey365_runner.mapper import Monkey365Mapper, MappingResult

logger = logging.getLogger(__name__)


@dataclass
class ScanRequest:
    """Paramètres d'un scan M365"""
    tenant_id: str
    client_id: str
    client_secret: str
    auth_method: str = "client_credentials"
    provider: str = "Microsoft365"
    plugins: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Résultat complet d'un scan + mapping"""
    scan_id: str
    status: str                           # success | error | timeout
    findings_count: int = 0
    mapped_count: int = 0
    unmapped_count: int = 0
    error: Optional[str] = None
    mapping_details: list[dict] = field(default_factory=list)
    manual_controls: list[dict] = field(default_factory=list)


class Monkey365Service:
    """
    Service haut-niveau pour exécuter un scan M365 et intégrer
    les résultats dans un assessment AssistantAudit.
    """

    @staticmethod
    def run_scan_and_map(
        db: Session,
        assessment_id: int,
        scan_request: ScanRequest,
        monkey365_path: Optional[str] = None,
    ) -> ScanResult:
        """
        Workflow complet :
        1. Valide l'assessment (doit utiliser un framework avec engine=monkey365)
        2. Lance Monkey365
        3. Parse les résultats
        4. Mappe vers les ControlResults
        """
        scan_id = f"m365_{uuid.uuid4().hex[:8]}"

        # 1. Valider l'assessment
        assessment = AssessmentService.get_assessment(db, assessment_id)
        if not assessment:
            return ScanResult(
                scan_id=scan_id, status="error",
                error=f"Assessment {assessment_id} introuvable"
            )

        framework = assessment.framework
        if not framework or framework.engine != "monkey365":
            return ScanResult(
                scan_id=scan_id, status="error",
                error=f"Le framework '{framework.ref_id if framework else '?'}' "
                      f"n'utilise pas le moteur monkey365"
            )

        # 2. Configurer et lancer Monkey365
        config = Monkey365Config(
            provider=M365Provider(scan_request.provider),
            auth_mode=Monkey365AuthMode(scan_request.auth_method),
            tenant_id=scan_request.tenant_id,
            client_id=scan_request.client_id,
            client_secret=scan_request.client_secret,
            plugins=scan_request.plugins,
        )

        try:
            executor = Monkey365Executor(config, monkey365_path)
        except FileNotFoundError as e:
            return ScanResult(
                scan_id=scan_id, status="error",
                error=str(e)
            )

        logger.info(f"Lancement scan Monkey365 [{scan_id}] pour assessment #{assessment_id}")
        raw_result = executor.run_scan(scan_id)

        if raw_result["status"] != "success":
            return ScanResult(
                scan_id=scan_id,
                status=raw_result["status"],
                error=raw_result.get("error", "Erreur inconnue"),
            )

        # 3. Parser les résultats
        raw_findings = raw_result.get("results", [])
        findings: list[Monkey365Finding] = Monkey365Parser.parse_raw_results(raw_findings)

        # 4. Mapper vers l'assessment
        mapping_results: list[MappingResult] = Monkey365Mapper.map_findings_to_assessment(
            db, assessment, findings, assessed_by="monkey365"
        )

        # 5. Identifier les contrôles manuels restants
        manual_controls = Monkey365Mapper.get_unmapped_controls(assessment)

        logger.info(
            f"Scan [{scan_id}] terminé : {len(findings)} findings, "
            f"{len(mapping_results)} mappés, "
            f"{len(manual_controls)} contrôles manuels restants"
        )

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
            return ScanResult(
                scan_id=scan_id, status="error",
                error=f"Assessment {assessment_id} introuvable"
            )

        # Parser les findings simulés
        findings = Monkey365Parser.parse_raw_results(simulated_findings)

        # Mapper
        mapping_results = Monkey365Mapper.map_findings_to_assessment(
            db, assessment, findings, assessed_by="simulation"
        )
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
