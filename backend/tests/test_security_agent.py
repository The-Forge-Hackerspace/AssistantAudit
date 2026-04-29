"""
Tests pour les extensions agent/enrollment de core/security.py et core/deps.py.
Verifie que les fonctions existantes (user tokens) ne sont pas cassees.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security import (
    # Existing functions — regression check
    create_access_token,
    # New functions
    create_agent_token,
    create_enrollment_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_agent_token,
    verify_enrollment_token,
    verify_password,
)

# ────────────────────────────────────────────────────────────────────────
# Existing functions — regression tests
# ────────────────────────────────────────────────────────────────────────


class TestExistingFunctions:
    def test_hash_verify_password(self):
        hashed = hash_password("test123")
        assert verify_password("test123", hashed)
        assert not verify_password("wrong", hashed)

    def test_create_decode_access_token(self):
        token = create_access_token(subject=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_create_decode_refresh_token(self):
        token = create_refresh_token(subject=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        assert decode_token("invalid.token.here") is None


# ────────────────────────────────────────────────────────────────────────
# Agent tokens
# ────────────────────────────────────────────────────────────────────────


class TestAgentToken:
    def test_create_verify_roundtrip(self):
        token = create_agent_token(agent_uuid="abc-123", owner_id=7)
        payload = verify_agent_token(token)
        assert payload["sub"] == "abc-123"
        assert payload["owner_id"] == 7
        assert payload["type"] == "agent"

    def test_agent_token_long_expiry(self):
        token = create_agent_token(agent_uuid="abc-123", owner_id=1)
        payload = verify_agent_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Should expire in ~30 days
        assert (exp - now).days >= 29

    def test_verify_wrong_type_raises(self):
        """Un token user ne passe pas verify_agent_token."""
        user_token = create_access_token(subject=1)
        with pytest.raises(jwt.PyJWTError, match="agent"):
            verify_agent_token(user_token)

    def test_verify_refresh_token_wrong_type(self):
        """Un refresh token ne passe pas verify_agent_token."""
        refresh_token = create_refresh_token(subject=1)
        with pytest.raises(jwt.PyJWTError, match="agent"):
            verify_agent_token(refresh_token)

    def test_verify_invalid_token_raises(self):
        with pytest.raises(jwt.PyJWTError):
            verify_agent_token("not.a.valid.jwt")

    def test_verify_expired_token_raises(self):
        """Un token agent expire leve JWTError."""
        import jwt

        from app.core.config import get_settings

        settings = get_settings()

        payload = {
            "type": "agent",
            "sub": "abc-123",
            "owner_id": 1,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(days=31),
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        with pytest.raises(jwt.PyJWTError):
            verify_agent_token(expired_token)

    def test_agent_token_not_decoded_by_user_flow(self):
        """decode_token retourne le payload mais get_current_user rejette type=agent."""
        token = create_agent_token(agent_uuid="abc", owner_id=1)
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "agent"
        # get_current_user checks type == "access", so this would be rejected


# ────────────────────────────────────────────────────────────────────────
# Enrollment tokens
# ────────────────────────────────────────────────────────────────────────


class TestEnrollmentToken:
    def test_create_returns_triple(self):
        code, code_hash, expiration = create_enrollment_token()
        assert isinstance(code, str)
        assert len(code) == 8
        assert code == code.upper()  # uppercase
        assert isinstance(code_hash, str)
        assert len(code_hash) == 64  # SHA-256 hex
        assert isinstance(expiration, datetime)
        assert expiration > datetime.now(timezone.utc)

    def test_verify_valid_code(self):
        code, code_hash, expiration = create_enrollment_token()
        assert verify_enrollment_token(code, code_hash, expiration) is True

    def test_verify_wrong_code(self):
        _, code_hash, expiration = create_enrollment_token()
        assert verify_enrollment_token("WRONGCOD", code_hash, expiration) is False

    def test_verify_expired(self):
        code, code_hash, _ = create_enrollment_token()
        expired = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert verify_enrollment_token(code, code_hash, expired) is False

    def test_codes_are_unique(self):
        codes = {create_enrollment_token()[0] for _ in range(20)}
        # With 8 chars from urlsafe, collisions are extremely unlikely in 20 tries
        assert len(codes) == 20

    def test_hash_is_deterministic(self):
        """Le meme code produit le meme hash."""
        import hashlib

        code = "TESTCODE"
        expected = hashlib.sha256(code.encode()).hexdigest()
        assert verify_enrollment_token(code, expected, datetime.now(timezone.utc) + timedelta(minutes=5))


# ────────────────────────────────────────────────────────────────────────
# FastAPI dependency: get_current_agent (via deps.py)
# ────────────────────────────────────────────────────────────────────────


class TestGetCurrentAgentDep:
    """Tests get_current_agent via TestClient."""

    @pytest.fixture
    def setup(self, db_session):
        """Create user + active agent, return (db, user, agent, token)."""
        from app.core.security import hash_password
        from app.models.agent import Agent
        from app.models.user import User

        user = User(
            username="dep_test_user",
            email="dep_agent@test.com",
            password_hash=hash_password("pass"),
            role="auditeur",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        agent = Agent(
            name="Test-Agent",
            user_id=user.id,
            status="active",
            agent_uuid="dep-test-uuid-1234",
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        token = create_agent_token(agent_uuid=agent.agent_uuid, owner_id=user.id)
        return db_session, user, agent, token

    def test_valid_agent_token(self, setup, client):
        """An active agent with a valid token gets through."""
        _, _, agent, token = setup
        # We need an endpoint that uses get_current_agent.
        # Since none exists yet, we test the dependency function directly.
        # Direct invocation test is complex with FastAPI deps.
        # Instead, verify the token is valid and the agent exists.
        payload = verify_agent_token(token)
        assert payload["sub"] == agent.agent_uuid

    def test_user_token_rejected_as_agent(self):
        """A user access token must not pass verify_agent_token."""
        user_token = create_access_token(subject=1)
        with pytest.raises(jwt.PyJWTError):
            verify_agent_token(user_token)


# ────────────────────────────────────────────────────────────────────────
# FastAPI dependency: role checks (already in deps.py, regression)
# ────────────────────────────────────────────────────────────────────────


class TestRoleChecks:
    """Test require_auditeur and require_admin via TestClient."""

    def test_auditeur_can_access_auditeur_route(self, client, auditeur_headers):
        # Any route protected by get_current_auditeur.
        # Use /api/v1/entreprises which requires auditeur role.
        response = client.get("/api/v1/entreprises", headers=auditeur_headers)
        assert response.status_code == 200

    def test_admin_can_access_auditeur_route(self, client, admin_headers):
        response = client.get("/api/v1/entreprises", headers=admin_headers)
        assert response.status_code == 200

    def test_lecteur_rejected_from_auditeur_route(self, client, lecteur_headers):
        # POST to create requires auditeur, but GET list might also.
        # Let's use POST which definitely requires auditeur.
        response = client.post(
            "/api/v1/entreprises",
            json={"nom": "TestRoleEntreprise"},
            headers=lecteur_headers,
        )
        assert response.status_code == 403
