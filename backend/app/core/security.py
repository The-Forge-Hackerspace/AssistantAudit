"""
Securite : hashing de mots de passe, gestion JWT (user + agent), enrollment.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

import bcrypt
from jose import JWTError, jwt

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
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    """Crée un refresh token JWT"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode et valide un token JWT"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


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
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_agent_token(token: str) -> dict:
    """
    Verifie un token agent. Raise JWTError si invalide ou mauvais type.
    Retourne {"sub": agent_uuid, "owner_id": int, ...}.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "agent":
        raise JWTError("Invalid token type: expected 'agent'")
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
    if datetime.now(timezone.utc) > expiration:
        return False
    return hashlib.sha256(code.encode()).hexdigest() == stored_hash
