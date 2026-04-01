"""Tests unitaires — FindingService."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.assessment import (
    Assessment, AssessmentCampaign, CampaignStatus, ComplianceStatus, ControlResult,
)
from app.models.equipement import Equipement
from app.models.finding import Finding, FindingStatus, VALID_TRANSITIONS
from app.models.framework import CheckType, Control, ControlSeverity, Framework, FrameworkCategory
from app.models.user import User
from app.models.audit import Audit
from app.models.entreprise import Entreprise
from app.models.site import Site
from app.services.finding_service import FindingService


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def seed_data(db: Session):
    """Crée les données minimales pour tester le FindingService."""
    # Utilisateur
    user = User(username="auditeur1", email="a@test.fr", password_hash="x", role="auditeur")
    db.add(user)
    db.flush()

    # Entreprise + Site
    entreprise = Entreprise(nom="TestCorp", owner_id=user.id)
    db.add(entreprise)
    db.flush()

    site = Site(nom="HQ", entreprise_id=entreprise.id)
    db.add(site)
    db.flush()

    # Audit
    audit = Audit(nom_projet="Audit Test", entreprise_id=entreprise.id, owner_id=user.id)
    db.add(audit)
    db.flush()

    # Framework + Category + Controls
    fw = Framework(ref_id="TEST-FW", name="TestFW", version="1.0", source_hash="abc")
    db.add(fw)
    db.flush()

    cat = FrameworkCategory(name="Réseau", framework_id=fw.id)
    db.add(cat)
    db.flush()

    ctrl_critical = Control(
        ref_id="C-001", title="TLS obligatoire", category_id=cat.id,
        severity=ControlSeverity.CRITICAL, check_type=CheckType.MANUAL,
    )
    ctrl_medium = Control(
        ref_id="C-002", title="Logs activés", category_id=cat.id,
        severity=ControlSeverity.MEDIUM, check_type=CheckType.MANUAL,
    )
    ctrl_ok = Control(
        ref_id="C-003", title="Firewall actif", category_id=cat.id,
        severity=ControlSeverity.HIGH, check_type=CheckType.MANUAL,
    )
    db.add_all([ctrl_critical, ctrl_medium, ctrl_ok])
    db.flush()

    # Equipement
    equip = Equipement(
        type_equipement="serveur", hostname="srv01", ip_address="10.0.0.1",
        site_id=site.id,
    )
    db.add(equip)
    db.flush()

    # Campaign + Assessment
    campaign = AssessmentCampaign(
        name="Camp1", audit_id=audit.id, status=CampaignStatus.IN_PROGRESS,
    )
    db.add(campaign)
    db.flush()

    assessment = Assessment(
        campaign_id=campaign.id, equipement_id=equip.id, framework_id=fw.id,
    )
    db.add(assessment)
    db.flush()

    # ControlResults
    cr_nc = ControlResult(
        assessment_id=assessment.id, control_id=ctrl_critical.id,
        status=ComplianceStatus.NON_COMPLIANT,
        comment="TLS 1.0 détecté", remediation_note="Activer TLS 1.2+",
    )
    cr_pc = ControlResult(
        assessment_id=assessment.id, control_id=ctrl_medium.id,
        status=ComplianceStatus.PARTIALLY_COMPLIANT,
        comment="Logs partiels",
    )
    cr_ok = ControlResult(
        assessment_id=assessment.id, control_id=ctrl_ok.id,
        status=ComplianceStatus.COMPLIANT,
    )
    db.add_all([cr_nc, cr_pc, cr_ok])
    db.flush()

    return {
        "user": user,
        "assessment": assessment,
        "equipment": equip,
        "cr_nc": cr_nc,
        "cr_pc": cr_pc,
        "cr_ok": cr_ok,
    }


# ── Tests de génération ─────────────────────────────────────────────

class TestGeneration:
    def test_generate_creates_findings_for_non_compliant(self, db, seed_data):
        """Génère un finding par ControlResult NON_COMPLIANT ou PARTIALLY_COMPLIANT."""
        generated, skipped = FindingService.generate_from_assessment(
            db, seed_data["assessment"].id, user_id=seed_data["user"].id
        )
        assert generated == 2
        assert skipped == 0

    def test_generate_skips_existing(self, db, seed_data):
        """La deuxième génération ne crée pas de doublons."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        generated, skipped = FindingService.generate_from_assessment(
            db, seed_data["assessment"].id
        )
        assert generated == 0
        assert skipped == 2

    def test_generated_finding_has_correct_fields(self, db, seed_data):
        """Les findings générés ont les bons champs."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        findings, total = FindingService.list_findings(db)
        assert total == 2

        critical = next(f for f in findings if f.severity == "critical")
        assert critical.title == "TLS obligatoire"
        assert critical.status == FindingStatus.OPEN
        assert critical.equipment_id == seed_data["equipment"].id


# ── Tests de listing/filtrage ────────────────────────────────────────

class TestListing:
    def test_list_with_status_filter(self, db, seed_data):
        """Filtre par statut."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        findings, total = FindingService.list_findings(db, status="open")
        assert total == 2

        findings, total = FindingService.list_findings(db, status="closed")
        assert total == 0

    def test_list_with_severity_filter(self, db, seed_data):
        """Filtre par sévérité."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        findings, total = FindingService.list_findings(db, severity="critical")
        assert total == 1

    def test_counts_by_status(self, db, seed_data):
        """Compteurs par statut."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        counts = FindingService.counts_by_status(db)
        assert counts["open"] == 2
        assert counts["total"] == 2
        assert counts["closed"] == 0


