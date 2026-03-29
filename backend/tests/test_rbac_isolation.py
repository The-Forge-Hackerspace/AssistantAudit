"""
Tests RBAC — isolation des audits et entreprises par owner_id.

Verifie que chaque auditeur ne voit que ses propres audits/entreprises
et que l'admin voit tout.
"""
import pytest
from app.core.security import create_access_token, hash_password
from app.models import User
from app.models.audit import Audit
from app.models.entreprise import Entreprise


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def entreprise(db_session):
    e = Entreprise(nom="Entreprise RBAC Test")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture
def audit_user_a(db_session, auditeur_user, entreprise):
    """Audit cree par auditeur_user (User A)."""
    a = Audit(
        nom_projet="Audit User A",
        entreprise_id=entreprise.id,
        owner_id=auditeur_user.id,
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def audit_user_b(db_session, second_auditeur_user, entreprise):
    """Audit cree par second_auditeur_user (User B)."""
    a = Audit(
        nom_projet="Audit User B",
        entreprise_id=entreprise.id,
        owner_id=second_auditeur_user.id,
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


# ══════════════════════════════════════════════════════════════════════
# AUDIT ISOLATION
# ══════════════════════════════════════════════════════════════════════


class TestAuditIsolation:

    def test_user_a_sees_only_own_audits(
        self, client, auditeur_headers, audit_user_a, audit_user_b,
    ):
        """User A ne voit que ses propres audits dans la liste."""
        r = client.get("/api/v1/audits", headers=auditeur_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        audit_ids = [a["id"] for a in items]
        assert audit_user_a.id in audit_ids
        assert audit_user_b.id not in audit_ids

    def test_user_b_does_not_see_user_a_in_list(
        self, client, second_auditeur_headers, audit_user_a, audit_user_b,
    ):
        """User B ne voit pas l'audit de User A dans la liste."""
        r = client.get("/api/v1/audits", headers=second_auditeur_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        audit_ids = [a["id"] for a in items]
        assert audit_user_b.id in audit_ids
        assert audit_user_a.id not in audit_ids

    def test_user_b_get_user_a_audit_returns_404(
        self, client, second_auditeur_headers, audit_user_a,
    ):
        """User B ne peut pas acceder a l'audit de User A par ID."""
        r = client.get(
            f"/api/v1/audits/{audit_user_a.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_user_b_update_user_a_audit_returns_404(
        self, client, second_auditeur_headers, audit_user_a,
    ):
        """User B ne peut pas modifier l'audit de User A."""
        r = client.put(
            f"/api/v1/audits/{audit_user_a.id}",
            json={"nom_projet": "Hijacked"},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_sees_all_audits(
        self, client, admin_headers, audit_user_a, audit_user_b,
    ):
        """Admin voit les audits de User A et User B."""
        r = client.get("/api/v1/audits", headers=admin_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        audit_ids = [a["id"] for a in items]
        assert audit_user_a.id in audit_ids
        assert audit_user_b.id in audit_ids

    def test_admin_can_get_any_audit(
        self, client, admin_headers, audit_user_a, audit_user_b,
    ):
        """Admin peut acceder a n'importe quel audit par ID."""
        r1 = client.get(f"/api/v1/audits/{audit_user_a.id}", headers=admin_headers)
        r2 = client.get(f"/api/v1/audits/{audit_user_b.id}", headers=admin_headers)
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_user_a_sees_only_own_count(
        self, client, auditeur_headers, audit_user_a, audit_user_b,
    ):
        """Le total dans la pagination ne compte que les audits du user."""
        r = client.get("/api/v1/audits", headers=auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 1


# ══════════════════════════════════════════════════════════════════════
# ENTREPRISE ISOLATION (acces implicite via audit ownership)
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def entreprise_a(db_session):
    """Entreprise liee uniquement aux audits de User A."""
    e = Entreprise(nom="Entreprise A Only")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture
def entreprise_shared(db_session):
    """Entreprise partagee entre User A et User B."""
    e = Entreprise(nom="Entreprise Shared")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture
def audit_a_on_entreprise_a(db_session, auditeur_user, entreprise_a):
    a = Audit(
        nom_projet="Audit A on Ent A",
        entreprise_id=entreprise_a.id,
        owner_id=auditeur_user.id,
    )
    db_session.add(a)
    db_session.commit()
    return a


@pytest.fixture
def audit_a_on_shared(db_session, auditeur_user, entreprise_shared):
    a = Audit(
        nom_projet="Audit A on Shared",
        entreprise_id=entreprise_shared.id,
        owner_id=auditeur_user.id,
    )
    db_session.add(a)
    db_session.commit()
    return a


@pytest.fixture
def audit_b_on_shared(db_session, second_auditeur_user, entreprise_shared):
    a = Audit(
        nom_projet="Audit B on Shared",
        entreprise_id=entreprise_shared.id,
        owner_id=second_auditeur_user.id,
    )
    db_session.add(a)
    db_session.commit()
    return a


class TestEntrepriseIsolation:

    def test_user_a_sees_own_entreprise(
        self, client, auditeur_headers, audit_a_on_entreprise_a, entreprise_a,
    ):
        """User A voit l'entreprise liee a son audit."""
        r = client.get("/api/v1/entreprises", headers=auditeur_headers)
        assert r.status_code == 200
        noms = [e["nom"] for e in r.json()["items"]]
        assert entreprise_a.nom in noms

    def test_user_b_without_audit_sees_empty(
        self, client, second_auditeur_headers, audit_a_on_entreprise_a,
    ):
        """User B sans audit ne voit pas l'entreprise de User A."""
        r = client.get("/api/v1/entreprises", headers=second_auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_user_b_get_entreprise_a_returns_404(
        self, client, second_auditeur_headers, audit_a_on_entreprise_a, entreprise_a,
    ):
        """User B GET entreprise de User A → 404."""
        r = client.get(
            f"/api/v1/entreprises/{entreprise_a.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_shared_entreprise_visible_by_both(
        self, client, auditeur_headers, second_auditeur_headers,
        audit_a_on_shared, audit_b_on_shared, entreprise_shared,
    ):
        """Entreprise partagee visible par les 2 users ayant un audit dessus."""
        r_a = client.get("/api/v1/entreprises", headers=auditeur_headers)
        r_b = client.get("/api/v1/entreprises", headers=second_auditeur_headers)
        noms_a = [e["nom"] for e in r_a.json()["items"]]
        noms_b = [e["nom"] for e in r_b.json()["items"]]
        assert entreprise_shared.nom in noms_a
        assert entreprise_shared.nom in noms_b

    def test_admin_sees_all_entreprises(
        self, client, admin_headers,
        audit_a_on_entreprise_a, entreprise_a, entreprise_shared,
    ):
        """Admin voit toutes les entreprises."""
        r = client.get("/api/v1/entreprises", headers=admin_headers)
        assert r.status_code == 200
        noms = [e["nom"] for e in r.json()["items"]]
        assert entreprise_a.nom in noms
        assert entreprise_shared.nom in noms

    def test_any_auditeur_can_create_entreprise(
        self, client, second_auditeur_headers,
    ):
        """Tout auditeur peut creer une entreprise (meme sans audit)."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Nouvelle Entreprise", "contacts": []},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 201
        assert r.json()["nom"] == "Nouvelle Entreprise"
