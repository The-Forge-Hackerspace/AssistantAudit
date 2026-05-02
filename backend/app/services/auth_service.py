"""
Service d'authentification : login, création d'utilisateur, gestion des tokens.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.logging_config import hash_username
from ..core.security import create_access_token, create_refresh_token, hash_password, verify_password
from ..models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> Optional[User]:
        """Authentifie un utilisateur par identifiant (username ou email) + mot de passe"""
        identifier = username.strip()
        user = (
            db.query(User)
            .filter(
                or_(
                    User.username == identifier,
                    User.email.ilike(identifier),
                )
            )
            .first()
        )
        if user is None or not verify_password(password, user.password_hash):
            logger.warning(
                "login_failure",
                extra={"event": "login_failure", "username_hash": hash_username(identifier), "reason": "bad_credentials"},
            )
            return None
        if not user.is_active:
            logger.warning(
                "login_failure",
                extra={"event": "login_failure", "username_hash": hash_username(identifier), "reason": "account_disabled"},
            )
            return None

        # Mettre à jour la dernière connexion
        user.last_login = datetime.now(timezone.utc)
        db.flush()

        logger.info(
            "login_success",
            extra={"event": "login_success", "user_id": user.id, "username_hash": hash_username(user.username)},
        )
        return user

    @staticmethod
    def create_tokens(user: User) -> dict:
        """Crée les tokens JWT pour un utilisateur"""
        access_token = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role, "username": user.username},
        )
        refresh_token = create_refresh_token(subject=user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def create_user(
        db: Session, username: str, email: str, password: str, full_name: str = None, role: str = "auditeur"
    ) -> User:
        """Crée un nouvel utilisateur"""
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
        )
        db.add(user)
        db.flush()
        db.refresh(user)
        logger.info(
            "user_created",
            extra={"event": "user_created", "user_id": user.id, "username_hash": hash_username(username), "role": role},
        )
        return user

    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
        """Change le mot de passe d'un utilisateur"""
        if not verify_password(current_password, user.password_hash):
            return False
        user.password_hash = hash_password(new_password)
        db.flush()
        logger.info(
            "password_changed",
            extra={"event": "password_changed", "user_id": user.id, "username_hash": hash_username(user.username)},
        )
        return True

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.get(User, user_id)

    @staticmethod
    def list_users(db: Session, offset: int = 0, limit: int = 20) -> tuple[list[User], int]:
        total = db.query(User).count()
        users = db.query(User).offset(offset).limit(limit).all()
        return users, total

    @staticmethod
    def find_user_by_username_or_email(db: Session, username: str, email: str) -> Optional[User]:
        """Cherche un utilisateur par username ou email (vérification d'unicité)."""
        return (
            db.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        )

    @staticmethod
    def find_by_username(db: Session, username: str) -> Optional[User]:
        """Cherche un utilisateur par username exact."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def find_by_email(db: Session, email: str, exclude_id: int = None) -> Optional[User]:
        """Cherche un utilisateur par email, avec exclusion optionnelle d'un ID."""
        q = db.query(User).filter(User.email == email)
        if exclude_id is not None:
            q = q.filter(User.id != exclude_id)
        return q.first()

    @staticmethod
    def apply_user_updates(
        db: Session,
        user: User,
        email: str = None,
        full_name: str = None,
        role: str = None,
        is_active: bool = None,
        password: str = None,
    ) -> User:
        """Applique les modifications sur un utilisateur et synchronise la session."""
        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if password is not None:
            user.password_hash = hash_password(password)
        db.flush()
        db.refresh(user)
        return user

    @staticmethod
    def deactivate_user(db: Session, user: User) -> None:
        """Désactive un utilisateur (soft delete)."""
        user.is_active = False
        db.flush()
