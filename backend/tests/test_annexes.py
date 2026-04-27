"""Tests pour la generation des annexes (TOS-25 section 7)."""

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
from app.models.site import Site
from app.services.annexes_service import AnnexesService


@pytest.fixture
def audit_with_data(db_session, auditeur_user):
    e = Entreprise(nom="ACME", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.flush()
    audit = Audit(
        nom_projet="Audit annexes test",
        entreprise_id=e.id,
        owner_id=auditeur_user.id,
    )
    db_session.add(audit)
    db_session.flush()

    site = Site(nom="Paris", entreprise_id=e.id)
    db_session.add(site)
    db_session.flush()
    eq = Equipement(
        site_id=site.id,
        type_equipement="equipement",
        ip_address="10.0.0.1",
        hostname="dc-paris-01",
    )
    db_session.add(eq)
    db_session.flush()

    fw = Framework(
        ref_id="AD",
        name="Audit Active Directory",
        version="1.0",
        is_active=True,
        source="ANSSI",
        author="The Forge",
    )
    db_session.add(fw)
    db_session.flush()
    cat = FrameworkCategory(name="Securite", framework_id=fw.id)
    db_session.add(cat)
    db_session.flush()

    return audit, eq, fw, cat, site


class TestAnnexesService:
    def test_empty_audit_returns_empty_lists(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, _, _, _, _ = audit_with_data
        annexes = AnnexesService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        assert annexes.equipements == []
        assert annexes.results == []
        assert annexes.frameworks == []

    def test_aggregates_equipements_results_and_frameworks(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat, _ = audit_with_data

        c1 = Control(
            ref_id="AD-001",
            title="MFA actif",
            severity=ControlSeverity.CRITICAL,
            category_id=cat.id,
        )
        db_session.add(c1)
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
                control_id=c1.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        db_session.commit()

        annexes = AnnexesService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        # equipement deduplique sur eq.id
        assert len(annexes.equipements) == 1
        assert annexes.equipements[0].hostname == "dc-paris-01"
        assert annexes.equipements[0].site_name == "Paris"
        # 1 controle
        assert len(annexes.results) == 1
        assert annexes.results[0].control_ref == "AD-001"
        assert annexes.results[0].non_compliant == 1
        assert annexes.results[0].compliant == 0
        assert annexes.results[0].framework_name == "Audit Active Directory"
        # 1 framework
        assert len(annexes.frameworks) == 1
        assert annexes.frameworks[0].ref_id == "AD"
        assert annexes.frameworks[0].source == "ANSSI"

    def test_status_counts_aggregate_across_assessments(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat, site = audit_with_data
        c = Control(
            ref_id="AD-002",
            title="Sauvegarde DC",
            severity=ControlSeverity.HIGH,
            category_id=cat.id,
        )
        db_session.add(c)
        db_session.flush()
        eq2 = Equipement(
            site_id=site.id,
            type_equipement="equipement",
            ip_address="10.0.0.2",
            hostname="dc-paris-02",
        )
        db_session.add(eq2)
        db_session.flush()

        camp = AssessmentCampaign(name="C", audit_id=audit.id)
        db_session.add(camp)
        db_session.flush()
        a1 = Assessment(campaign_id=camp.id, equipement_id=eq.id, framework_id=fw.id)
        a2 = Assessment(campaign_id=camp.id, equipement_id=eq2.id, framework_id=fw.id)
        db_session.add_all([a1, a2])
        db_session.flush()
        # 1 conforme, 1 non conforme sur le meme controle
        db_session.add(
            ControlResult(
                assessment_id=a1.id,
                control_id=c.id,
                status=ComplianceStatus.COMPLIANT,
            )
        )
        db_session.add(
            ControlResult(
                assessment_id=a2.id,
                control_id=c.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        db_session.commit()

        annexes = AnnexesService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        result = annexes.results[0]
        assert result.compliant == 1
        assert result.non_compliant == 1
        # 2 equipements distincts
        assert len(annexes.equipements) == 2
