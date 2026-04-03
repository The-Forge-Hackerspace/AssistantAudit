"""
Schémas User : authentification et gestion utilisateurs.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_complexity(password: str) -> str:
    """Valide la complexite du mot de passe et retourne un message explicite."""
    missing = []
    if len(password) < 12:
        missing.append("au moins 12 caracteres")
    if not re.search(r"[A-Z]", password):
        missing.append("au moins 1 majuscule")
    if not re.search(r"[a-z]", password):
        missing.append("au moins 1 minuscule")
    if not re.search(r"[0-9]", password):
        missing.append("au moins 1 chiffre")
    if not re.search(r"[^A-Za-z0-9]", password):
        missing.append("au moins 1 caractere special")
    if missing:
        raise ValueError("Mot de passe trop faible : " + ", ".join(missing))
    return password


# --- Auth ---
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# --- User CRUD ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    full_name: Optional[str] = None
    role: str = Field(default="auditeur", pattern=r"^(admin|auditeur|lecteur)$")


class UserCreate(UserBase):
    password: str = Field(..., min_length=12)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern=r"^(admin|auditeur|lecteur)$")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=12)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_password_complexity(v)


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)