# ── Tests de transition de statut ────────────────────────────────────

class TestStatusTransition:
    def _get_first_finding(self, db, seed_data) -> Finding:
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        findings, _ = FindingService.list_findings(db)
        return findings[0]

    def test_valid_transition(self, db, seed_data):
        """Transition OPEN → ASSIGNED fonctionne."""
        finding = self._get_first_finding(db, seed_data)
        updated = FindingService.update_status(
            db, finding, "assigned",
            user_id=seed_data["user"].id,
            comment="Assigné à l'équipe réseau",
            assigned_to="Jean Dupont",
        )
        assert updated.status == FindingStatus.ASSIGNED
        assert updated.assigned_to == "Jean Dupont"
        assert len(updated.status_history) == 1
        assert updated.status_history[0].old_status == FindingStatus.OPEN
        assert updated.status_history[0].new_status == FindingStatus.ASSIGNED

    def test_invalid_transition_raises(self, db, seed_data):
        """Transition OPEN → VERIFIED lève ValueError."""
        finding = self._get_first_finding(db, seed_data)
        with pytest.raises(ValueError, match="Transition invalide"):
            FindingService.update_status(db, finding, "verified")

    def test_full_lifecycle(self, db, seed_data):
        """Cycle complet OPEN → ASSIGNED → IN_PROGRESS → REMEDIATED → VERIFIED → CLOSED."""
        finding = self._get_first_finding(db, seed_data)
        uid = seed_data["user"].id

        for new_status in ["assigned", "in_progress", "remediated", "verified", "closed"]:
            finding = FindingService.update_status(db, finding, new_status, user_id=uid)

        assert finding.status == FindingStatus.CLOSED
        assert len(finding.status_history) == 5

    def test_reopen_from_verified(self, db, seed_data):
        """Régression : VERIFIED → OPEN possible."""
        finding = self._get_first_finding(db, seed_data)
        uid = seed_data["user"].id
        for s in ["assigned", "in_progress", "remediated", "verified"]:
            finding = FindingService.update_status(db, finding, s, user_id=uid)

        finding = FindingService.update_status(
            db, finding, "open", user_id=uid, comment="Régression détectée"
        )
        assert finding.status == FindingStatus.OPEN


# ── Tests de liaison doublon ─────────────────────────────────────────

class TestDuplicate:
    def test_link_duplicate(self, db, seed_data):
        """Liaison de doublon fonctionne."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        findings, _ = FindingService.list_findings(db)
        f1, f2 = findings[0], findings[1]

        updated = FindingService.link_duplicate(db, f2, f1.id)
        assert updated.duplicate_of_id == f1.id

    def test_self_duplicate_raises(self, db, seed_data):
        """Un finding ne peut pas être doublon de lui-même."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        findings, _ = FindingService.list_findings(db)
        with pytest.raises(ValueError, match="doublon de lui-même"):
            FindingService.link_duplicate(db, findings[0], findings[0].id)

    def test_invalid_duplicate_raises(self, db, seed_data):
        """Finding original inexistant lève ValueError."""
        FindingService.generate_from_assessment(db, seed_data["assessment"].id)
        findings, _ = FindingService.list_findings(db)
        with pytest.raises(ValueError, match="introuvable"):
            FindingService.link_duplicate(db, findings[0], 99999)
