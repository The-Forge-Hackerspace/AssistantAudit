"""Tests du rate-limiter à backend pluggable (TOS-77 / S-004).

Couvre :
- MemoryBackend mono-process (régression du comportement actuel).
- RedisBackend avec un faux client compatible (parité multi-worker).
- Boot-time guard de Settings : `ENV=production` + `RATE_LIMIT_BACKEND=memory`
  doit refuser de démarrer.
- Sélection du backend par `RATE_LIMIT_BACKEND`.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

import pytest

from app.core import rate_limit
from app.core.rate_limit import (
    MemoryBackend,
    RedisBackend,
    _RateLimiter,
    _reset_backend_for_tests,
)

# ── Fakes / Helpers ───────────────────────────────────────────────────────────


class _FakePipeline:
    def __init__(self, parent: "_FakeRedis") -> None:
        self._parent = parent
        self._ops: list[tuple[str, tuple[Any, ...]]] = []

    def incr(self, key: str) -> "_FakePipeline":
        self._ops.append(("incr", (key,)))
        return self

    def expire(self, key: str, seconds: int, nx: bool = False) -> "_FakePipeline":
        self._ops.append(("expire", (key, seconds, nx)))
        return self

    def set(self, key: str, value: str, ex: int | None = None) -> "_FakePipeline":
        self._ops.append(("set", (key, value, ex)))
        return self

    def delete(self, *keys: str) -> "_FakePipeline":
        self._ops.append(("delete", keys))
        return self

    def execute(self) -> list[Any]:
        results: list[Any] = []
        for op, args in self._ops:
            results.append(getattr(self._parent, op)(*args))
        self._ops.clear()
        return results


class _FakeRedis:
    """Client Redis minimaliste, partagé entre workers fictifs.

    Implémente uniquement la surface utilisée par `RedisBackend` :
    `ttl`, `incr`, `expire`, `set`, `delete`, `scan_iter`, `pipeline`.
    Les TTL sont calculés via `time.time()` ; aucune horloge mockée.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._expiry: dict[str, float] = {}
        self._lock = Lock()

    def _expired(self, key: str, now: float) -> bool:
        exp = self._expiry.get(key)
        return exp is not None and exp <= now

    def _purge(self, now: float) -> None:
        for k in [k for k in list(self._expiry) if self._expired(k, now)]:
            self._store.pop(k, None)
            self._expiry.pop(k, None)

    def ttl(self, key: str) -> int:
        with self._lock:
            now = time.time()
            self._purge(now)
            if key not in self._store:
                return -2
            if key not in self._expiry:
                return -1
            return max(0, int(self._expiry[key] - now))

    def incr(self, key: str) -> int:
        with self._lock:
            now = time.time()
            self._purge(now)
            new = int(self._store.get(key, "0")) + 1
            self._store[key] = str(new)
            return new

    def expire(self, key: str, seconds: int, nx: bool = False) -> int:
        with self._lock:
            if key not in self._store:
                return 0
            if nx and key in self._expiry:
                return 0
            self._expiry[key] = time.time() + seconds
            return 1

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        with self._lock:
            self._store[key] = value
            if ex is not None:
                self._expiry[key] = time.time() + ex
            else:
                self._expiry.pop(key, None)
            return True

    def delete(self, *keys: str) -> int:
        with self._lock:
            n = 0
            for k in keys:
                if k in self._store:
                    self._store.pop(k, None)
                    self._expiry.pop(k, None)
                    n += 1
            return n

    def scan_iter(self, match: str = "*"):
        import fnmatch

        with self._lock:
            keys = list(self._store.keys())
        for k in keys:
            if fnmatch.fnmatchcase(k, match):
                yield k

    def pipeline(self) -> _FakePipeline:
        return _FakePipeline(self)


class _FakeRequest:
    def __init__(self, ip: str = "1.2.3.4") -> None:
        class _Client:
            host = ip

        self.client = _Client()
        self.headers: dict[str, str] = {}


# ── MemoryBackend ─────────────────────────────────────────────────────────────


