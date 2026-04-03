"""Rate limiter in-memory pour protéger contre le brute-force et l'abus d'API.

Limite les requêtes par IP avec des seuils configurables par catégorie :
- auth : 5 req/min (login, enroll) — protection brute-force
- api  : 30 req/min (endpoints authentifiés) — usage normal
- public : 100 req/min (health, metrics, readiness) — monitoring

En production avec plusieurs workers, remplacer par Redis-backed (slowapi).
"""
import logging
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# ── Configuration par catégorie ──────────────────────────────────────────────
RATE_LIMITS = {
    "auth": {"max_attempts": 5, "window_seconds": 60, "block_seconds": 300},
    "api": {"max_attempts": 30, "window_seconds": 60, "block_seconds": 60},
    "public": {"max_attempts": 100, "window_seconds": 60, "block_seconds": 30},
}

CLEANUP_INTERVAL = 120  # nettoyage mémoire toutes les 2 minutes


class _RateLimiter:
    """Compteur de tentatives par IP avec fenêtre glissante."""

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 60,
        block_seconds: int = 300,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds
        # {ip: [timestamp1, timestamp2, ...]}
        self._attempts: dict[str, list[float]] = defaultdict(list)
        # {ip: block_until_timestamp}
        self._blocked: dict[str, float] = {}
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup(self):
        """Supprime les anciennes entrées pour éviter les fuites mémoire."""
        now = time.time()
        if now - self._last_cleanup < CLEANUP_INTERVAL:
            return

        with self._lock:
            self._last_cleanup = now
            cutoff = now - self.window_seconds

            # Nettoyer les tentatives expirées
            expired_ips = []
            for ip, timestamps in self._attempts.items():
                self._attempts[ip] = [t for t in timestamps if t > cutoff]
                if not self._attempts[ip]:
                    expired_ips.append(ip)
            for ip in expired_ips:
                del self._attempts[ip]

            # Nettoyer les blocages expirés
            expired_blocks = [
                ip for ip, until in self._blocked.items() if until < now
            ]
            for ip in expired_blocks:
                del self._blocked[ip]

    def _get_client_ip(self, request: Request) -> str:
        """
        Extrait l'IP du client.
        X-Forwarded-For n'est utilisé qu'en production (derrière un reverse proxy
        de confiance). En dev, on utilise toujours l'IP directe pour éviter
        le spoofing du header.
        """
        from .config import get_settings
        _settings = get_settings()
        if _settings.ENV in ("production", "preprod", "staging"):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        """
        Vérifie si l'IP est autorisée à effectuer la requête.
        Lève HTTP 429 si le rate limit est dépassé.
        """
        self._cleanup()
        ip = self._get_client_ip(request)
        now = time.time()

        with self._lock:
            # Vérifier si l'IP est bloquée
            if ip in self._blocked:
                remaining = int(self._blocked[ip] - now)
                if remaining > 0:
                    logger.warning(
                        f"[RATE_LIMIT] IP {ip} bloquée, reste {remaining}s"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Trop de requêtes. Réessayez dans {remaining} secondes.",
                        headers={"Retry-After": str(remaining)},
                    )
                else:
                    del self._blocked[ip]

            # Nettoyer les tentatives hors fenêtre pour cette IP
            cutoff = now - self.window_seconds
            self._attempts[ip] = [
                t for t in self._attempts[ip] if t > cutoff
            ]

            # Vérifier le nombre de tentatives
            if len(self._attempts[ip]) >= self.max_attempts:
                self._blocked[ip] = now + self.block_seconds
                self._attempts[ip].clear()
                logger.warning(
                    f"[RATE_LIMIT] IP {ip} bloquée pour {self.block_seconds}s "
                    f"après {self.max_attempts} requêtes"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Trop de requêtes. Réessayez dans {self.block_seconds} secondes.",
                    headers={"Retry-After": str(self.block_seconds)},
                )

    def record_attempt(self, request: Request) -> None:
        """Enregistre une tentative (appelé à chaque requête)."""
        ip = self._get_client_ip(request)
        now = time.time()
        with self._lock:
            self._attempts[ip].append(now)

    def reset(self, request: Request) -> None:
        """Remet le compteur à zéro après un login réussi."""
        ip = self._get_client_ip(request)
        with self._lock:
            self._attempts.pop(ip, None)
            self._blocked.pop(ip, None)

    def reset_all(self) -> None:
        """Remet tous les compteurs à zéro (utilisé dans les tests)."""
        with self._lock:
            self._attempts.clear()
            self._blocked.clear()


# ── Singletons par catégorie ─────────────────────────────────────────────────
login_rate_limiter = _RateLimiter(**RATE_LIMITS["auth"])
enroll_rate_limiter = _RateLimiter(**RATE_LIMITS["auth"])
api_rate_limiter = _RateLimiter(**RATE_LIMITS["api"])
public_rate_limiter = _RateLimiter(**RATE_LIMITS["public"])
