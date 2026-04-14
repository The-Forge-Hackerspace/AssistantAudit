"""
Tests RBAC — isolation complète des ressources par owner_id.

Vérifie que chaque auditeur ne voit que ses propres ressources
à chaque niveau de la hiérarchie (audit, entreprise, site, equipement,
scan, campaign) et que l'admin voit tout.
"""

import pytest

from app.models.assessment import AssessmentCampaign
from app.models.audit import Audit
from app.models.entreprise import Entreprise
from app.models.equipement import Equipement
from app.models.scan import ScanReseau
from app.models.site import Site

# ── Helpers ──────────────────────────────────────────────────────────


def _create_chain(db, user, *, ent_name="Ent", site_name="Site", equip_ip="10.0.0.1"):
    """Crée la chaîne complète : entreprise → audit → site → equipement."""
    ent = Entreprise(nom=ent_name, owner_id=user.id)
    db.add(ent)
    db.flush()
    audit = Audit(nom_projet=f"Audit {ent_name}", entreprise_id=ent.id, owner_id=user.id)
    db.add(audit)
    db.flush()
    site = Site(nom=site_name, entreprise_id=ent.id)
    db.add(site)
    db.flush()
    equip = Equipement(
        ip_address=equip_ip,
        site_id=site.id,
        type_equipement="equipement",
    )
    db.add(equip)
    db.commit()
    db.refresh(ent)
    db.refresh(audit)
    db.refresh(site)
    db.refresh(equip)
    return ent, audit, site, equip


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def entreprise(db_session, auditeur_user):
    e = Entreprise(nom="Entreprise RBAC Test", owner_id=auditeur_user.id)
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
# A) AUDIT ISOLATION
# ══════════════════════════════════════════════════════════════════════