def test_memory_backend_blocks_after_max_attempts():
    backend = MemoryBackend()
    key = "auth-login:1.2.3.4"
    for _ in range(5):
        assert backend.acquire(key, max_attempts=5, window_seconds=60, block_seconds=300) == 0
    # 6e tentative : bloquée pour ~300s
    remaining = backend.acquire(key, max_attempts=5, window_seconds=60, block_seconds=300)
    assert remaining > 0
    assert remaining <= 300


def test_memory_backend_reset_clears_state():
    backend = MemoryBackend()
    key = "auth:ip"
    for _ in range(5):
        backend.acquire(key, 5, 60, 300)
    assert backend.acquire(key, 5, 60, 300) > 0
    backend.reset(key)
    # Après reset : à nouveau possible
    assert backend.acquire(key, 5, 60, 300) == 0


# ── RedisBackend (multi-worker partagé) ───────────────────────────────────────


def test_redis_backend_shared_state_blocks_second_worker():
    """AC4 : la 6e tentative sur un 2e worker partageant Redis est bloquée.

    Deux instances `RedisBackend` distinctes pointent sur le même `_FakeRedis`
    pour simuler deux workers Uvicorn derrière le même Redis.
    """
    fake = _FakeRedis()
    worker_a = RedisBackend(fake)
    worker_b = RedisBackend(fake)
    key = "auth-login:1.2.3.4"

    # 3 tentatives sur worker A, 2 sur worker B → 5 cumulées (limite atteinte).
    for _ in range(3):
        assert worker_a.acquire(key, 5, 60, 300) == 0
    for _ in range(2):
        assert worker_b.acquire(key, 5, 60, 300) == 0

    # 6e tentative sur worker B → doit être bloquée car Redis est partagé.
    remaining = worker_b.acquire(key, 5, 60, 300)
    assert remaining > 0, "Multi-worker rate-limit doit voir 6e tentative bloquée"

    # Et worker A voit aussi le blocage (même clé block:).
    assert worker_a.acquire(key, 5, 60, 300) > 0


def test_redis_backend_reset_clears_block():
    fake = _FakeRedis()
    backend = RedisBackend(fake)
    key = "api:ip"
    for _ in range(5):
        backend.acquire(key, 5, 60, 300)
    assert backend.acquire(key, 5, 60, 300) > 0
    backend.reset(key)
    assert backend.acquire(key, 5, 60, 300) == 0


# ── Settings boot guard (AC1) ─────────────────────────────────────────────────


def test_settings_refuse_memory_backend_in_production(monkeypatch):
    """AC1 : ENV=production + RATE_LIMIT_BACKEND=memory ⇒ ValueError au boot."""
    from app.core.config import Settings

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("ENCRYPTION_KEY", "a" * 64)
    monkeypatch.setenv("FILE_ENCRYPTION_KEY", "b" * 64)
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')

    with pytest.raises(ValueError, match="RATE_LIMIT_BACKEND=memory est interdit"):
        Settings()


def test_settings_accept_redis_backend_in_production(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("ENCRYPTION_KEY", "a" * 64)
    monkeypatch.setenv("FILE_ENCRYPTION_KEY", "b" * 64)
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')

    s = Settings()
    assert s.RATE_LIMIT_BACKEND == "redis"
    assert s.RATE_LIMIT_REDIS_URL == "redis://redis:6379/0"


def test_settings_redis_without_url_rejected(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "")

    with pytest.raises(ValueError, match="RATE_LIMIT_REDIS_URL"):
        Settings()


def test_settings_memory_backend_allowed_in_development(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    s = Settings()
    assert s.RATE_LIMIT_BACKEND == "memory"


# ── _RateLimiter façade (intégration backend) ────────────────────────────────


def test_rate_limiter_uses_backend_singleton(monkeypatch):
    """Vérifie que `_RateLimiter.acquire_attempt` consomme bien le backend
    sélectionné par les settings (ici on force RedisBackend via fake)."""
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limit, "_backend_singleton", RedisBackend(fake))

    limiter = _RateLimiter("auth-login", max_attempts=5, window_seconds=60, block_seconds=300)
    request = _FakeRequest("9.9.9.9")

    for _ in range(5):
        limiter.acquire_attempt(request)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        limiter.acquire_attempt(request)
    assert exc.value.status_code == 429

    # Cleanup pour ne pas polluer les autres tests.
    _reset_backend_for_tests()
