"""Service de generation des recommandations exhaustives d'un audit (TOS-25 section 5).

Groupe les non-conformites par controle, trie par severite, et expose la liste
complete pour le rapport PDF (section recommendations) et la page web.
"""

import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from ..core.helpers import check_audit_access
from ..models.assessment import (
    AssessmentCampaign,
    ComplianceStatus,
)
from ..schemas.recommendations import RecommendationDetail, RecommendationsList
from ._severity import SEVERITY_RANK

logger = logging.getLogger(__name__)


class RecommendationsService:
    """Calcule la liste exhaustive des recommandations d'un audit."""

    @staticmethod
    def generate(
        db: Session, audit_id: int, user_id: int, is_admin: bool
    ) -> RecommendationsList:
        """Liste exhaustive des recommandations groupees par severite.

        Une recommandation = un controle non-conforme aggrege sur ses occurrences.
        Tri intra-severite : nombre d'occurrences decroissant.
        """
        check_audit_access(db, audit_id, user_id, is_admin)

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

        # Construire les details et grouper par severite + categorie
        by_severity: dict[str, list[RecommendationDetail]] = defaultdict(list)
        by_category: dict[str, list[RecommendationDetail]] = defaultdict(list)
        for item in nc_by_control.values():
            ctrl = item["control"]
            sev = ctrl.severity.value
            sub_cat = ctrl.category.name if ctrl.category else "Autres"
            # Groupement de la synthese par framework (ex: AD, Firewall, M365),
            # pas par sous-categorie : un audit cible un seul referentiel par bloc.
            framework = ctrl.category.framework if ctrl.category else None
            group_name = framework.name if framework else "Autres"
            detail = RecommendationDetail(
                control_ref=ctrl.ref_id,
                title=ctrl.title,
                severity=sev,
                description=ctrl.description,
                remediation=ctrl.remediation,
                occurrences=item["count"],
                affected_equipements=item["equipements"],
                category_name=sub_cat,
            )
            by_severity[sev].append(detail)
            by_category[group_name].append(detail)

        # Tri intra-severite par occurrences desc
        for sev in by_severity:
            by_severity[sev].sort(key=lambda x: -x.occurrences)

        # Tri intra-categorie par severite puis occurrences
        for cat in by_category:
            by_category[cat].sort(
                key=lambda x: (SEVERITY_RANK.get(x.severity, 99), -x.occurrences)
            )

        # Reordonner par severite (critical -> info) et categorie (alpha)
        ordered_by_severity = dict(
            sorted(
                by_severity.items(),
                key=lambda kv: SEVERITY_RANK.get(kv[0], 99),
            )
        )
        ordered_by_category = dict(sorted(by_category.items(), key=lambda kv: kv[0]))

        return RecommendationsList(
            audit_id=audit_id,
            total=sum(len(v) for v in ordered_by_severity.values()),
            by_severity=ordered_by_severity,
            by_category=ordered_by_category,
        )
