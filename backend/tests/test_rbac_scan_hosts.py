"""
Tests RBAC — isolation des opérations sur les hosts et lancement de scan.

Vérifie que decide_host, link_host, import_all_hosts et launch_scan
respectent l'ownership (host → scan → ScanReseau.owner_id pour les hosts,
Site → Entreprise → Audit.owner_id pour le lancement).
"""
import pytest
from app.models.entreprise import Entreprise
from app.models.audit import Audit
from app.models.site import Site
from app.models.equipement import Equipement
from app.models.scan import ScanReseau, ScanHost


# ── Helpers ──────────────────────────────────────────────────────────

def _create_site_with_ownership(db, owner, *, ent_name):
    """Crée la chaîne entreprise → audit (ownership) → site pour un owner donné."""
    ent = Entreprise(nom=ent_name, owner_id=owner.id)
    db.add(ent)
    db.flush()
    audit = Audit(nom_projet=f"Audit {ent_name}", entreprise_id=ent.id, owner_id=owner.id)
    db.add(audit)
    db.flush()
    site = Site(nom=f"Site {ent_name}", entreprise_id=ent.id)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def _create_scan_with_host(db, owner, *, ent_name, ip="10.0.0.1"):
    """Crée la chaîne entreprise → site → scan → host pour un owner donné."""
    ent = Entreprise(nom=ent_name, owner_id=owner.id)
    db.add(ent)
    db.flush()
    site = Site(nom=f"Site {ent_name}", entreprise_id=ent.id)
    db.add(site)
    db.flush()
    scan = ScanReseau(
        site_id=site.id, owner_id=owner.id,
        type_scan="discovery", statut="completed",
    )
    db.add(scan)
    db.flush()
    host = ScanHost(
        scan_id=scan.id, ip_address=ip,
        status="up", decision="pending",
    )
    db.add(host)
    db.commit()
    db.refresh(scan)
    db.refresh(host)
    return scan, host


# ══════════════════════════════════════════════════════════════════════
# decide_host — PUT /scans/hosts/{host_id}/decision
# ══════════════════════════════════════════════════════════════════════


