"""
Tests pour POST /auth/refresh et validate_refresh_token.
"""

from datetime import timedelta

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
)

# ────────────────────────────────────────────────────────────────────────
# validate_refresh_token — Tests unitaires
# ────────────────────────────────────────────────────────────────────────


class TestValidateRefreshToken:
    """Tests de la fonction validate_refresh_token."""

    def test_valid_refresh_token(self, auditeur_user):
        """Un refresh token valide retourne le payload."""
        token = create_refresh_token(subject=auditeur_user.id)
        payload = validate_refresh_token(token)
        assert payload["sub"] == str(auditeur_user.id)
        assert payload["type"] == "refresh"

    def test_access_token_rejected(self, auditeur_user):
        """Un access token est refuse (mauvais type)."""
        token = create_access_token(subject=auditeur_user.id)
        with pytest.raises(JWTError, match="refresh"):
            validate_refresh_token(token)

    def test_expired_token_rejected(self, auditeur_user):
        """Un refresh token expire est refuse."""
        from datetime import datetime, timezone

        from jose import jwt

        from app.core.config import get_settings

        settings = get_settings()
        payload = {
            "sub": str(auditeur_user.id),
            "type": "refresh",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(JWTError):
            validate_refresh_token(token)

    def test_garbage_token_rejected(self):
        """Un token invalide est refuse."""
        with pytest.raises(JWTError):
            validate_refresh_token("not.a.valid.token")


# ────────────────────────────────────────────────────────────────────────
# POST /auth/refresh — Tests d'integration
# ────────────────────────────────────────────────────────────────────────


class TestRefreshEndpoint:
    """Tests de l'endpoint POST /api/v1/auth/refresh."""

    def test_refresh_success(self, client, auditeur_user):
        """Un refresh token valide retourne de nouveaux tokens."""
        refresh_token = create_refresh_token(subject=auditeur_user.id)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_access_token_fails(self, client, auditeur_user):
        """Un access token ne doit pas etre accepte comme refresh token."""
        access_token = create_access_token(subject=auditeur_user.id)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401

    def test_refresh_with_invalid_token_fails(self, client):
        """Un token invalide retourne 401."""
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_refresh_inactive_user_fails(self, client, auditeur_user, db_session):
        """Un utilisateur desactive ne peut pas rafraichir ses tokens."""
        refresh_token = create_refresh_token(subject=auditeur_user.id)
        # Desactiver l'utilisateur
        auditeur_user.is_active = False
        db_session.commit()

        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401
        assert "desactive" in resp.json()["detail"].lower()

    def test_refresh_nonexistent_user_fails(self, client):
        """Un refresh token pour un user inexistant retourne 401."""
        refresh_token = create_refresh_token(subject=99999)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401

    def test_refresh_missing_body_fails(self, client):
        """Sans cookie ni body, l'endpoint retourne 401 (token requis)."""
        # Le refresh_token est desormais optionnel dans le body : il peut etre lu
        # depuis le cookie httpOnly aa_refresh_token. Sans aucune source -> 401.
        resp = client.post("/api/v1/auth/refresh", json={})
        assert resp.status_code == 401

    def test_login_returns_refresh_token(self, client, auditeur_user):
        """Les endpoints login retournent un refresh_token."""
        resp = client.post(
            "/api/v1/auth/login/json",
            json={"username": "auditeur_test", "password": "AuditeurPass1!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "refresh_token" in data
        assert len(data["refresh_token"]) > 0

    def test_full_flow_login_then_refresh(self, client, auditeur_user):
        """Flow complet : login → refresh → access valide."""
        # Login
        login_resp = client.post(
            "/api/v1/auth/login/json",
            json={"username": "auditeur_test", "password": "AuditeurPass1!"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        new_access = refresh_resp.json()["access_token"]

        # Utiliser le nouveau access token
        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "auditeur_test"


    # ────────────────────────────────────────────────────────────────────────
    # Sources du refresh_token : cookie httpOnly, body legacy, precedence
    # ────────────────────────────────────────────────────────────────────────

    def test_refresh_via_cookie_only(self, client, auditeur_user):
        """Cookie aa_refresh_token seul (body vide) -> 200 + nouveaux cookies."""
        token = create_refresh_token(subject=auditeur_user.id)
        client.cookies.set("aa_refresh_token", token)
        resp = client.post("/api/v1/auth/refresh", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        # Les nouveaux cookies sont poses par le serveur
        assert "aa_access_token" in resp.cookies
        assert "aa_refresh_token" in resp.cookies

    def test_refresh_via_body_only_legacy_client(self, client, auditeur_user):
        """Body legacy sans cookie -> 200 (compat scripts/agents)."""
        token = create_refresh_token(subject=auditeur_user.id)
        # Pas de cookie : le test client part avec un jar vide
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    def test_refresh_cookie_takes_precedence_over_body(self, client, auditeur_user):
        """Si cookie ET body sont presents, le cookie prime (auth principale)."""
        valid_cookie_token = create_refresh_token(subject=auditeur_user.id)
        # Si le body etait utilise en priorite, /refresh renverrait 401 sur ce token
        invalid_body_token = "definitely.invalid.token"
        client.cookies.set("aa_refresh_token", valid_cookie_token)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": invalid_body_token},
        )
        assert resp.status_code == 200, (
            "le cookie aurait du etre utilise en priorite, pas le body invalide"
        )
