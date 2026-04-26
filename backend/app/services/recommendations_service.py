"""Service de generation des recommandations exhaustives d'un audit (TOS-25 section 5).

Groupe les non-conformites par controle, trie par severite, et expose la liste
complete pour le rapport PDF (section recommendations) et la page web.
"""

import logging
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.assessment import (
    AssessmentCampaign,
    ComplianceStatus,
)
from ..models.audit import Audit
from ..schemas.recommendations import RecommendationDetail, RecommendationsList

logger = logging.getLogger(__name__)

# Ordre de severite (du plus critique au moins critique)
SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
    "unknown": 5,
}


class RecommendationsService:
    """Calcule la liste exhaustive des recommandations d'un audit."""

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
    ) -> RecommendationsList:
        """Liste exhaustive des recommandations groupees par severite.

        Une recommandation = un controle non-conforme aggrege sur ses occurrences.
        Tri intra-severite : nombre d'occurrences decroissant.
        """
        RecommendationsService._check_audit_access(db, audit_id, user_id, is_admin)

        campaigns = (
            db.query(AssessmentCampaign)
            .filter(AssessmentCampaign.audit_id == audit_id)
            .all()
        )

        # control_id -> {control, count, equipements}
        nc_by_control: dict[int, dict] = {}
        for campaign in campaigns:
            for assessment in campaign.assessments:
                for r in assessment.results:
                    if r.status != ComplianceStatus.NON_COMPLIANT or not r.control:
                        continue
                    cid = r.control.id
                    if cid not in nc_by_control:
                        nc_by_control[cid] = {
                            "control": r.control,
                            "count": 0,
                            "equipements": [],
                        }
                    nc_by_control[cid]["count"] += 1
                    eq = assessment.equipement
                    if eq:
                        label = eq.hostname or eq.ip_address or f"Equipement {eq.id}"
                        if label not in nc_by_control[cid]["equipements"]:
                            nc_by_control[cid]["equipements"].append(label)

        # Construire les details et grouper par severite
        by_severity: dict[str, list[RecommendationDetail]] = defaultdict(list)
        for item in nc_by_control.values():
            ctrl = item["control"]
            sev = ctrl.severity.value
            detail = RecommendationDetail(
                control_ref=ctrl.ref_id,
                title=ctrl.title,
                severity=sev,
                description=ctrl.description,
                remediation=ctrl.remediation,
                occurrences=item["count"],
                affected_equipements=item["equipements"],
                category_name=ctrl.category.name if ctrl.category else None,
            )
            by_severity[sev].append(detail)

        # Tri intra-severite par occurrences desc
        for sev in by_severity:
            by_severity[sev].sort(key=lambda x: -x.occurrences)

        # Reordonner par severite (critical -> info)
        ordered_by_severity = dict(
            sorted(
                by_severity.items(),
                key=lambda kv: SEVERITY_RANK.get(kv[0], 99),
            )
        )

        return RecommendationsList(
            audit_id=audit_id,
            total=sum(len(v) for v in ordered_by_severity.values()),
            by_severity=ordered_by_severity,
        )
