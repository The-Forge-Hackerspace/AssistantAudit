"""
Routes de gestion des utilisateurs — admin uniquement.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import PaginationParams, get_current_admin
from ...models.user import User
from ...schemas.common import PaginatedResponse
from ...schemas.user import UserCreate, UserRead, UserUpdate
from ...services.auth_service import AuthService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserRead])
def list_users(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Liste tous les utilisateurs (admin uniquement)."""
    users, total = AuthService.list_users(db, offset=pagination.offset, limit=pagination.page_size)
    pages = (total + pagination.page_size - 1) // pagination.page_size
    return {
        "items": users,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": pages,
    }


@router.post("/", response_model=UserRead, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Crée un nouvel utilisateur (admin uniquement)."""
    existing = AuthService.find_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur est déjà pris")

    existing = AuthService.find_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")

    user = AuthService.create_user(
        db,
        username=body.username,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Modifie un utilisateur (admin uniquement)."""
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if body.email is not None:
        existing = AuthService.find_by_email(db, body.email, exclude_id=user_id)
        if existing:
            raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")

    user = AuthService.apply_user_updates(
        db,
        user,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
        password=body.password,
    )
    return user


@router.delete("/{user_id}", status_code=200)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Désactive un utilisateur (soft delete). L'admin ne peut pas se désactiver lui-même."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous désactiver vous-même")

    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    AuthService.deactivate_user(db, user)
    return {"message": f"Utilisateur '{user.username}' désactivé"}
