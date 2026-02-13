"""
Rate limiter in-memory pour protéger contre le brute-force.

Limite les tentatives par IP sur les endpoints sensibles (login).
En production avec plusieurs workers, remplacer par Redis-backed (slowapi).
"""
import time
import logging
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
MAX_ATTEMPTS = 5          # tentatives max par fenêtre
WINDOW_SECONDS = 60       # durée de la fenêtre (1 minute)
BLOCK_SECONDS = 300       # durée du blocage après dépassement (5 minutes)
CLEANUP_INTERVAL = 120    # nettoyage mémoire toutes les 2 minutes


class _RateLimiter:
    """Compteur de tentatives par IP avec fenêtre glissante."""

    def __init__(self):
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
            cutoff = now - WINDOW_SECONDS

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
        """Extrait l'IP du client (supporte X-Forwarded-For derrière reverse proxy)."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Premier IP = client réel
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        """
        Vérifie si l'IP est autorisée à tenter un login.
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
                        detail=f"Trop de tentatives. Réessayez dans {remaining} secondes.",
                        headers={"Retry-After": str(remaining)},
                    )
                else:
                    del self._blocked[ip]

            # Nettoyer les tentatives hors fenêtre pour cette IP
            cutoff = now - WINDOW_SECONDS
            self._attempts[ip] = [
                t for t in self._attempts[ip] if t > cutoff
            ]

            # Vérifier le nombre de tentatives
            if len(self._attempts[ip]) >= MAX_ATTEMPTS:
                self._blocked[ip] = now + BLOCK_SECONDS
                self._attempts[ip].clear()
                logger.warning(
                    f"[RATE_LIMIT] IP {ip} bloquée pour {BLOCK_SECONDS}s "
                    f"après {MAX_ATTEMPTS} tentatives"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Trop de tentatives. Réessayez dans {BLOCK_SECONDS} secondes.",
                    headers={"Retry-After": str(BLOCK_SECONDS)},
                )

    def record_attempt(self, request: Request) -> None:
        """Enregistre une tentative de login (appelé à chaque essai)."""
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


# Singleton global
login_rate_limiter = _RateLimiter()
