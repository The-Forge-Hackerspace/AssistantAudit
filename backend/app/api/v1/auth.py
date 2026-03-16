"""
Routes d'authentification : login, register, refresh, profile, logout.

SEC-03 : les tokens JWT sont désormais stockés dans des cookies httpOnly
(inaccessibles au JavaScript côté client → protection XSS).
Le header Authorization: Bearer reste accepté en fallback pour
Swagger UI et les clients API externes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.database import get_db
from ...core.deps import get_current_user, get_current_admin
from ...core.rate_limit import login_rate_limiter
from ...core.security import decode_token, create_access_token, create_refresh_token
from ...models.user import User
from ...schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    PasswordChange,
)
from ...schemas.common import MessageResponse
from ...services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger(__name__)

_settings = get_settings()

# ── Cookie helpers ────────────────────────────────────────────────────────

# Nom des cookies — identiques à ceux utilisés historiquement
ACCESS_COOKIE = "aa_access_token"
REFRESH_COOKIE = "aa_refresh_token"


def _set_auth_cookies(response: Response, tokens: dict) -> None:
    """
    Positionne les cookies httpOnly pour l'access token et le refresh token.
    - Access cookie : path=/ (envoyé sur toutes les requêtes API)
    - Refresh cookie : path=/api/v1/auth (envoyé uniquement sur /auth/refresh)
    """
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=tokens["access_token"],
        httponly=True,
        secure=_settings.COOKIE_SECURE,
        samesite=_settings.COOKIE_SAMESITE,
        path="/",
        max_age=_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens["refresh_token"],
        httponly=True,
        secure=_settings.COOKIE_SECURE,
        samesite=_settings.COOKIE_SAMESITE,
        path=f"{_settings.API_V1_PREFIX}/auth",
        max_age=_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Supprime les cookies d'authentification (logout / refresh échoué)."""
    response.delete_cookie(
        key=ACCESS_COOKIE,
        path="/",
        httponly=True,
        samesite=_settings.COOKIE_SAMESITE,
        secure=_settings.COOKIE_SECURE,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=f"{_settings.API_V1_PREFIX}/auth",
        httponly=True,
        samesite=_settings.COOKIE_SAMESITE,
        secure=_settings.COOKIE_SECURE,
    )


# ── Auth endpoints ────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authentification par username/password → JWT.
    Accepte le format OAuth2 form (utilisé par Swagger Authorize).
    Les tokens sont renvoyés dans le body (pour Swagger) ET dans des
    cookies httpOnly (pour le frontend).
    """
    login_rate_limiter.check(request)
    login_rate_limiter.record_attempt(request)

    logger.info(f"[LOGIN] Tentative login user='{form_data.username}'")
    user = AuthService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    login_rate_limiter.reset(request)
    tokens = AuthService.create_tokens(user)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/login/json", response_model=TokenResponse)
def login_json(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authentification par JSON body (clients API)."""
    login_rate_limiter.check(request)
    login_rate_limiter.record_attempt(request)

    user = AuthService.authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    login_rate_limiter.reset(request)
    tokens = AuthService.create_tokens(user)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Rafraîchit la session : lit le refresh token depuis le cookie httpOnly,
    génère un nouveau couple access+refresh et les positionne en cookies.
    """
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token manquant",
        )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré",
        )

    user_id = payload.get("sub")
    if user_id is None:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou désactivé",
        )

    tokens = AuthService.create_tokens(user)
    _set_auth_cookies(response, tokens)
    logger.info(f"[REFRESH] Token rafraîchi pour user='{user.username}'")
    return tokens


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Créer un nouvel utilisateur (admin seulement)"""
    existing = db.query(User).filter(
        (User.username == body.username) | (User.email == body.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un utilisateur avec ce nom ou email existe déjà",
        )
    user = AuthService.create_user(
        db,
        username=body.username,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )
    return user


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """Profil de l'utilisateur courant"""
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Changer son mot de passe"""
    success = AuthService.change_password(
        db, current_user, body.current_password, body.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    return MessageResponse(message="Mot de passe modifié avec succès")


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """Déconnexion : supprime les cookies httpOnly d'authentification."""
    _clear_auth_cookies(response)
    return MessageResponse(message="Déconnecté avec succès")
