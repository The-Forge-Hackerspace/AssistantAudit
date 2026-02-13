"""
Routes d'authentification : login, register, refresh, profile.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_admin
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


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authentification par username/password → JWT.
    Accepte le format OAuth2 form (utilisé par Swagger Authorize)
    et le format JSON classique.
    """
    logger.info(f"[LOGIN] Tentative login user='{form_data.username}' (len_pwd={len(form_data.password)})")
    user = AuthService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    tokens = AuthService.create_tokens(user)
    return tokens


@router.post("/login/json", response_model=TokenResponse)
async def login_json(body: LoginRequest, db: Session = Depends(get_db)):
    """Authentification par JSON body (pour les clients API)"""
    user = AuthService.authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    tokens = AuthService.create_tokens(user)
    return tokens


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Créer un nouvel utilisateur (admin seulement)"""
    # Vérifier unicité
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
async def get_me(current_user: User = Depends(get_current_user)):
    """Profil de l'utilisateur courant"""
    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
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
