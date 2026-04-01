"""
Tests du logging des échecs d'ownership RBAC.

Vérifie que les access_denied produisent des WARNING structurés
sans leaker de données sensibles.
"""
import logging

from app.models.audit import Audit
from app.models.entreprise import Entreprise

SECURITY_LOGGER = "security"


class TestAccessDeniedLogging:

    def test_access_denied_logs_warning(
        self, client, db_session, auditeur_user, auditeur_headers,
        second_auditeur_user, second_auditeur_headers, caplog,
    ):
        """Un ownership failure produit un WARNING contenant 'access_denied'."""
        ent = Entreprise(nom="Ent Log Test", owner_id=auditeur_user.id)
        db_session.add(ent)
        db_session.flush()
        audit = Audit(nom_projet="Audit Log", entreprise_id=ent.id, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(audit)

        with caplog.at_level(logging.WARNING, logger=SECURITY_LOGGER):
            r = client.get(f"/api/v1/audits/{audit.id}", headers=second_auditeur_headers)

        assert r.status_code == 404
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("access_denied" in r.message for r in warnings)
        assert any(str(second_auditeur_user.id) in r.message for r in warnings)

    def test_access_denied_log_contains_resource_info(
        self, client, db_session, auditeur_user,
        second_auditeur_user, second_auditeur_headers, caplog,
    ):
        """Le log contient user_id de B, resource_type et resource_id."""
        ent = Entreprise(nom="Ent ResInfo", owner_id=auditeur_user.id)
        db_session.add(ent)
        db_session.flush()
        audit = Audit(nom_projet="Audit ResInfo", entreprise_id=ent.id, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(audit)

        with caplog.at_level(logging.WARNING, logger=SECURITY_LOGGER):
            client.get(f"/api/v1/audits/{audit.id}", headers=second_auditeur_headers)

        ad_logs = [r.message for r in caplog.records if "access_denied" in r.message]
        assert len(ad_logs) >= 1
        msg = ad_logs[0]
        assert str(second_auditeur_user.id) in msg
        assert "Audit" in msg
        assert str(audit.id) in msg

    def test_access_denied_log_no_sensitive_data(
        self, client, db_session, auditeur_user,
        second_auditeur_user, second_auditeur_headers, caplog,
    ):
        """Le log ne contient pas de données métier (nom_projet, owner_id de A comme user=)."""
        ent = Entreprise(nom="Ent NoLeak", owner_id=auditeur_user.id)
        db_session.add(ent)
        db_session.flush()
        audit = Audit(
            nom_projet="Projet Super Secret", entreprise_id=ent.id,
            owner_id=auditeur_user.id,
        )
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(audit)

        with caplog.at_level(logging.WARNING, logger=SECURITY_LOGGER):
            client.get(f"/api/v1/audits/{audit.id}", headers=second_auditeur_headers)

        ad_logs = [r.message for r in caplog.records if "access_denied" in r.message]
        assert len(ad_logs) >= 1
        msg = ad_logs[0]
        # Le nom du projet ne doit jamais apparaître dans le log
        assert "Projet Super Secret" not in msg
        # Le user= doit être celui qui tente l'accès (user B), pas le propriétaire (user A)
        assert f"user={second_auditeur_user.id}" in msg
        assert f"user={auditeur_user.id}" not in msg

    def test_nonexistent_resource_no_access_denied_log(
        self, client, second_auditeur_headers, caplog,
    ):
        """Un vrai 404 (ressource inexistante) ne produit pas de log access_denied."""
        with caplog.at_level(logging.WARNING, logger=SECURITY_LOGGER):
            r = client.get("/api/v1/audits/99999", headers=second_auditeur_headers)

        assert r.status_code == 404
        ad_logs = [r for r in caplog.records if "access_denied" in r.message]
        assert len(ad_logs) == 0

    def test_admin_bypass_no_access_denied_log(
        self, client, db_session, auditeur_user, admin_headers, caplog,
    ):
        """Un accès admin ne produit pas de log access_denied."""
        ent = Entreprise(nom="Ent Admin Bypass", owner_id=auditeur_user.id)
        db_session.add(ent)
        db_session.flush()
        audit = Audit(nom_projet="Audit Admin", entreprise_id=ent.id, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(audit)

        with caplog.at_level(logging.WARNING, logger=SECURITY_LOGGER):
            r = client.get(f"/api/v1/audits/{audit.id}", headers=admin_headers)

        assert r.status_code == 200
        ad_logs = [r for r in caplog.records if "access_denied" in r.message]
        assert len(ad_logs) == 0

    def test_entreprise_access_denied_logged(
        self, client, db_session, auditeur_user,
        second_auditeur_user, second_auditeur_headers, caplog,
    ):
        """Un échec d'accès entreprise produit un log avec 'Entreprise'."""
        ent = Entreprise(nom="Ent Priv", owner_id=auditeur_user.id)
        db_session.add(ent)
        db_session.flush()
        audit = Audit(nom_projet="Audit Ent", entreprise_id=ent.id, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(ent)

        with caplog.at_level(logging.WARNING, logger=SECURITY_LOGGER):
            r = client.get(f"/api/v1/entreprises/{ent.id}", headers=second_auditeur_headers)

        assert r.status_code == 404
        ad_logs = [r.message for r in caplog.records if "access_denied" in r.message]
        assert len(ad_logs) >= 1
        assert any("Entreprise" in m for m in ad_logs)
