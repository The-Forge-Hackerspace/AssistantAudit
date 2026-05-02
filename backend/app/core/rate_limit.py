"""Rate limiter avec backend pluggable (memory ou Redis).

Limite les requêtes par IP avec des seuils configurables par catégorie :
- auth   : 5 req/min (login, enroll) — protection brute-force
- api    : 30 req/min (endpoints authentifiés) — usage normal
- public : 100 req/min (health, metrics, readiness) — monitoring

Backend sélectionné via `RATE_LIMIT_BACKEND` :
- `memory` : compteur in-process, OK en dev/test mono-worker. Refusé en
  production par la validation de `core/config.py` (les workers ne partagent
  pas leur état → contournement trivial du quota).
- `redis`  : compteur partagé via Redis (`RATE_LIMIT_REDIS_URL`). Cohérent
  multi-worker / multi-instance.

Le contrat public (`login_rate_limiter`, `enroll_rate_limiter`,
`api_rate_limiter`, `public_rate_limiter` exposant `acquire_attempt`,
`reset`, `reset_all`) reste inchangé pour les appelants.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Protocol

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# ── Configuration par catégorie ──────────────────────────────────────────────
# Les seuils max_attempts sont configurables via .env :
# RATE_LIMIT_{AUTH,API,PUBLIC}_MAX. Window/block restent codés en dur (les
# défauts couvrent les cas standards ; à variabiliser en cas de besoin réel).
def _build_rate_limits() -> dict[str, dict[str, int]]:
    from .config import get_settings

    s = get_settings()
    return {
        "auth": {"max_attempts": s.RATE_LIMIT_AUTH_MAX, "window_seconds": 60, "block_seconds": 300},
        "api": {"max_attempts": s.RATE_LIMIT_API_MAX, "window_seconds": 60, "block_seconds": 60},
        "public": {"max_attempts": s.RATE_LIMIT_PUBLIC_MAX, "window_seconds": 60, "block_seconds": 30},
    }


CLEANUP_INTERVAL = 120  # nettoyage mémoire toutes les 2 minutes


# ── Backend Protocol ─────────────────────────────────────────────────────────
class RateLimitBackend(Protocol):
    """Contrat d'un backend de rate-limit. Toutes les opérations sont atomiques."""

    def acquire(self, key: str, max_attempts: int, window_seconds: int, block_seconds: int) -> int:
        """Retourne 0 si la tentative est acceptée, sinon le nombre de secondes
        restantes avant déblocage. Doit être thread-safe et atomique."""
        ...

    def reset(self, key: str) -> None:
        """Supprime tout l'état pour `key`."""
        ...

    def reset_all(self) -> None:
        """Vide complètement le backend (utilisé en tests)."""
        ...


# ── Memory backend (mono-process) ────────────────────────────────────────────
class MemoryBackend:
    """Backend in-memory : counters + blocages dans des dicts protégés par lock.

    Convient pour dev/test mono-worker. Refusé en production (multi-worker)
    par la validation de `Settings.model_post_init` car les compteurs ne sont
    pas partagés entre workers Uvicorn.
    """

    def __init__(self) -> None:
        # {key: [timestamp1, timestamp2, ...]}
        self._attempts: dict[str, list[float]] = defaultdict(list)
        # {key: block_until_timestamp}
        self._blocked: dict[str, float] = {}
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup_locked(self, now: float, window_seconds: int) -> None:
        if now - self._last_cleanup < CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        cutoff = now - window_seconds

        expired_keys: list[str] = []
        for key, timestamps in self._attempts.items():
            self._attempts[key] = [t for t in timestamps if t > cutoff]
            if not self._attempts[key]:
                expired_keys.append(key)
        for key in expired_keys:
            del self._attempts[key]

        expired_blocks = [k for k, until in self._blocked.items() if until < now]
        for k in expired_blocks:
            del self._blocked[k]

    def acquire(self, key: str, max_attempts: int, window_seconds: int, block_seconds: int) -> int:
        now = time.time()
        with self._lock:
            self._cleanup_locked(now, window_seconds)

            if key in self._blocked:
                remaining = int(self._blocked[key] - now)
                if remaining > 0:
                    return remaining
                del self._blocked[key]

            cutoff = now - window_seconds
            self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]

            if len(self._attempts[key]) >= max_attempts:
                self._blocked[key] = now + block_seconds
                self._attempts[key].clear()
                return block_seconds

            self._attempts[key].append(now)
            return 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._blocked.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._attempts.clear()
            self._blocked.clear()


