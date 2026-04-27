"""Tests pour la liste exhaustive des recommandations (TOS-25 section 5)."""

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
from app.services.recommendations_service import RecommendationsService


@pytest.fixture
def audit_with_data(db_session, auditeur_user):
    e = Entreprise(nom="ACME", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.flush()
    audit = Audit(
        nom_projet="Audit reco test",
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


class TestRecommendationsService:
    def test_no_non_compliances_returns_empty(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, _, _, _ = audit_with_data
        result = RecommendationsService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        assert result.total == 0
        assert result.by_severity == {}

    def test_grouping_by_severity_ordered(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat = audit_with_data

        # 3 controles : critical, medium, high
        ctrls = []
        for ref, sev in [
            ("C-001", ControlSeverity.CRITICAL),
            ("C-002", ControlSeverity.MEDIUM),
            ("C-003", ControlSeverity.HIGH),
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

        result = RecommendationsService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        assert result.total == 3
        # Cles ordonnees critical -> high -> medium
        keys = list(result.by_severity.keys())
        assert keys == ["critical", "high", "medium"]
        assert result.by_severity["critical"][0].control_ref == "C-001"
        assert result.by_severity["critical"][0].remediation == "Fix C-001"

    def test_intra_severity_sorted_by_occurrences(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat = audit_with_data
        # 2 controles HIGH, le second avec 2 occurrences
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

        # 2eme equipement
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

        # c1 : 1 NC sur srv-01, c2 : 2 NC sur srv-01 + srv-02
        db_session.add(
            ControlResult(
                assessment_id=a1.id,
                control_id=c1.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        db_session.add(
            ControlResult(
                assessment_id=a1.id,
                control_id=c2.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        db_session.add(
            ControlResult(
                assessment_id=a2.id,
                control_id=c2.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        db_session.commit()

        result = RecommendationsService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        # H-002 (2 occ) avant H-001 (1 occ)
        items = result.by_severity["high"]
        assert items[0].control_ref == "H-002"
        assert items[0].occurrences == 2
        assert sorted(items[0].affected_equipements) == ["srv-01", "srv-02"]
        assert items[1].control_ref == "H-001"
        assert items[1].occurrences == 1
