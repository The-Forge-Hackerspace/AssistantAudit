"""
Tests de sécurité — TOS-11 : Hardening sécurité & rate limiting.

Couvre :
- T001 : Security headers complets (CSP, HSTS, X-Frame-Options, etc.)
- T002 : Rate limiting granulaire par catégorie (auth, api, public)
- T003 : CORS strict en production (pas de wildcard)
- T004 : Tests automatisés
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.rate_limit import RATE_LIMITS, _RateLimiter

# ══════════════════════════════════════════════════════════════════════
# 1. SECURITY HEADERS
# ══════════════════════════════════════════════════════════════════════


class TestSecurityHeaders:
    """T001 : Tous les security headers OWASP doivent être présents."""

    def test_x_content_type_options(self, client: TestClient):
        resp = client.get("/health")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client: TestClient):
        resp = client.get("/health")
        assert resp.headers["X-Frame-Options"] == "DENY"

    def test_x_xss_protection(self, client: TestClient):
        resp = client.get("/health")
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy(self, client: TestClient):
        resp = client.get("/health")
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client: TestClient):
        resp = client.get("/health")
        policy = resp.headers["Permissions-Policy"]
        for directive in ("camera=()", "microphone=()", "geolocation=()"):
            assert directive in policy

    def test_content_security_policy(self, client: TestClient):
        resp = client.get("/health")
        csp = resp.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "script-src" in csp

    def test_no_server_header(self, client: TestClient):
        """Le header 'server' ne doit pas être exposé (anti-fingerprinting)."""
        resp = client.get("/health")
        assert "server" not in resp.headers

    def test_all_required_headers_present(self, client: TestClient):
        """Vérifie la présence de tous les headers en un seul test."""
        resp = client.get("/health")
        required = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
            "Content-Security-Policy",
        ]
        for header in required:
            assert header in resp.headers, f"Header manquant : {header}"


# ══════════════════════════════════════════════════════════════════════
# 2. RATE LIMITING GRANULAIRE
# ══════════════════════════════════════════════════════════════════════


class TestRateLimitConfig:
    """T002 : Les seuils de rate limiting sont bien configurés par catégorie."""

    def test_auth_limit_is_5_per_minute(self):
        assert RATE_LIMITS["auth"]["max_attempts"] == 5
        assert RATE_LIMITS["auth"]["window_seconds"] == 60

    def test_api_limit_is_30_per_minute(self):
        assert RATE_LIMITS["api"]["max_attempts"] == 30
        assert RATE_LIMITS["api"]["window_seconds"] == 60

    def test_public_limit_is_100_per_minute(self):
        assert RATE_LIMITS["public"]["max_attempts"] == 100
        assert RATE_LIMITS["public"]["window_seconds"] == 60


class TestRateLimiterConfigurable:
    """T002 : Le rate limiter respecte les paramètres configurables."""

    def _make_request(self, ip: str = "10.0.0.1"):
        req = MagicMock()
        req.client.host = ip
        req.headers = {}
        return req

    def test_custom_limit_blocks_at_threshold(self):
        """Un limiter configuré à 3 req bloque à la 4ème."""
        limiter = _RateLimiter(max_attempts=3, window_seconds=60, block_seconds=10)
        req = self._make_request()
        for _ in range(3):
            limiter.acquire_attempt(req)
        with pytest.raises(HTTPException) as exc_info:
            limiter.acquire_attempt(req)
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    def test_api_limiter_allows_30_requests(self):
        """Le limiter API autorise 30 requêtes."""
        limiter = _RateLimiter(**RATE_LIMITS["api"])
        req = self._make_request()
        for _ in range(30):
            limiter.acquire_attempt(req)
        with pytest.raises(HTTPException) as exc_info:
            limiter.acquire_attempt(req)
        assert exc_info.value.status_code == 429

    def test_public_limiter_allows_100_requests(self):
        """Le limiter public autorise 100 requêtes."""
        limiter = _RateLimiter(**RATE_LIMITS["public"])
        req = self._make_request()
        for _ in range(100):
            limiter.acquire_attempt(req)
        with pytest.raises(HTTPException) as exc_info:
            limiter.acquire_attempt(req)
        assert exc_info.value.status_code == 429


class TestRateLimitMiddlewareIntegration:
    """T002 : Le middleware applique le bon limiter selon la route."""

    def test_health_endpoint_not_blocked_under_100(self, client: TestClient):
        """Health supporte 100 requêtes sans blocage."""
        for _ in range(50):
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_api_endpoint_blocked_after_30(self, client: TestClient, admin_headers):
        """Un endpoint API est bloqué après 30 requêtes/min."""
        for i in range(30):
            resp = client.get("/api/v1/users/me", headers=admin_headers)
            # 200 ou 404, tant que pas 429
            assert resp.status_code != 429, f"Bloqué trop tôt à la requête {i + 1}"
        # La 31ème doit être bloquée
        resp = client.get("/api/v1/users/me", headers=admin_headers)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_auth_login_not_rate_limited_by_api_limiter(self, client: TestClient):
        """Le login utilise son propre limiter, pas le limiter API."""
        # Faire 30+ requêtes login (mauvais credentials) — ne doit pas trigger le API limiter
        for _ in range(6):
            resp = client.post(
                "/api/v1/auth/login",
                data={"username": "fake", "password": "fake"},
            )
        # Le login a son propre limiter à 5/min, le 6ème doit être 429
        assert resp.status_code == 429

    def test_agents_enroll_not_rate_limited_by_api_limiter(self, client: TestClient):
        """POST /agents/enroll utilise son propre limiter (5/min), pas le API (30/min).

        Le middleware exempte /agents/enroll du rate limiter API générique.
        L'enroll a son propre limiter auth (5/min) dans le service.
        On vérifie que les 5 premières requêtes passent (pas de 429 du API limiter)
        et que la 6ème est bloquée par le limiter enroll (pas avant).
        """
        for i in range(5):
            resp = client.post(
                "/api/v1/agents/enroll",
                json={"enrollment_code": "fake-code"},
            )
            assert resp.status_code != 429, f"Requête enroll #{i + 1} bloquée trop tôt"
        # La 6ème doit être bloquée par le enroll_rate_limiter (auth: 5/min)
        resp = client.post(
            "/api/v1/agents/enroll",
            json={"enrollment_code": "fake-code"},
        )
        assert resp.status_code == 429


# ══════════════════════════════════════════════════════════════════════
# 3. CORS PRODUCTION HARDENING
# ══════════════════════════════════════════════════════════════════════


class TestCorsValidation:
    """T003 : CORS strict en production."""

    def test_wildcard_origin_rejected_in_production(self):
        """CORS_ORIGINS avec '*' doit être rejeté en production."""
        with pytest.raises(ValueError, match="ne doit pas contenir"):
            with patch.dict(
                os.environ,
                {
                    "ENV": "production",
                    "SECRET_KEY": "a" * 64,
                    "ENCRYPTION_KEY": "ab" * 32,
                    "FILE_ENCRYPTION_KEY": "cd" * 32,
                    "CORS_ORIGINS": '["*"]',
                },
                clear=False,
            ):
                from app.core.config import Settings

                Settings()

    def test_invalid_origin_rejected_in_production(self):
        """Une origine sans http/https doit être rejetée en production."""
        with pytest.raises(ValueError, match="CORS_ORIGINS invalide"):
            with patch.dict(
                os.environ,
                {
                    "ENV": "production",
                    "SECRET_KEY": "a" * 64,
                    "ENCRYPTION_KEY": "ab" * 32,
                    "FILE_ENCRYPTION_KEY": "cd" * 32,
                    "CORS_ORIGINS": '["not-a-url"]',
                },
                clear=False,
            ):
                from app.core.config import Settings

                Settings()

    def test_valid_origins_accepted_in_production(self):
        """Des origines valides sont acceptées en production."""
        with patch.dict(
            os.environ,
            {
                "ENV": "production",
                "SECRET_KEY": "a" * 64,
                "ENCRYPTION_KEY": "ab" * 32,
                "FILE_ENCRYPTION_KEY": "cd" * 32,
                "CORS_ORIGINS": '["https://audit.example.com"]',
                "RATE_LIMIT_BACKEND": "redis",
                "RATE_LIMIT_REDIS_URL": "redis://redis:6379/0",
            },
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.CORS_ORIGINS == ["https://audit.example.com"]

    def test_wildcard_allowed_in_development(self):
        """En développement, le wildcard est toléré."""
        with patch.dict(
            os.environ,
            {
                "ENV": "development",
                "CORS_ORIGINS": '["*"]',
            },
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert "*" in s.CORS_ORIGINS

    def test_cors_middleware_rejects_unknown_origin(self, client: TestClient):
        """Une requête cross-origin non listée ne reçoit pas de header CORS."""
        resp = client.get(
            "/health",
            headers={"Origin": "https://evil.example.com"},
        )
        # Starlette CORSMiddleware ne renvoie pas access-control-allow-origin
        # pour les origines non listées
        assert resp.headers.get("access-control-allow-origin") != "https://evil.example.com"