# ── Redis backend (multi-process / multi-instance) ───────────────────────────
class RedisBackend:
    """Backend Redis : compteurs et blocages partagés entre workers.

    Algorithme :
    - Si `block:{key}` existe → renvoie son TTL en secondes (refus).
    - Sinon : INCR `count:{key}` ; si premier hit, EXPIRE à `window_seconds`.
    - Si compteur dépasse `max_attempts` : SETEX `block:{key}` à `block_seconds`,
      DEL `count:{key}` et renvoie `block_seconds`.

    Toutes les opérations critiques sont regroupées dans un pipeline atomique.
    """

    def __init__(self, redis_client) -> None:  # type: ignore[no-untyped-def]
        self._r = redis_client

    @staticmethod
    def _count_key(key: str) -> str:
        return f"rl:count:{key}"

    @staticmethod
    def _block_key(key: str) -> str:
        return f"rl:block:{key}"

    def acquire(self, key: str, max_attempts: int, window_seconds: int, block_seconds: int) -> int:
        block_k = self._block_key(key)
        ttl = self._r.ttl(block_k)
        # ttl > 0 → bloqué, ttl == -1 → existe sans TTL (anomalie), -2 → absent.
        if ttl is not None and ttl > 0:
            return int(ttl)

        count_k = self._count_key(key)
        pipe = self._r.pipeline()
        pipe.incr(count_k)
        pipe.expire(count_k, window_seconds, nx=True)
        results = pipe.execute()
        count = int(results[0])

        if count > max_attempts:
            block_pipe = self._r.pipeline()
            block_pipe.set(block_k, "1", ex=block_seconds)
            block_pipe.delete(count_k)
            block_pipe.execute()
            return block_seconds

        return 0

    def reset(self, key: str) -> None:
        self._r.delete(self._count_key(key), self._block_key(key))

    def reset_all(self) -> None:
        # SCAN + DEL pour ne pas bloquer Redis sur de gros datasets.
        for k in self._r.scan_iter(match="rl:count:*"):
            self._r.delete(k)
        for k in self._r.scan_iter(match="rl:block:*"):
            self._r.delete(k)


# ── Backend factory ──────────────────────────────────────────────────────────
def _build_backend() -> RateLimitBackend:
    """Construit le backend selon `Settings.RATE_LIMIT_BACKEND`.

    La validation `ENV=production + memory` est faite dans `Settings.model_post_init` ;
    on ne la duplique pas ici pour éviter les divergences. Si la lib `redis` est
    indisponible alors que `redis` est demandé, on lève `RuntimeError`.
    """
    from .config import get_settings

    s = get_settings()
    backend = (s.RATE_LIMIT_BACKEND or "memory").lower()

    if backend == "memory":
        logger.info("[RATE_LIMIT] backend=memory")
        return MemoryBackend()

    if backend == "redis":
        try:
            import redis  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "RATE_LIMIT_BACKEND=redis mais le paquet `redis` n'est pas installé. "
                "Ajoutez `redis` à requirements.txt."
            ) from exc
        url = s.RATE_LIMIT_REDIS_URL
        if not url:
            raise RuntimeError(
                "RATE_LIMIT_BACKEND=redis nécessite RATE_LIMIT_REDIS_URL "
                "(ex. redis://redis:6379/0)."
            )
        client = redis.Redis.from_url(url, decode_responses=True)
        logger.info("[RATE_LIMIT] backend=redis url=%s", url)
        return RedisBackend(client)

    raise RuntimeError(
        f"RATE_LIMIT_BACKEND inconnu : '{backend}'. Valeurs supportées : memory, redis."
    )


