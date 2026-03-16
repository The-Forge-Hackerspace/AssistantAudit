"""
Dépendances FastAPI réutilisables :
  - Session de base de données
  - Utilisateur courant (authentifié via JWT — cookie httpOnly ou header Authorization)
  - Pagination
"""
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .security import decode_token

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Dépendance : récupère l'utilisateur authentifié depuis le token JWT.
    Ordre de lecture du token :
      1. Cookie httpOnly « aa_access_token » (frontend via withCredentials)
      2. Header Authorization: Bearer <token> (Swagger UI, clients API)
    Lève 401 si aucun token valide n'est trouvé.
    """
    # Cookie httpOnly prioritaire, fallback sur le header Authorization
    effective_token = request.cookies.get("aa_access_token") or token

    if effective_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(effective_token)
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


def get_current_admin(current_user=Depends(get_current_user)):
    """Dépendance : vérifie que l'utilisateur est administrateur"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis",
        )
    return current_user


def get_current_auditeur(current_user=Depends(get_current_user)):
    """Dépendance : vérifie que l'utilisateur est au moins auditeur (admin ou auditeur)"""
    if current_user.role not in ("admin", "auditeur"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits auditeur requis (rôle lecteur insuffisant)",
        )
    return current_user


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