class TestAuditIsolation:
    def test_user_a_sees_only_own_audits(
        self,
        client,
        auditeur_headers,
        audit_user_a,
        audit_user_b,
    ):
        """User A ne voit que ses propres audits dans la liste."""
        r = client.get("/api/v1/audits", headers=auditeur_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        audit_ids = [a["id"] for a in items]
        assert audit_user_a.id in audit_ids
        assert audit_user_b.id not in audit_ids

    def test_user_b_does_not_see_user_a_in_list(
        self,
        client,
        second_auditeur_headers,
        audit_user_a,
        audit_user_b,
    ):
        """User B ne voit pas l'audit de User A dans la liste."""
        r = client.get("/api/v1/audits", headers=second_auditeur_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        audit_ids = [a["id"] for a in items]
        assert audit_user_b.id in audit_ids
        assert audit_user_a.id not in audit_ids

    def test_user_b_get_user_a_audit_returns_404(
        self,
        client,
        second_auditeur_headers,
        audit_user_a,
    ):
        """User B ne peut pas acceder a l'audit de User A par ID."""
        r = client.get(
            f"/api/v1/audits/{audit_user_a.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_user_b_update_user_a_audit_returns_404(
        self,
        client,
        second_auditeur_headers,
        audit_user_a,
    ):
        """User B ne peut pas modifier l'audit de User A."""
        r = client.put(
            f"/api/v1/audits/{audit_user_a.id}",
            json={"nom_projet": "Hijacked"},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_sees_all_audits(
        self,
        client,
        admin_headers,
        audit_user_a,
        audit_user_b,
    ):
        """Admin voit les audits de User A et User B."""
        r = client.get("/api/v1/audits", headers=admin_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        audit_ids = [a["id"] for a in items]
        assert audit_user_a.id in audit_ids
        assert audit_user_b.id in audit_ids

    def test_admin_can_get_any_audit(
        self,
        client,
        admin_headers,
        audit_user_a,
        audit_user_b,
    ):
        """Admin peut acceder a n'importe quel audit par ID."""
        r1 = client.get(f"/api/v1/audits/{audit_user_a.id}", headers=admin_headers)
        r2 = client.get(f"/api/v1/audits/{audit_user_b.id}", headers=admin_headers)
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_user_a_sees_only_own_count(
        self,
        client,
        auditeur_headers,
        audit_user_a,
        audit_user_b,
    ):
        """Le total dans la pagination ne compte que les audits du user."""
        r = client.get("/api/v1/audits", headers=auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 1


# ══════════════════════════════════════════════════════════════════════
# B) ENTREPRISE ISOLATION (acces implicite via audit ownership)
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def entreprise_a(db_session, auditeur_user):
    """Entreprise liee uniquement aux audits de User A."""
    e = Entreprise(nom="Entreprise A Only", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture
def entreprise_shared(db_session, auditeur_user):
    """Entreprise partagee entre User A et User B."""
    e = Entreprise(nom="Entreprise Shared", owner_id=auditeur_user.id)
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
        self,
        client,
        auditeur_headers,
        audit_a_on_entreprise_a,
        entreprise_a,
    ):
        """User A voit l'entreprise liee a son audit."""
        r = client.get("/api/v1/entreprises", headers=auditeur_headers)
        assert r.status_code == 200
        noms = [e["nom"] for e in r.json()["items"]]
        assert entreprise_a.nom in noms

    def test_user_b_without_audit_sees_empty(
        self,
        client,
        second_auditeur_headers,
        audit_a_on_entreprise_a,
    ):
        """User B sans audit ne voit pas l'entreprise de User A."""
        r = client.get("/api/v1/entreprises", headers=second_auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_user_b_get_entreprise_a_returns_404(
        self,
        client,
        second_auditeur_headers,
        audit_a_on_entreprise_a,
        entreprise_a,
    ):
        """User B GET entreprise de User A → 404."""
        r = client.get(
            f"/api/v1/entreprises/{entreprise_a.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_shared_entreprise_visible_by_both(
        self,
        client,
        auditeur_headers,
        second_auditeur_headers,
        audit_a_on_shared,
        audit_b_on_shared,
        entreprise_shared,
    ):
        """Entreprise partagee visible par les 2 users ayant un audit dessus."""
        r_a = client.get("/api/v1/entreprises", headers=auditeur_headers)
        r_b = client.get("/api/v1/entreprises", headers=second_auditeur_headers)
        noms_a = [e["nom"] for e in r_a.json()["items"]]
        noms_b = [e["nom"] for e in r_b.json()["items"]]
        assert entreprise_shared.nom in noms_a
        assert entreprise_shared.nom in noms_b

    def test_admin_sees_all_entreprises(
        self,
        client,
        admin_headers,
        audit_a_on_entreprise_a,
        entreprise_a,
        entreprise_shared,
    ):
        """Admin voit toutes les entreprises."""
        r = client.get("/api/v1/entreprises", headers=admin_headers)
        assert r.status_code == 200
        noms = [e["nom"] for e in r.json()["items"]]
        assert entreprise_a.nom in noms
        assert entreprise_shared.nom in noms

    def test_any_auditeur_can_create_entreprise(
        self,
        client,
        second_auditeur_headers,
    ):
        """Tout auditeur peut creer une entreprise (meme sans audit)."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Nouvelle Entreprise", "contacts": []},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 201
        assert r.json()["nom"] == "Nouvelle Entreprise"


# ══════════════════════════════════════════════════════════════════════
# C) SITE ISOLATION (via chaîne Entreprise)
# ══════════════════════════════════════════════════════════════════════


class TestSiteIsolation:
    def test_site_not_visible_to_other_user(
        self,
        client,
        db_session,
        auditeur_user,
        auditeur_headers,
        second_auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne voit pas les sites de User A."""
        ent, audit, site, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent Site A",
            site_name="Site A",
        )
        # User B GET /sites → liste vide
        r = client.get("/api/v1/sites", headers=second_auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0

        # User B GET /sites/{id} → 404
        r = client.get(f"/api/v1/sites/{site.id}", headers=second_auditeur_headers)
        assert r.status_code == 404

    def test_site_update_by_other_user_returns_404(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne peut pas modifier le site de User A."""
        _, _, site, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent SiteUpd",
        )
        r = client.put(
            f"/api/v1/sites/{site.id}",
            json={"nom": "Hijacked"},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_site_create_requires_entreprise_access(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne peut pas créer de site sur l'entreprise de User A."""
        ent, _, _, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent SiteCrt",
        )
        r = client.post(
            "/api/v1/sites",
            json={"nom": "Intrus", "entreprise_id": ent.id},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_sees_all_sites(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_user,
        admin_headers,
    ):
        """Admin voit les sites des 2 users."""
        _create_chain(db_session, auditeur_user, ent_name="Ent SiteAdm A", site_name="SiteAdmA", equip_ip="10.1.0.1")
        _create_chain(
            db_session, second_auditeur_user, ent_name="Ent SiteAdm B", site_name="SiteAdmB", equip_ip="10.2.0.1"
        )
        r = client.get("/api/v1/sites", headers=admin_headers)
        assert r.status_code == 200
        noms = [s["nom"] for s in r.json()["items"]]
        assert "SiteAdmA" in noms
        assert "SiteAdmB" in noms


# ══════════════════════════════════════════════════════════════════════
# D) EQUIPEMENT ISOLATION (via chaîne Site → Entreprise)
# ══════════════════════════════════════════════════════════════════════


class TestEquipementIsolation:
    def test_equipement_not_visible_to_other_user(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne voit pas les equipements de User A."""
        _, _, _, equip = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent EqVis",
        )
        # Liste vide
        r = client.get("/api/v1/equipements", headers=second_auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0

        # Detail → 404
        r = client.get(f"/api/v1/equipements/{equip.id}", headers=second_auditeur_headers)
        assert r.status_code == 404

    def test_equipement_create_requires_site_access(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne peut pas créer d'equipement sur le site de User A."""
        _, _, site, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent EqCrt",
        )
        r = client.post(
            "/api/v1/equipements",
            json={
                "ip_address": "192.168.99.1",
                "site_id": site.id,
                "type_equipement": "serveur",
            },
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# E) SCAN ISOLATION (owner_id direct)
# ══════════════════════════════════════════════════════════════════════


class TestScanIsolation:
    def test_scan_not_visible_to_other_user(
        self,
        client,
        db_session,
        auditeur_user,
        auditeur_headers,
        second_auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne voit pas les scans de User A."""
        _, _, site, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent ScanVis",
        )
        scan = ScanReseau(
            site_id=site.id,
            owner_id=auditeur_user.id,
            type_scan="discovery",
            statut="completed",
        )
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        # User B liste → vide
        r = client.get("/api/v1/scans", headers=second_auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0

        # User B detail → 404
        r = client.get(f"/api/v1/scans/{scan.id}", headers=second_auditeur_headers)
        assert r.status_code == 404

    def test_scan_delete_by_other_user_returns_404(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne peut pas supprimer le scan de User A."""
        _, _, site, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent ScanDel",
        )
        scan = ScanReseau(
            site_id=site.id,
            owner_id=auditeur_user.id,
            type_scan="discovery",
            statut="completed",
        )
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        r = client.delete(f"/api/v1/scans/{scan.id}", headers=second_auditeur_headers)
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# F) CAMPAIGN / ASSESSMENT ISOLATION (via chaîne Audit)
# ══════════════════════════════════════════════════════════════════════


class TestCampaignIsolation:
    def test_campaign_not_visible_to_other_user(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne voit pas les campagnes de User A."""
        ent, audit, _, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent CampVis",
        )
        camp = AssessmentCampaign(name="Camp A", audit_id=audit.id)
        db_session.add(camp)
        db_session.commit()
        db_session.refresh(camp)

        # Liste vide
        r = client.get("/api/v1/assessments/campaigns", headers=second_auditeur_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0

        # Detail → 404
        r = client.get(
            f"/api/v1/assessments/campaigns/{camp.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_campaign_create_requires_audit_access(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne peut pas créer de campagne sur l'audit de User A."""
        _, audit, _, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent CampCrt",
        )
        r = client.post(
            "/api/v1/assessments/campaigns",
            json={"name": "Intrus", "audit_id": audit.id},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_campaign_update_by_other_user_returns_404(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B ne peut pas modifier la campagne de User A."""
        _, audit, _, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent CampUpd",
        )
        camp = AssessmentCampaign(name="Camp A", audit_id=audit.id)
        db_session.add(camp)
        db_session.commit()
        db_session.refresh(camp)

        r = client.put(
            f"/api/v1/assessments/campaigns/{camp.id}",
            json={"name": "Hijacked"},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# G) CHAÎNE COMPLÈTE CROSS-RESOURCE
# ══════════════════════════════════════════════════════════════════════


class TestFullChainIsolation:
    def test_full_chain_isolation(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """User B reçoit 404 à CHAQUE niveau de la chaîne de User A."""
        ent, audit, site, equip = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent FullChain",
        )
        camp = AssessmentCampaign(name="Camp FullChain", audit_id=audit.id)
        db_session.add(camp)
        db_session.commit()
        db_session.refresh(camp)

        checks = [
            f"/api/v1/entreprises/{ent.id}",
            f"/api/v1/audits/{audit.id}",
            f"/api/v1/sites/{site.id}",
            f"/api/v1/equipements/{equip.id}",
            f"/api/v1/assessments/campaigns/{camp.id}",
        ]
        for url in checks:
            r = client.get(url, headers=second_auditeur_headers)
            assert r.status_code == 404, f"Expected 404 on {url}, got {r.status_code}"

    def test_full_chain_admin_bypass(
        self,
        client,
        db_session,
        auditeur_user,
        admin_headers,
    ):
        """Admin accède à toutes les ressources de la chaîne."""
        ent, audit, site, equip = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent AdminBypass",
        )
        camp = AssessmentCampaign(name="Camp AdminBypass", audit_id=audit.id)
        db_session.add(camp)
        db_session.commit()
        db_session.refresh(camp)

        checks = [
            f"/api/v1/entreprises/{ent.id}",
            f"/api/v1/audits/{audit.id}",
            f"/api/v1/sites/{site.id}",
            f"/api/v1/equipements/{equip.id}",
            f"/api/v1/assessments/campaigns/{camp.id}",
        ]
        for url in checks:
            r = client.get(url, headers=admin_headers)
            assert r.status_code == 200, f"Expected 200 on {url}, got {r.status_code}"


# ══════════════════════════════════════════════════════════════════════
# H) 404 PAS 403 (sécurité anti-énumération)
# ══════════════════════════════════════════════════════════════════════


class TestAntiEnumeration:
    def test_ownership_failure_returns_404_not_403(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """L'échec d'ownership retourne 404, pas 403."""
        _, audit, _, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent 404v403",
        )
        r = client.get(
            f"/api/v1/audits/{audit.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404
        body_text = r.text.lower()
        for word in ("forbidden", "permission", "denied"):
            assert word not in body_text, f"Response must not contain '{word}'"

    def test_nonexistent_resource_same_404_as_unauthorized(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """Un 404 sur ressource inexistante a le même format qu'un 404 ownership."""
        _, audit, _, _ = _create_chain(
            db_session,
            auditeur_user,
            ent_name="Ent SameFmt",
        )
        # Ressource inexistante
        r1 = client.get("/api/v1/audits/99999", headers=second_auditeur_headers)
        # Ressource existante mais non autorisée
        r2 = client.get(
            f"/api/v1/audits/{audit.id}",
            headers=second_auditeur_headers,
        )
        assert r1.status_code == 404
        assert r2.status_code == 404
        # Même format JSON (mêmes clés)
        assert set(r1.json().keys()) == set(r2.json().keys())


# ══════════════════════════════════════════════════════════════════════
# I) ENTREPRISE PARTAGÉE — isolation des audits
# ══════════════════════════════════════════════════════════════════════


class TestSharedEntreprise:
    def test_shared_entreprise_audits_isolated(
        self,
        client,
        db_session,
        auditeur_user,
        auditeur_headers,
        second_auditeur_user,
        second_auditeur_headers,
    ):
        """Sur une entreprise partagée, chaque user ne voit que SON audit."""
        ent = Entreprise(nom="Ent Shared Audits", owner_id=auditeur_user.id)
        db_session.add(ent)
        db_session.flush()

        a_a = Audit(nom_projet="Shared Audit A", entreprise_id=ent.id, owner_id=auditeur_user.id)
        a_b = Audit(nom_projet="Shared Audit B", entreprise_id=ent.id, owner_id=second_auditeur_user.id)
        db_session.add_all([a_a, a_b])
        db_session.commit()
        db_session.refresh(a_a)
        db_session.refresh(a_b)

        # User A voit uniquement son audit
        r_a = client.get("/api/v1/audits", headers=auditeur_headers)
        ids_a = [a["id"] for a in r_a.json()["items"]]
        assert a_a.id in ids_a
        assert a_b.id not in ids_a

        # User B voit uniquement son audit
        r_b = client.get("/api/v1/audits", headers=second_auditeur_headers)
        ids_b = [a["id"] for a in r_b.json()["items"]]
        assert a_b.id in ids_b
        assert a_a.id not in ids_b

        # Les 2 voient l'entreprise
        r_ea = client.get("/api/v1/entreprises", headers=auditeur_headers)
        r_eb = client.get("/api/v1/entreprises", headers=second_auditeur_headers)
        noms_a = [e["nom"] for e in r_ea.json()["items"]]
        noms_b = [e["nom"] for e in r_eb.json()["items"]]
        assert ent.nom in noms_a
        assert ent.nom in noms_b

    def test_shared_entreprise_sites_visible_by_both(
        self,
        client,
        db_session,
        auditeur_user,
        auditeur_headers,
        second_auditeur_user,
        second_auditeur_headers,
    ):
        """Un site créé sur entreprise partagée est visible par les 2 users."""
        ent = Entreprise(nom="Ent Shared Sites", owner_id=auditeur_user.id)
        db_session.add(ent)
        db_session.flush()

        # Les 2 users ont un audit sur cette entreprise
        a_a = Audit(nom_projet="Shared Sites A", entreprise_id=ent.id, owner_id=auditeur_user.id)
        a_b = Audit(nom_projet="Shared Sites B", entreprise_id=ent.id, owner_id=second_auditeur_user.id)
        db_session.add_all([a_a, a_b])
        db_session.flush()

        site = Site(nom="Site Partagé", entreprise_id=ent.id)
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        # User A peut voir le site
        r_a = client.get(f"/api/v1/sites/{site.id}", headers=auditeur_headers)
        assert r_a.status_code == 200

        # User B peut aussi voir le site
        r_b = client.get(f"/api/v1/sites/{site.id}", headers=second_auditeur_headers)
        assert r_b.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# J) CONTRÔLE DE RÔLES
# ══════════════════════════════════════════════════════════════════════


class TestRoleControl:
    def test_lecteur_cannot_create_audit(
        self,
        client,
        lecteur_headers,
    ):
        """Le lecteur ne peut pas créer d'audit (403)."""
        r = client.post(
            "/api/v1/audits",
            json={"nom_projet": "Intrus", "entreprise_id": 1},
            headers=lecteur_headers,
        )
        assert r.status_code == 403

    def test_lecteur_can_list_own_audits(
        self,
        client,
        db_session,
        lecteur_user,
        lecteur_headers,
    ):
        """Un lecteur voit les audits dont il est owner."""
        ent = Entreprise(nom="Ent Lecteur", owner_id=lecteur_user.id)
        db_session.add(ent)
        db_session.flush()
        audit = Audit(
            nom_projet="Audit Lecteur",
            entreprise_id=ent.id,
            owner_id=lecteur_user.id,
        )
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(audit)

        r = client.get("/api/v1/audits", headers=lecteur_headers)
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()["items"]]
        assert audit.id in ids
