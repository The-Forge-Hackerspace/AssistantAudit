"""Tests pour le plan de remediation (TOS-25 section 6)."""

import pytest

from app.models.assessment import (
    Assessment,
    AssessmentCampaign,
    ComplianceStatus,
    ControlResult,
)
from app.models.audit import Audit
from app.models.entreprise import Entreprise
from app.models.equipement import Equipement
from app.models.framework import Control, ControlSeverity, Framework, FrameworkCategory
from app.services.remediation_plan_service import RemediationPlanService


@pytest.fixture
def audit_with_data(db_session, auditeur_user):
    e = Entreprise(nom="ACME", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.flush()
    audit = Audit(
        nom_projet="Audit plan test",
        entreprise_id=e.id,
        owner_id=auditeur_user.id,
    )
    db_session.add(audit)
    db_session.flush()

    from app.models.site import Site

    site = Site(nom="S1", entreprise_id=e.id)
    db_session.add(site)
    db_session.flush()
    eq = Equipement(
        site_id=site.id,
        type_equipement="equipement",
        ip_address="10.0.0.1",
        hostname="srv-01",
    )
    db_session.add(eq)
    db_session.flush()

    fw = Framework(ref_id="TEST", name="Test", version="1.0", is_active=True)
    db_session.add(fw)
    db_session.flush()
    cat = FrameworkCategory(name="Securite", framework_id=fw.id)
    db_session.add(cat)
    db_session.flush()

    return audit, eq, fw, cat


class TestRemediationPlanService:
    def test_no_non_compliances_returns_empty_horizons(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, _, _, _ = audit_with_data
        plan = RemediationPlanService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        assert plan.total_actions == 0
        assert plan.total_effort_days == 0
        assert len(plan.horizons) == 4
        assert all(h.total_actions == 0 for h in plan.horizons)

    def test_severity_to_horizon_mapping(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat = audit_with_data

        ctrls = []
        for ref, sev in [
            ("C-001", ControlSeverity.CRITICAL),
            ("H-001", ControlSeverity.HIGH),
            ("M-001", ControlSeverity.MEDIUM),
            ("L-001", ControlSeverity.LOW),
        ]:
            c = Control(
                ref_id=ref,
                title=f"Ctrl {ref}",
                severity=sev,
                category_id=cat.id,
                remediation=f"Fix {ref}",
            )
            db_session.add(c)
            ctrls.append(c)
        db_session.flush()

        camp = AssessmentCampaign(name="C", audit_id=audit.id)
        db_session.add(camp)
        db_session.flush()
        assess = Assessment(
            campaign_id=camp.id, equipement_id=eq.id, framework_id=fw.id
        )
        db_session.add(assess)
        db_session.flush()
        for c in ctrls:
            db_session.add(
                ControlResult(
                    assessment_id=assess.id,
                    control_id=c.id,
                    status=ComplianceStatus.NON_COMPLIANT,
                )
            )
        db_session.commit()

        plan = RemediationPlanService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        assert plan.total_actions == 4

        by_key = {h.key: h for h in plan.horizons}
        assert by_key["quick_wins"].total_actions == 1
        assert by_key["quick_wins"].actions[0].control_ref == "C-001"
        assert by_key["short_term"].total_actions == 1
        assert by_key["short_term"].actions[0].control_ref == "H-001"
        assert by_key["mid_term"].total_actions == 1
        assert by_key["mid_term"].actions[0].control_ref == "M-001"
        assert by_key["long_term"].total_actions == 1
        assert by_key["long_term"].actions[0].control_ref == "L-001"

    def test_total_effort_sums_correctly(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat = audit_with_data

        # 1 critique (0.25j) + 2 high (1j chacun)
        ctrls = []
        for ref, sev in [
            ("C-001", ControlSeverity.CRITICAL),
            ("H-001", ControlSeverity.HIGH),
            ("H-002", ControlSeverity.HIGH),
        ]:
            c = Control(ref_id=ref, title=ref, severity=sev, category_id=cat.id)
            db_session.add(c)
            ctrls.append(c)
        db_session.flush()
        camp = AssessmentCampaign(name="C", audit_id=audit.id)
        db_session.add(camp)
        db_session.flush()
        assess = Assessment(
            campaign_id=camp.id, equipement_id=eq.id, framework_id=fw.id
        )
        db_session.add(assess)
        db_session.flush()
        for c in ctrls:
            db_session.add(
                ControlResult(
                    assessment_id=assess.id,
                    control_id=c.id,
                    status=ComplianceStatus.NON_COMPLIANT,
                )
            )
        db_session.commit()

        plan = RemediationPlanService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        # 1*0.25 + 2*1 = 2.25
        assert plan.total_effort_days == pytest.approx(2.25)

    def test_control_effort_override_takes_precedence_over_heuristic(
        self, db_session, audit_with_data, auditeur_user
    ):
        """Si un controle a effort_days renseigne, il prime sur le fallback severite."""
        audit, eq, fw, cat = audit_with_data
        # Critique avec override a 4j (au lieu de 0.25j par defaut)
        c = Control(
            ref_id="C-OVER",
            title="Refonte AD complete",
            severity=ControlSeverity.CRITICAL,
            category_id=cat.id,
            effort_days=4.0,
        )
        db_session.add(c)
        db_session.flush()
        camp = AssessmentCampaign(name="C", audit_id=audit.id)
        db_session.add(camp)
        db_session.flush()
        a = Assessment(campaign_id=camp.id, equipement_id=eq.id, framework_id=fw.id)
        db_session.add(a)
        db_session.flush()
        db_session.add(
            ControlResult(
                assessment_id=a.id,
                control_id=c.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        db_session.commit()

        plan = RemediationPlanService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        # Toujours classe en quick_wins (mapping severite) mais avec 4j
        quick = next(h for h in plan.horizons if h.key == "quick_wins")
        assert quick.actions[0].effort_days == 4.0
        assert plan.total_effort_days == 4.0

    def test_intra_horizon_sorted_by_occurrences(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat = audit_with_data

        c1 = Control(
            ref_id="H-001",
            title="High solo",
            severity=ControlSeverity.HIGH,
            category_id=cat.id,
        )
        c2 = Control(
            ref_id="H-002",
            title="High double",
            severity=ControlSeverity.HIGH,
            category_id=cat.id,
        )
        db_session.add_all([c1, c2])
        db_session.flush()

        camp = AssessmentCampaign(name="C", audit_id=audit.id)
        db_session.add(camp)
        db_session.flush()
        a1 = Assessment(campaign_id=camp.id, equipement_id=eq.id, framework_id=fw.id)
        db_session.add(a1)
        db_session.flush()

        eq2 = Equipement(
            site_id=eq.site_id,
            type_equipement="equipement",
            ip_address="10.0.0.2",
            hostname="srv-02",
        )
        db_session.add(eq2)
        db_session.flush()
        a2 = Assessment(campaign_id=camp.id, equipement_id=eq2.id, framework_id=fw.id)
        db_session.add(a2)
        db_session.flush()

        # c1 : 1 NC, c2 : 2 NC
        db_session.add(
            ControlResult(
                assessment_id=a1.id,
                control_id=c1.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        for a in (a1, a2):
            db_session.add(
                ControlResult(
                    assessment_id=a.id,
                    control_id=c2.id,
                    status=ComplianceStatus.NON_COMPLIANT,
                )
            )
        db_session.commit()

        plan = RemediationPlanService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        short = next(h for h in plan.horizons if h.key == "short_term")
        assert short.actions[0].control_ref == "H-002"
        assert short.actions[0].occurrences == 2
        assert short.actions[1].control_ref == "H-001"
