"""
Routes d'authentification : login, register, refresh, profile.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
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


def _clear_legacy_httponly_cookies(response: Response) -> None:
    """
    Supprime les anciens cookies httpOnly qui peuvent rester dans le navigateur
    suite à une version précédente du code. Sans cette suppression, js-cookie
    ne peut ni lire ni écraser ces cookies → l'auth frontend est cassée.
    """
    response.delete_cookie("aa_access_token", path="/", httponly=True, samesite="strict")
    response.delete_cookie("aa_refresh_token", path=f"{_settings.API_V1_PREFIX}/auth", httponly=True, samesite="strict")


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authentification par username/password → JWT.
    Accepte le format OAuth2 form (utilisé par Swagger Authorize)
    et le format JSON classique.
    """
    # Rate limiting anti brute-force
    login_rate_limiter.check(request)
    login_rate_limiter.record_attempt(request)

    logger.info(f"[LOGIN] Tentative login user='{form_data.username}'")
    user = AuthService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    # Login réussi : reset le compteur
    login_rate_limiter.reset(request)
    tokens = AuthService.create_tokens(user)
    _clear_legacy_httponly_cookies(response)
    return tokens


@router.post("/login/json", response_model=TokenResponse)
def login_json(request: Request, response: Response, body: LoginRequest, db: Session = Depends(get_db)):
    """Authentification par JSON body (pour les clients API)"""
    # Rate limiting anti brute-force
    login_rate_limiter.check(request)
    login_rate_limiter.record_attempt(request)

    user = AuthService.authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    # Login réussi : reset le compteur
    login_rate_limiter.reset(request)
    tokens = AuthService.create_tokens(user)
    _clear_legacy_httponly_cookies(response)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Renouvelle les tokens a partir d'un refresh token valide."""
    # Rate limiting (meme limiter que /login)
    login_rate_limiter.check(request)
    login_rate_limiter.record_attempt(request)

    try:
        payload = validate_refresh_token(body.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expire",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou desactive",
        )

    login_rate_limiter.reset(request)
    return AuthService.create_tokens(user)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Créer un nouvel utilisateur (admin seulement)"""
    # Vérifier unicité
    existing = db.query(User).filter((User.username == body.username) | (User.email == body.email)).first()
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
    """Déconnexion : supprime les éventuels cookies httpOnly résiduels."""
    _clear_legacy_httponly_cookies(response)
    return MessageResponse(message="Déconnecté avec succès")
