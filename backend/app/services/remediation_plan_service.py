"""Service de generation du plan de remediation d'un audit (TOS-25 section 6).

Heuristique : sevirite -> horizon temporel + charge estimee. Toutes les
non-conformites sont incluses ; le client ajustera ensuite selon ses contraintes.
"""

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.assessment import (
    AssessmentCampaign,
    ComplianceStatus,
)
from ..models.audit import Audit
from ..schemas.remediation_plan import (
    RemediationAction,
    RemediationHorizon,
    RemediationPlan,
)

logger = logging.getLogger(__name__)


# Mapping severite -> horizon temporel (la charge specifique est lue
# sur le controle si disponible, sinon on applique le fallback ci-dessous).
SEVERITY_TO_HORIZON: dict[str, str] = {
    "critical": "quick_wins",
    "high": "short_term",
    "medium": "mid_term",
    "low": "long_term",
    "info": "long_term",
}

# Fallback charge par severite (jours-homme) quand le controle n'a pas
# d'estimation specifique (effort_days). Vocation a etre remplace par
# une estimation contextuelle generee par LLM (TOS-7X).
DEFAULT_EFFORT_BY_SEVERITY: dict[str, float] = {
    "critical": 0.25,
    "high": 1.0,
    "medium": 3.0,
    "low": 5.0,
    "info": 5.0,
}

HORIZONS_ORDER = [
    (
        "quick_wins",
        "Quick wins",
        "Actions immediates a engager pour limiter les risques majeurs.",
    ),
    (
        "short_term",
        "0 a 3 mois",
        "Corrections importantes a planifier dans le trimestre.",
    ),
    (
        "mid_term",
        "3 a 6 mois",
        "Actions structurantes a integrer dans la roadmap a moyen terme.",
    ),
    (
        "long_term",
        "6 a 12 mois",
        "Ameliorations et bonnes pratiques a derouler sur l'annee.",
    ),
]


class RemediationPlanService:
    """Calcule le plan de remediation d'un audit."""

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
    ) -> RemediationPlan:
        """Plan de remediation groupe par horizon temporel.

        Toutes les non-conformites sont incluses. L'horizon et la charge sont
        derives de la severite du controle (heuristique par defaut).
        """
        RemediationPlanService._check_audit_access(db, audit_id, user_id, is_admin)

        campaigns = (
            db.query(AssessmentCampaign)
            .filter(AssessmentCampaign.audit_id == audit_id)
            .all()
        )

        # Aggregat par controle (un controle = une action, eventuellement multi-equipements)
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

        # Construire les actions et grouper par horizon
        actions_by_horizon: dict[str, list[RemediationAction]] = {
            key: [] for key, _, _ in HORIZONS_ORDER
        }
        for item in nc_by_control.values():
            ctrl = item["control"]
            sev = ctrl.severity.value
            horizon_key = SEVERITY_TO_HORIZON.get(sev, "long_term")
            effort = (
                ctrl.effort_days
                if ctrl.effort_days is not None
                else DEFAULT_EFFORT_BY_SEVERITY.get(sev, 5.0)
            )
            action = RemediationAction(
                control_ref=ctrl.ref_id,
                title=ctrl.title,
                severity=sev,
                remediation=ctrl.remediation,
                occurrences=item["count"],
                affected_equipements=item["equipements"],
                horizon=horizon_key,
                effort_days=effort,
            )
            actions_by_horizon[horizon_key].append(action)

        # Tri intra-horizon : occurrences decroissantes
        for actions in actions_by_horizon.values():
            actions.sort(key=lambda a: -a.occurrences)

        horizons: list[RemediationHorizon] = []
        for key, label, desc in HORIZONS_ORDER:
            actions = actions_by_horizon[key]
            horizons.append(
                RemediationHorizon(
                    key=key,
                    label=label,
                    description=desc,
                    actions=actions,
                    total_actions=len(actions),
                    total_effort_days=sum(a.effort_days for a in actions),
                )
            )

        total_actions = sum(h.total_actions for h in horizons)
        total_effort_days = sum(h.total_effort_days for h in horizons)

        return RemediationPlan(
            audit_id=audit_id,
            total_actions=total_actions,
            total_effort_days=total_effort_days,
            horizons=horizons,
        )
