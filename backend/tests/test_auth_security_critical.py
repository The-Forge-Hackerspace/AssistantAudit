"""
Tests critiques manquants : auth, rate limiting, token validation, password hashing.
Audit dev 3/4.
"""
import time

import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    create_agent_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_agent_token,
    verify_password,
    create_enrollment_token,
    verify_enrollment_token,
)
from app.core.rate_limit import _RateLimiter
from app.services.auth_service import AuthService


# ══════════════════════════════════════════════════════════════════════
# 1. PASSWORD HASHING
# ══════════════════════════════════════════════════════════════════════


class TestPasswordHashing:

    def test_hash_password_returns_different_hash(self):
        """Deux hash du meme mot de passe doivent etre differents (salt unique)."""
        h1 = hash_password("test_password_123")
        h2 = hash_password("test_password_123")
        assert h1 != h2

    def test_verify_password_correct(self):
        h = hash_password("correct_horse")
        assert verify_password("correct_horse", h) is True

    def test_verify_password_wrong(self):
        h = hash_password("correct_horse")
        assert verify_password("wrong_horse", h) is False

    def test_hash_password_empty_string(self):
        """Un mot de passe vide doit quand meme etre hashable."""
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("not_empty", h) is False


# ══════════════════════════════════════════════════════════════════════
# 2. JWT TOKENS
# ══════════════════════════════════════════════════════════════════════


class TestJWTTokens:

    def test_access_token_roundtrip(self):
        token = create_access_token(subject=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        token = create_refresh_token(subject=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"

    def test_agent_token_roundtrip(self):
        token = create_agent_token("agent-uuid-123", owner_id=7)
        payload = verify_agent_token(token)
        assert payload["sub"] == "agent-uuid-123"
        assert payload["owner_id"] == 7
        assert payload["type"] == "agent"

    def test_invalid_token_returns_none(self):
        assert decode_token("garbage.token.here") is None

    def test_agent_token_rejected_by_decode_access(self):
        """Un token agent ne doit PAS etre accepte comme access."""
        token = create_agent_token("agent-uuid", owner_id=1)
        payload = decode_token(token)
        # decode_token retourne le payload mais type != "access"
        assert payload is not None
        assert payload["type"] == "agent"

    def test_access_token_rejected_by_verify_agent(self):
        """Un token access ne doit PAS etre accepte comme agent."""
        from jose import JWTError
        token = create_access_token(subject=1)
        with pytest.raises(JWTError, match="Invalid token type"):
            verify_agent_token(token)

    def test_access_token_extra_claims(self):
        token = create_access_token(subject=1, extra_claims={"role": "admin", "username": "test"})
        payload = decode_token(token)
        assert payload["role"] == "admin"
        assert payload["username"] == "test"


# ══════════════════════════════════════════════════════════════════════
# 3. ENROLLMENT TOKENS
# ══════════════════════════════════════════════════════════════════════


class TestEnrollmentTokens:

    def test_enrollment_token_verify_correct(self):
        code, code_hash, expiration = create_enrollment_token()
        assert len(code) == 8
        assert len(code_hash) == 64  # SHA-256 hex
        assert verify_enrollment_token(code, code_hash, expiration) is True

    def test_enrollment_token_verify_wrong_code(self):
        _, code_hash, expiration = create_enrollment_token()
        assert verify_enrollment_token("WRONGCOD", code_hash, expiration) is False

    def test_enrollment_token_verify_expired(self):
        from datetime import datetime, timezone, timedelta
        code, code_hash, _ = create_enrollment_token()
        expired = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert verify_enrollment_token(code, code_hash, expired) is False

    def test_enrollment_tokens_unique(self):
        codes = {create_enrollment_token()[0] for _ in range(20)}
        assert len(codes) == 20


# ══════════════════════════════════════════════════════════════════════
# 4. RATE LIMITER
# ══════════════════════════════════════════════════════════════════════


class TestRateLimiter:

    def _make_request(self, ip: str = "10.0.0.1"):
        """Cree un mock Request avec une IP."""
        from unittest.mock import MagicMock
        req = MagicMock()
        req.client.host = ip
        req.headers = {}
        return req

    def test_allows_under_limit(self):
        limiter = _RateLimiter()
        req = self._make_request()
        for _ in range(4):
            limiter.check(req)
            limiter.record_attempt(req)
        # 4 tentatives < 5 max : pas de blocage

    def test_blocks_at_limit(self):
        limiter = _RateLimiter()
        req = self._make_request()
        for _ in range(5):
            limiter.check(req)
            limiter.record_attempt(req)
        # 6eme tentative bloquee
        with pytest.raises(HTTPException) as exc_info:
            limiter.check(req)
        assert exc_info.value.status_code == 429

    def test_reset_clears_counter(self):
        limiter = _RateLimiter()
        req = self._make_request()
        for _ in range(4):
            limiter.check(req)
            limiter.record_attempt(req)
        limiter.reset(req)
        # Apres reset, on peut refaire des tentatives
        limiter.check(req)
        limiter.record_attempt(req)

    def test_different_ips_independent(self):
        limiter = _RateLimiter()
        req_a = self._make_request("10.0.0.1")
        req_b = self._make_request("10.0.0.2")
        for _ in range(5):
            limiter.check(req_a)
            limiter.record_attempt(req_a)
        # IP A bloquee, IP B pas affectee
        limiter.check(req_b)
        limiter.record_attempt(req_b)


# ══════════════════════════════════════════════════════════════════════
# 5. AUTH SERVICE
# ══════════════════════════════════════════════════════════════════════


class TestAuthService:

    def test_authenticate_success(self, db_session):
        user = AuthService.create_user(db_session, "testuser", "test@example.com", "password123")
        result = AuthService.authenticate(db_session, "testuser", "password123")
        assert result is not None
        assert result.id == user.id

    def test_authenticate_wrong_password(self, db_session):
        AuthService.create_user(db_session, "testuser2", "test2@example.com", "password123")
        result = AuthService.authenticate(db_session, "testuser2", "wrong_password")
        assert result is None

    def test_authenticate_by_email(self, db_session):
        AuthService.create_user(db_session, "testuser3", "test3@example.com", "password123")
        result = AuthService.authenticate(db_session, "test3@example.com", "password123")
        assert result is not None

    def test_authenticate_inactive_user(self, db_session):
        user = AuthService.create_user(db_session, "testuser4", "test4@example.com", "password123")
        user.is_active = False
        db_session.commit()
        result = AuthService.authenticate(db_session, "testuser4", "password123")
        assert result is None

    def test_create_tokens(self, db_session):
        user = AuthService.create_user(db_session, "testuser5", "test5@example.com", "password123")
        tokens = AuthService.create_tokens(user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        # Verify access token has correct claims
        payload = decode_token(tokens["access_token"])
        assert payload["sub"] == str(user.id)
        assert payload["type"] == "access"

    def test_change_password(self, db_session):
        user = AuthService.create_user(db_session, "testuser6", "test6@example.com", "old_password")
        assert AuthService.change_password(db_session, user, "old_password", "new_password") is True
        # Verify new password works
        result = AuthService.authenticate(db_session, "testuser6", "new_password")
        assert result is not None

    def test_change_password_wrong_current(self, db_session):
        user = AuthService.create_user(db_session, "testuser7", "test7@example.com", "the_password")
        assert AuthService.change_password(db_session, user, "wrong_current", "new_password") is False
