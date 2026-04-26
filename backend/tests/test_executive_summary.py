"""Tests pour la synthese executive d'un audit (TOS-29)."""

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


@pytest.fixture
def entreprise_test(db_session, auditeur_user):
    e = Entreprise(nom="ACME Corp", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.flush()
    return e


@pytest.fixture
def audit_owned(db_session, auditeur_user, entreprise_test):
    audit = Audit(
        nom_projet="Audit synthese test",
        entreprise_id=entreprise_test.id,
        owner_id=auditeur_user.id,
    )
    db_session.add(audit)
    db_session.flush()
    return audit


@pytest.fixture
def framework_test(db_session):
    fw = Framework(ref_id="TEST-FW", name="Test Framework", version="1.0", is_active=True)
    db_session.add(fw)
    db_session.flush()
    cat = FrameworkCategory(name="Securite", framework_id=fw.id)
    db_session.add(cat)
    db_session.flush()
    return fw, cat


@pytest.fixture
def equip_test(db_session, entreprise_test):
    from app.models.site import Site

    site = Site(nom="Site test", entreprise_id=entreprise_test.id)
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
    return eq


def _make_control(db_session, framework, category, ref, severity, remediation=None):
    # framework parametre conserve pour la lisibilite (lien via category.framework_id)
    _ = framework
    c = Control(
        ref_id=ref,
        title=f"Control {ref}",
        description=f"Desc {ref}",
        severity=severity,
        category_id=category.id,
        remediation=remediation or f"Fix {ref}",
    )
    db_session.add(c)
    db_session.flush()
    return c


class TestExecutiveSummary:
    def test_audit_without_evaluations_returns_no_data(
        self, client, auditeur_headers, audit_owned
    ):
        resp = client.get(
            f"/api/v1/audits/{audit_owned.id}/executive-summary",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["has_data"] is False
        assert body["global_score"] is None
        assert body["total_evaluations"] == 0
        assert body["top_non_compliances"] == []

    def test_audit_other_user_returns_404(
        self, client, second_auditeur_user, audit_owned, db_session
    ):
        from app.core.security import create_access_token

        token = create_access_token(subject=second_auditeur_user.id)
        resp = client.get(
            f"/api/v1/audits/{audit_owned.id}/executive-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_summary_with_results(
        self,
        client,
        auditeur_headers,
        audit_owned,
        framework_test,
        equip_test,
        db_session,
    ):
        framework, category = framework_test
        # 3 controles : 1 critical NC, 1 high NC, 1 medium compliant
        ctrl_crit = _make_control(
            db_session, framework, category, "CTRL-001", ControlSeverity.CRITICAL,
            "Activer le firewall",
        )
        ctrl_high = _make_control(
            db_session, framework, category, "CTRL-002", ControlSeverity.HIGH,
        )
        ctrl_med = _make_control(
            db_session, framework, category, "CTRL-003", ControlSeverity.MEDIUM,
        )

        # Campagne + assessment
        campaign = AssessmentCampaign(
            name="Camp test", audit_id=audit_owned.id
        )
        db_session.add(campaign)
        db_session.flush()
        assessment = Assessment(
            campaign_id=campaign.id,
            equipement_id=equip_test.id,
            framework_id=framework.id,
        )
        db_session.add(assessment)
        db_session.flush()
        # Results
        for ctrl, status in [
            (ctrl_crit, ComplianceStatus.NON_COMPLIANT),
            (ctrl_high, ComplianceStatus.NON_COMPLIANT),
            (ctrl_med, ComplianceStatus.COMPLIANT),
        ]:
            db_session.add(
                ControlResult(
                    assessment_id=assessment.id,
                    control_id=ctrl.id,
                    status=status,
                )
            )
        db_session.commit()

        resp = client.get(
            f"/api/v1/audits/{audit_owned.id}/executive-summary",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["has_data"] is True
        # 1 compliant / 3 assessed = 33.3
        assert abs(body["global_score"] - 33.3) < 0.5
        assert body["total_evaluations"] == 1
        assert body["total_equipements"] == 1
        assert body["by_status"]["compliant"] == 1
        assert body["by_status"]["non_compliant"] == 2
        # Top NC : critical en premier
        assert len(body["top_non_compliances"]) == 2
        assert body["top_non_compliances"][0]["severity"] == "critical"
        assert body["top_non_compliances"][0]["control_ref"] == "CTRL-001"
        # Recommandations : max 3, severity-tri en premier
        assert len(body["recommendations"]) == 2
        assert body["recommendations"][0]["control_ref"] == "CTRL-001"
        assert body["recommendations"][0]["remediation"] == "Activer le firewall"

    def test_top_non_compliances_limited_to_5(
        self,
        client,
        auditeur_headers,
        audit_owned,
        framework_test,
        equip_test,
        db_session,
    ):
        framework, category = framework_test
        campaign = AssessmentCampaign(name="Camp", audit_id=audit_owned.id)
        db_session.add(campaign)
        db_session.flush()
        assessment = Assessment(
            campaign_id=campaign.id,
            equipement_id=equip_test.id,
            framework_id=framework.id,
        )
        db_session.add(assessment)
        db_session.flush()
        # 7 NC distincts
        for i in range(7):
            ctrl = _make_control(
                db_session, framework, category, f"CTRL-{i:03d}", ControlSeverity.HIGH,
            )
            db_session.add(
                ControlResult(
                    assessment_id=assessment.id,
                    control_id=ctrl.id,
                    status=ComplianceStatus.NON_COMPLIANT,
                )
            )
        db_session.commit()

        resp = client.get(
            f"/api/v1/audits/{audit_owned.id}/executive-summary",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["top_non_compliances"]) == 5
        assert len(body["recommendations"]) == 3
