"""Tests des events d'auth structurés (TOS-82)."""

import logging


def test_login_attempt_emits_structured_event_without_username(client, auditeur_user, caplog):
    """Le router /auth/login émet un event structuré avec username_hash, pas de username clair."""
    with caplog.at_level(logging.INFO, logger="app.api.v1.auth"):
        client.post(
            "/api/v1/auth/login",
            data={"username": auditeur_user.username, "password": "AuditeurPass1!"},
        )

    login_attempts = [r for r in caplog.records if getattr(r, "event", None) == "login_attempt"]
    assert login_attempts, "login_attempt event manquant dans caplog"
    rec = login_attempts[0]
    # Username_hash présent et de longueur 12
    assert getattr(rec, "username_hash", None)
    assert len(rec.username_hash) == 12
    # Aucun champ ne doit contenir le username en clair
    assert auditeur_user.username not in rec.message
    for k, v in vars(rec).items():
        if isinstance(v, str):
            assert auditeur_user.username not in v, f"username clair fuite dans champ {k}"


def test_login_failure_logged_with_username_hash(client, caplog):
    """Un échec de login émet event login_failure avec username_hash et reason."""
    with caplog.at_level(logging.WARNING, logger="app.services.auth_service"):
        client.post(
            "/api/v1/auth/login",
            data={"username": "ghost_user", "password": "wrong"},
        )

    failures = [r for r in caplog.records if getattr(r, "event", None) == "login_failure"]
    assert failures, "login_failure event manquant"
    rec = failures[0]
    assert getattr(rec, "username_hash", None)
    assert getattr(rec, "reason", None) in {"bad_credentials", "account_disabled"}
    # Pas de username clair
    assert "ghost_user" not in rec.message
    for k, v in vars(rec).items():
        if isinstance(v, str):
            assert "ghost_user" not in v


def test_login_success_emits_structured_event(client, auditeur_user, caplog):
    """Login réussi émet login_success avec user_id."""
    with caplog.at_level(logging.INFO, logger="app.services.auth_service"):
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": auditeur_user.username, "password": "AuditeurPass1!"},
        )
    assert resp.status_code == 200
    successes = [r for r in caplog.records if getattr(r, "event", None) == "login_success"]
    assert successes
    assert successes[0].user_id == auditeur_user.id
