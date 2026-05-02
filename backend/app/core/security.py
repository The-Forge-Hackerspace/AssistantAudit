"""
Securite : hashing de mots de passe, gestion JWT (user + agent), enrollment.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


# --- Hashing des mots de passe (bcrypt direct, sans passlib) ---
def hash_password(password: str) -> str:
    """Hash un mot de passe en clair"""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# --- JWT ---
def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """Crée un access token JWT"""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


# TOS-102 / AC-1b: rotation des refresh tokens. Chaque refresh contient un JTI
# unique ; lorsqu'il est consommé, le JTI passe dans une denylist en mémoire
# avec son expiration. Tout ré-usage du même token lève PyJWTError.
#
# Limitation: la denylist est in-process (cf. lockout rate_limiter pour la
# même contrainte multi-worker). En déploiement multi-worker, brancher Redis
# (cf. core/rate_limit.py RedisBackend) sur un futur RefreshTokenStore.
_revoked_refresh_jtis: dict[str, float] = {}
_revoked_lock = __import__("threading").Lock()


def _prune_revoked_jtis(now_ts: float) -> None:
    """Retire de la denylist les JTI dont l'expiration est dépassée."""
    expired = [jti for jti, exp in _revoked_refresh_jtis.items() if exp <= now_ts]
    for jti in expired:
        _revoked_refresh_jtis.pop(jti, None)


def revoke_refresh_jti(jti: str, expires_at: datetime) -> None:
    """Marque un JTI comme révoqué jusqu'à son expiration originelle."""
    if not jti:
        return
    exp_ts = expires_at.timestamp() if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc).timestamp()
    with _revoked_lock:
        _prune_revoked_jtis(datetime.now(timezone.utc).timestamp())
        _revoked_refresh_jtis[jti] = exp_ts


def is_refresh_jti_revoked(jti: str) -> bool:
    if not jti:
        return False
    with _revoked_lock:
        now_ts = datetime.now(timezone.utc).timestamp()
        _prune_revoked_jtis(now_ts)
        exp = _revoked_refresh_jtis.get(jti)
        return exp is not None and exp > now_ts


def create_refresh_token(subject: str | int) -> str:
    """Crée un refresh token JWT (avec JTI pour rotation)"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """Decode et valide un token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None


def validate_refresh_token(token: str) -> dict:
    """
    Decode un JWT et verifie que c'est un refresh token NON révoqué.
    Retourne le payload ou raise PyJWTError si invalide/expire/mauvais type/révoqué.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    if payload.get("type") != "refresh":
        raise jwt.PyJWTError("Type de token invalide : 'refresh' attendu")
    jti = payload.get("jti")
    if jti and is_refresh_jti_revoked(jti):
        raise jwt.PyJWTError("Refresh token déjà utilisé (rotation)")
    return payload


# --- Tokens agent (daemon Windows) ---


def create_agent_token(agent_uuid: str, owner_id: int) -> str:
    """
    Token JWT pour un agent enrolle. Longue duree (30 jours).
    L'owner_id est embarque — l'agent ne peut agir qu'au nom de son proprietaire.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "type": "agent",
        "sub": agent_uuid,
        "owner_id": owner_id,
        "exp": now + timedelta(days=30),
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_agent_token(token: str) -> dict:
    """
    Verifie un token agent. Raise JWTError si invalide ou mauvais type.
    Retourne {"sub": agent_uuid, "owner_id": int, ...}.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    if payload.get("type") != "agent":
        raise jwt.PyJWTError("Invalid token type: expected 'agent'")
    return payload


# --- Tokens d'enrollment (usage unique, ephemere) ---


def create_enrollment_token() -> tuple[str, str, datetime]:
    """
    Genere un code d'enrollment pour un nouvel agent.

    Returns:
        (code_clair, code_hash, expiration)
        - code_clair : 8 caracteres alphanumeriques majuscules, affiche a l'admin
        - code_hash : SHA-256 du code, stocke en base
        - expiration : datetime UTC, 10 minutes
    """
    code = secrets.token_urlsafe(6)[:8].upper()
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    expiration = datetime.now(timezone.utc) + timedelta(minutes=10)
    return code, code_hash, expiration


def verify_enrollment_token(code: str, stored_hash: str, expiration: datetime) -> bool:
    """Verifie un code d'enrollment contre son hash et son expiration."""
    now = datetime.now(timezone.utc)
    # SQLite peut retourner des datetimes naive — les traiter comme UTC
    exp = expiration if expiration.tzinfo else expiration.replace(tzinfo=timezone.utc)
    if now > exp:
        return False
    return hmac.compare_digest(hashlib.sha256(code.encode()).hexdigest(), stored_hash)
