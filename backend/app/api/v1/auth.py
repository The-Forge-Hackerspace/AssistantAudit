"""
Routes d'authentification : login, register, refresh, profile.
"""

import logging

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.database import get_db
from ...core.deps import get_current_admin, get_current_user
from ...core.rate_limit import login_rate_limiter
from ...core.security import validate_refresh_token
from ...models.user import User
from ...schemas.common import MessageResponse
from ...schemas.user import (
    LoginRequest,
    PasswordChange,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from ...services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger(__name__)

_settings = get_settings()

ACCESS_COOKIE = "aa_access_token"
REFRESH_COOKIE = "aa_refresh_token"
REFRESH_COOKIE_PATH = f"{_settings.API_V1_PREFIX}/auth"


def _is_secure_env() -> bool:
    """Active le flag Secure des cookies hors dev/test."""
    return _settings.ENV in ("production", "preprod", "staging")


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Pose access et refresh tokens en cookies httpOnly + SameSite=Strict.
    Le refresh est scope au path /api/v1/auth pour limiter sa surface d'envoi.
    """
    secure = _is_secure_env()
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=secure,
        samesite="strict",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Supprime les cookies d'auth poses par _set_auth_cookies."""
    response.delete_cookie(ACCESS_COOKIE, path="/", httponly=True, samesite="strict")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, samesite="strict")


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authentification par username/password → JWT.
    Pose les tokens en cookies httpOnly et les retourne aussi en body
    pour les clients programmatiques (Swagger, agents, scripts).
    """
    login_rate_limiter.acquire_attempt(request)

    logger.info(f"[LOGIN] Tentative login user='{form_data.username}'")
    user = AuthService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    login_rate_limiter.reset(request)
    tokens = AuthService.create_tokens(user)
    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return tokens


@router.post("/login/json", response_model=TokenResponse)
def login_json(request: Request, response: Response, body: LoginRequest, db: Session = Depends(get_db)):
    """Authentification par JSON body (pour les clients API)"""
    login_rate_limiter.acquire_attempt(request)

    user = AuthService.authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    login_rate_limiter.reset(request)
    tokens = AuthService.create_tokens(user)
    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    aa_refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """
    Renouvelle les tokens a partir d'un refresh token valide.
    Lit le refresh depuis le cookie httpOnly en priorite, puis depuis le body JSON
    si necessaire (compat clients legacy).
    """
    login_rate_limiter.acquire_attempt(request)

    refresh_token = aa_refresh_token or (body.refresh_token if body and body.refresh_token else None)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token requis",
        )

    try:
        payload = validate_refresh_token(refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expire",
        )

    user_id = payload.get("sub")
    user = AuthService.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou desactive",
        )

    login_rate_limiter.reset(request)
    tokens = AuthService.create_tokens(user)
    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return tokens


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Créer un nouvel utilisateur (admin seulement)"""
    existing = AuthService.find_user_by_username_or_email(db, body.username, body.email)
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
    success = AuthService.change_password(db, current_user, body.current_password, body.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    return MessageResponse(message="Mot de passe modifié avec succès")


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """Déconnexion : supprime les cookies d'auth httpOnly côté client."""
    _clear_auth_cookies(response)
    return MessageResponse(message="Déconnecté avec succès")
