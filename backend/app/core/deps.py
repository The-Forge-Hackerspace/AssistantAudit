"""
Dépendances FastAPI réutilisables :
  - Session de base de données
  - Utilisateur courant (authentifié via JWT)
  - Contexte RBAC (user_id, is_admin, role)
  - Pagination
"""

import logging
from datetime import datetime, timezone
from typing import NamedTuple, Optional

from fastapi import Cookie, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .errors import NotFoundError
from .security import decode_token, verify_agent_token

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    aa_access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """
    Dependance : recupere l'utilisateur authentifie depuis le token JWT.
    Source des tokens (par ordre de priorite) :
      1. Cookie httpOnly `aa_access_token` (frontend SPA, auth principale)
      2. Header Authorization: Bearer <token> (Swagger, scripts, fallback)
    Leve 401 si aucun token valide n'est trouve.
    """
    token = aa_access_token or token
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )

    from ..models.user import User

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou désactivé",
        )
    return user


async def get_current_admin(current_user=Depends(get_current_user)):
    """Dépendance : vérifie que l'utilisateur est administrateur"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis",
        )
    return current_user


async def get_current_agent(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Dependance pour les routes agent.
    Verifie le token JWT agent et retourne l'objet Agent.
    """
    import jwt

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token agent requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_agent_token(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token agent invalide ou expire",
        )

    from ..models.agent import Agent

    agent = (
        db.query(Agent)
        .filter(
            Agent.agent_uuid == payload["sub"],
            Agent.status == "active",
        )
        .first()
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent introuvable ou revoque",
        )

    # Avertissement si le certificat expire dans moins de 30 jours
    if agent.cert_expires_at:
        expires = agent.cert_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        days_left = (expires - datetime.now(timezone.utc)).days
        if days_left < 30:
            logging.getLogger(__name__).warning(
                "Agent %s certificate expires in %d days",
                agent.agent_uuid,
                days_left,
            )

    return agent


async def get_current_auditeur(current_user=Depends(get_current_user)):
    """Dépendance : vérifie que l'utilisateur est au moins auditeur (admin ou auditeur)"""
    if current_user.role not in ("admin", "auditeur"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits auditeur requis (rôle lecteur insuffisant)",
        )
    return current_user


class RbacContext(NamedTuple):
    """Contexte RBAC injecté via Depends(get_rbac_context).

    Centralise le pattern (user_id, is_admin) historiquement dupliqué dans les routeurs.
    Tuple-friendly : `uid, adm, _ = rbac` reste possible si besoin.
    """

    user_id: int
    is_admin: bool
    role: str

    def assert_owner_or_admin(self, owner_id: int | None, resource_label: str) -> None:
        """Vérifie que l'utilisateur est admin ou propriétaire de la ressource.

        Lève `NotFoundError(resource_label)` si non autorisé (pattern hide-as-404 :
        on ne révèle pas l'existence d'une ressource à un utilisateur non autorisé).
        """
        if self.is_admin:
            return
        if owner_id is None or owner_id != self.user_id:
            raise NotFoundError(resource_label)


def get_rbac_context(current_user=Depends(get_current_user)) -> RbacContext:
    """Dépendance : retourne le contexte RBAC (user_id, is_admin, role).

    Remplace les helpers privés `_rbac()` dupliqués dans les routeurs et
    les checks inline `current_user.role == "admin"`.
    """
    return RbacContext(
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
        role=current_user.role,
    )


def get_rbac_context_auditeur(current_user=Depends(get_current_auditeur)) -> RbacContext:
    """Variante auditeur : exige rôle admin ou auditeur (lecteur rejeté en 403).

    À utiliser sur les endpoints qui exigeaient `Depends(get_current_auditeur)`.
    """
    return RbacContext(
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
        role=current_user.role,
    )


class PaginationParams:
    """Paramètres de pagination réutilisables"""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Numéro de page"),
        page_size: int = Query(
            settings.DEFAULT_PAGE_SIZE,
            ge=1,
            le=settings.MAX_PAGE_SIZE,
            description="Nombre d'éléments par page",
        ),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