_backend_singleton: RateLimitBackend | None = None
_backend_lock = Lock()


def get_backend() -> RateLimitBackend:
    """Singleton du backend. Construit lazy à la première tentative de rate-limit."""
    global _backend_singleton
    if _backend_singleton is not None:
        return _backend_singleton
    with _backend_lock:
        if _backend_singleton is None:
            _backend_singleton = _build_backend()
        return _backend_singleton


def _reset_backend_for_tests() -> None:
    """Force la reconstruction du backend (pytest monkeypatch settings)."""
    global _backend_singleton
    with _backend_lock:
        _backend_singleton = None


# ── Limiter façade ───────────────────────────────────────────────────────────
class _RateLimiter:
    """Façade par catégorie : compose une `category` + un backend partagé.

    L'API publique (`acquire_attempt`, `reset`, `reset_all`) reste celle de la
    version mono-process pour ne pas casser les appelants existants.
    """

    _instance_counter = 0
    _instance_counter_lock = Lock()

    def __init__(
        self,
        category: str | None = None,
        max_attempts: int = 5,
        window_seconds: int = 60,
        block_seconds: int = 300,
    ) -> None:
        if category is None:
            with _RateLimiter._instance_counter_lock:
                _RateLimiter._instance_counter += 1
                category = f"_anon{_RateLimiter._instance_counter}"
        self.category = category
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds

    def _key(self, ip: str) -> str:
        return f"{self.category}:{ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extrait l'IP du client.

        X-Forwarded-For n'est utilisé qu'en prod/preprod/staging (derrière un
        reverse proxy de confiance). En dev, on utilise toujours l'IP directe
        pour éviter le spoofing du header.
        """
        from .config import get_settings

        _settings = get_settings()
        if _settings.ENV in ("production", "preprod", "staging"):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def acquire_attempt(self, request: Request) -> None:
        """Vérifie le seuil et enregistre la tentative atomiquement.

        Lève `HTTPException 429` si l'IP est bloquée ou si le seuil est atteint.
        """
        ip = self._get_client_ip(request)
        key = self._key(ip)

        remaining = get_backend().acquire(
            key, self.max_attempts, self.window_seconds, self.block_seconds
        )
        if remaining > 0:
            logger.warning(
                "[RATE_LIMIT] cat=%s ip=%s bloqué, reste %ss", self.category, ip, remaining
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Trop de requêtes. Réessayez dans {remaining} secondes.",
                headers={"Retry-After": str(remaining)},
            )

    def reset(self, request: Request) -> None:
        """Remet le compteur à zéro après un login réussi."""
        ip = self._get_client_ip(request)
        get_backend().reset(self._key(ip))

    def reset_all(self) -> None:
        """Remet tous les compteurs à zéro (utilisé dans les tests).

        Vide le backend complet — partagé par toutes les catégories.
        """
        get_backend().reset_all()


# ── Singletons par catégorie ─────────────────────────────────────────────────
# Construits à l'import : les seuils sont lus via `_build_rate_limits()` qui
# instancie `Settings` (donc déclenche la validation production+memory).
_RATE_LIMITS = _build_rate_limits()

login_rate_limiter = _RateLimiter("auth-login", **_RATE_LIMITS["auth"])
enroll_rate_limiter = _RateLimiter("auth-enroll", **_RATE_LIMITS["auth"])
api_rate_limiter = _RateLimiter("api", **_RATE_LIMITS["api"])
public_rate_limiter = _RateLimiter("public", **_RATE_LIMITS["public"])

# Compatibilité ascendante : exposé pour les anciens tests / scripts.
RATE_LIMITS = _RATE_LIMITS