class TestDecideHostIsolation:

    def test_owner_can_decide_own_host(
        self, client, db_session, auditeur_user, auditeur_headers,
    ):
        """Non-régression : un auditeur peut décider sur ses propres hosts."""
        _, host = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent DecideOwn",
        )
        r = client.put(
            f"/api/v1/scans/hosts/{host.id}/decision",
            json={"decision": "kept"},
            headers=auditeur_headers,
        )
        assert r.status_code == 200
        assert r.json()["decision"] == "kept"

    def test_other_user_decide_host_returns_404(
        self, client, db_session, auditeur_user,
        second_auditeur_headers,
    ):
        """Auditeur B ne peut pas modifier la décision d'un host d'auditeur A."""
        _, host = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent DecideCross",
        )
        r = client.put(
            f"/api/v1/scans/hosts/{host.id}/decision",
            json={"decision": "ignored"},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_can_decide_any_host(
        self, client, db_session, auditeur_user, admin_headers,
    ):
        """L'admin peut modifier la décision sur n'importe quel host."""
        _, host = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent DecideAdmin",
        )
        r = client.put(
            f"/api/v1/scans/hosts/{host.id}/decision",
            json={"decision": "ignored"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["decision"] == "ignored"


# ══════════════════════════════════════════════════════════════════════
# link_host — POST /scans/hosts/{host_id}/link/{equipement_id}
# ══════════════════════════════════════════════════════════════════════


class TestLinkHostIsolation:

    def test_owner_can_link_own_host(
        self, client, db_session, auditeur_user, auditeur_headers,
    ):
        """Non-régression : un auditeur peut lier ses propres hosts."""
        scan, host = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent LinkOwn",
        )
        equip = Equipement(
            site_id=scan.site_id, type_equipement="serveur",
            ip_address="10.0.0.99",
        )
        db_session.add(equip)
        db_session.commit()
        db_session.refresh(equip)

        r = client.post(
            f"/api/v1/scans/hosts/{host.id}/link/{equip.id}",
            headers=auditeur_headers,
        )
        assert r.status_code == 200
        assert r.json()["equipement_id"] == equip.id

    def test_other_user_link_host_returns_404(
        self, client, db_session, auditeur_user,
        second_auditeur_headers,
    ):
        """Auditeur B ne peut pas lier un host d'auditeur A à un équipement."""
        scan, host = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent LinkCross",
        )
        equip = Equipement(
            site_id=scan.site_id, type_equipement="serveur",
            ip_address="10.0.0.88",
        )
        db_session.add(equip)
        db_session.commit()
        db_session.refresh(equip)

        r = client.post(
            f"/api/v1/scans/hosts/{host.id}/link/{equip.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_can_link_any_host(
        self, client, db_session, auditeur_user, admin_headers,
    ):
        """L'admin peut lier n'importe quel host."""
        scan, host = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent LinkAdmin",
        )
        equip = Equipement(
            site_id=scan.site_id, type_equipement="serveur",
            ip_address="10.0.0.77",
        )
        db_session.add(equip)
        db_session.commit()
        db_session.refresh(equip)

        r = client.post(
            f"/api/v1/scans/hosts/{host.id}/link/{equip.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# import_all_hosts — POST /scans/{scan_id}/import-all
# ══════════════════════════════════════════════════════════════════════


class TestImportAllHostsIsolation:

    def test_owner_can_import_own_scan(
        self, client, db_session, auditeur_user, auditeur_headers,
    ):
        """Non-régression : un auditeur peut importer les hosts de son scan."""
        scan, _ = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent ImportOwn",
        )
        r = client.post(
            f"/api/v1/scans/{scan.id}/import-all",
            headers=auditeur_headers,
        )
        assert r.status_code == 200
        assert "créé" in r.json()["message"]

    def test_other_user_import_returns_404(
        self, client, db_session, auditeur_user,
        second_auditeur_headers,
    ):
        """Auditeur B ne peut pas importer les hosts du scan d'auditeur A."""
        scan, _ = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent ImportCross",
        )
        r = client.post(
            f"/api/v1/scans/{scan.id}/import-all",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_can_import_any_scan(
        self, client, db_session, auditeur_user, admin_headers,
    ):
        """L'admin peut importer les hosts de n'importe quel scan."""
        scan, _ = _create_scan_with_host(
            db_session, auditeur_user, ent_name="Ent ImportAdmin",
        )
        r = client.post(
            f"/api/v1/scans/{scan.id}/import-all",
            headers=admin_headers,
        )
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# launch_scan — POST /scans (ownership via Site → Entreprise → Audit)
# ══════════════════════════════════════════════════════════════════════


class TestLaunchScanIsolation:

    def test_owner_can_launch_scan_on_own_site(
        self, client, db_session, auditeur_user, auditeur_headers,
    ):
        """Non-régression : un auditeur peut lancer un scan sur son propre site."""
        site = _create_site_with_ownership(
            db_session, auditeur_user, ent_name="Ent LaunchOwn",
        )
        r = client.post(
            "/api/v1/scans",
            json={"site_id": site.id, "target": "192.168.1.0/24", "scan_type": "discovery"},
            headers=auditeur_headers,
        )
        assert r.status_code == 202

    def test_other_user_launch_scan_returns_404(
        self, client, db_session, auditeur_user,
        second_auditeur_headers,
    ):
        """Auditeur B ne peut pas lancer un scan sur le site d'auditeur A."""
        site = _create_site_with_ownership(
            db_session, auditeur_user, ent_name="Ent LaunchCross",
        )
        r = client.post(
            "/api/v1/scans",
            json={"site_id": site.id, "target": "192.168.1.0/24", "scan_type": "discovery"},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_can_launch_scan_on_any_site(
        self, client, db_session, auditeur_user, admin_headers,
    ):
        """L'admin peut lancer un scan sur n'importe quel site."""
        site = _create_site_with_ownership(
            db_session, auditeur_user, ent_name="Ent LaunchAdmin",
        )
        r = client.post(
            "/api/v1/scans",
            json={"site_id": site.id, "target": "192.168.1.0/24", "scan_type": "discovery"},
            headers=admin_headers,
        )
        assert r.status_code == 202
