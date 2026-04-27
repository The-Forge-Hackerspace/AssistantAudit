"""Tests pour le glossaire dynamique (TOS-25 section 8)."""

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
from app.services.glossary_service import GlossaryService, _entry_matches
from app.schemas.glossary import GlossaryEntry


@pytest.fixture
def audit_with_data(db_session, auditeur_user):
    e = Entreprise(nom="ACME", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.flush()
    audit = Audit(
        nom_projet="Audit glossaire test",
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


class TestEntryMatcher:
    def test_term_match_case_insensitive(self):
        e = GlossaryEntry(term="Active Directory", definition="x")
        assert _entry_matches(e, "Configurer active DIRECTORY correctement.")

    def test_alias_match(self):
        e = GlossaryEntry(term="Active Directory", definition="x", aliases=["AD"])
        assert _entry_matches(e, "Auditer l'AD est essentiel.")

    def test_no_partial_word_match(self):
        # "PRA" ne doit pas matcher "PRATIQUE"
        e = GlossaryEntry(term="PRA", definition="x")
        assert not _entry_matches(e, "Voici une bonne pratique.")

    def test_acronym_with_dashes_or_punctuation(self):
        e = GlossaryEntry(term="MFA", definition="x")
        assert _entry_matches(e, "Activer la MFA, c'est important.")


class TestGlossaryService:
    def test_no_non_compliances_returns_empty(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, _, _, _ = audit_with_data
        gloss = GlossaryService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        assert gloss.total == 0
        assert gloss.entries == []

    def test_only_terms_present_in_nc_controls_are_returned(
        self, db_session, audit_with_data, auditeur_user
    ):
        audit, eq, fw, cat = audit_with_data
        # 1 controle qui parle d'AD/MFA, 1 qui parle d'autre chose
        c1 = Control(
            ref_id="C-AD",
            title="MFA pour les Domain Admins de l'Active Directory",
            severity=ControlSeverity.CRITICAL,
            category_id=cat.id,
            remediation="Activer la MFA pour tous les comptes Domain Admin.",
        )
        c2 = Control(
            ref_id="C-OTHER",
            title="Sauvegarde des fichiers utilisateurs",
            severity=ControlSeverity.MEDIUM,
            category_id=cat.id,
            remediation="Mettre en place une procedure de sauvegarde quotidienne.",
        )
        db_session.add_all([c1, c2])
        db_session.flush()

        camp = AssessmentCampaign(name="C", audit_id=audit.id)
        db_session.add(camp)
        db_session.flush()
        a = Assessment(campaign_id=camp.id, equipement_id=eq.id, framework_id=fw.id)
        db_session.add(a)
        db_session.flush()
        # Seul c1 est non conforme — c2 est conforme et ne doit pas alimenter le glossaire
        db_session.add(
            ControlResult(
                assessment_id=a.id,
                control_id=c1.id,
                status=ComplianceStatus.NON_COMPLIANT,
            )
        )
        db_session.add(
            ControlResult(
                assessment_id=a.id,
                control_id=c2.id,
                status=ComplianceStatus.COMPLIANT,
            )
        )
        db_session.commit()

        gloss = GlossaryService.generate(
            db_session, audit.id, user_id=auditeur_user.id, is_admin=False
        )
        terms = [e.term for e in gloss.entries]
        # AD et MFA doivent apparaitre
        assert "Active Directory" in terms
        assert "MFA" in terms
        # On verifie que le service n'a pas reagi au mot "sauvegarde" du c2 conforme
        # (PRA/RTO/RPO ne doivent pas apparaitre — c2 est conforme et son texte ignore)
        assert "PRA" not in terms
        assert "RTO" not in terms
