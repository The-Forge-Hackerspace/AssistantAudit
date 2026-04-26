"""Service de generation de la synthese executive d'un audit.

La synthese agrege toutes les campagnes/assessments/results d'un audit
et expose les KPIs cles pour la page web et le rapport PDF.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.assessment import (
    AssessmentCampaign,
    ComplianceStatus,
    ControlResult,
)
from ..models.audit import Audit
from ..models.entreprise import Entreprise
from ..schemas.executive_summary import (
    ExecutiveSummary,
    Recommendation,
    SeverityBreakdown,
    StatusBreakdown,
    TopNonCompliance,
)

logger = logging.getLogger(__name__)

# Ordre de severite pour le tri (du plus critique au moins critique)
SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
    "unknown": 5,
}


class ExecutiveSummaryService:
    """Calcule la synthese executive d'un audit."""

    @staticmethod
    def _check_audit_access(
        db: Session, audit_id: int, user_id: int, is_admin: bool
    ) -> Audit:
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit non trouve")
        if not is_admin and audit.owner_id != user_id:
            raise HTTPException(status_code=404, detail="Audit non trouve")
        return audit

    @staticmethod
    def generate(
        db: Session, audit_id: int, user_id: int, is_admin: bool
    ) -> ExecutiveSummary:
        """Genere la synthese executive d'un audit.

        Renvoie un objet avec has_data=False si aucune evaluation n'a ete realisee.
        """
        audit = ExecutiveSummaryService._check_audit_access(
            db, audit_id, user_id, is_admin
        )
        entreprise = (
            db.query(Entreprise).filter(Entreprise.id == audit.entreprise_id).first()
            if audit.entreprise_id
            else None
        )

        # Charger toutes les campagnes de l'audit. Les chaines
        # campaign.assessments / assessment.results / result.control / assessment.equipement
        # sont configurees avec lazy="selectin" dans le modele.
        campaigns = (
            db.query(AssessmentCampaign)
            .filter(AssessmentCampaign.audit_id == audit_id)
            .all()
        )

        # Aplatir tous les results de toutes les campagnes
        all_results: list[ControlResult] = []
        equipement_ids: set[int] = set()
        assessment_count = 0
        for campaign in campaigns:
            for assessment in campaign.assessments:
                assessment_count += 1
                equipement_ids.add(assessment.equipement_id)
                all_results.extend(assessment.results)

        # Decompte par statut
        status_counts: dict[str, int] = defaultdict(int)
        # Decompte par severite -> statut
        severity_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Groupement par controle pour les non-conformites recurrentes
        # control_id -> {control, count, equipements}
        nc_by_control: dict[int, dict] = {}

        assessed_count = 0
        for r in all_results:
            status = r.status.value
            status_counts[status] += 1
            severity = r.control.severity.value if r.control else "unknown"
            severity_counts[severity]["total"] += 1
            severity_counts[severity][status] += 1

            if r.status not in (
                ComplianceStatus.NOT_ASSESSED,
                ComplianceStatus.NOT_APPLICABLE,
            ):
                assessed_count += 1

            # Aggreger uniquement les non-conformites pour le top
            if r.status == ComplianceStatus.NON_COMPLIANT and r.control:
                cid = r.control.id
                if cid not in nc_by_control:
                    nc_by_control[cid] = {
                        "control": r.control,
                        "count": 0,
                        "equipements": [],
                    }
                nc_by_control[cid]["count"] += 1
                eq = r.assessment.equipement if r.assessment else None
                if eq:
                    label = eq.hostname or eq.ip_address or f"Equipement {eq.id}"
                    if label not in nc_by_control[cid]["equipements"]:
                        nc_by_control[cid]["equipements"].append(label)

        # Score global : moyenne ponderee sur les results assesses
        global_score = None
        if assessed_count > 0:
            compliant = status_counts["compliant"]
            partial = status_counts["partially_compliant"]
            global_score = round((compliant + 0.5 * partial) / assessed_count * 100, 1)

        # Tri des non-conformites : severity rank asc puis count desc
        sorted_nc = sorted(
            nc_by_control.values(),
            key=lambda x: (
                SEVERITY_RANK.get(x["control"].severity.value, 99),
                -x["count"],
            ),
        )

        top_non_compliances = [
            TopNonCompliance(
                control_ref=item["control"].ref_id,
                title=item["control"].title,
                severity=item["control"].severity.value,
                occurrences=item["count"],
                affected_equipements=item["equipements"][:5],  # max 5 equips
            )
            for item in sorted_nc[:5]
        ]

        # Recommandations : 3 premiers de la liste avec remediation
        recommendations = [
            Recommendation(
                control_ref=item["control"].ref_id,
                title=item["control"].title,
                severity=item["control"].severity.value,
                remediation=item["control"].remediation,
                occurrences=item["count"],
            )
            for item in sorted_nc[:3]
        ]

        # Construire le breakdown par severite (cle = severite)
        by_severity = {}
        for sev, counts in severity_counts.items():
            by_severity[sev] = SeverityBreakdown(
                total=counts.get("total", 0),
                compliant=counts.get("compliant", 0),
                non_compliant=counts.get("non_compliant", 0),
                partially_compliant=counts.get("partially_compliant", 0),
                not_assessed=counts.get("not_assessed", 0),
                not_applicable=counts.get("not_applicable", 0),
            )

        return ExecutiveSummary(
            audit_id=audit.id,
            audit_name=audit.nom_projet,
            entreprise_name=entreprise.nom if entreprise else None,
            generated_at=datetime.now(timezone.utc),
            has_data=assessed_count > 0,
            global_score=global_score,
            total_evaluations=assessment_count,
            total_equipements=len(equipement_ids),
            total_controls_assessed=assessed_count,
            by_status=StatusBreakdown(
                compliant=status_counts.get("compliant", 0),
                non_compliant=status_counts.get("non_compliant", 0),
                partially_compliant=status_counts.get("partially_compliant", 0),
                not_applicable=status_counts.get("not_applicable", 0),
                not_assessed=status_counts.get("not_assessed", 0),
            ),
            by_severity=by_severity,
            top_non_compliances=top_non_compliances,
            recommendations=recommendations,
        )
