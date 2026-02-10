"""
Service d'authentification : login, création d'utilisateur, gestion des tokens.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..core.security import hash_password, verify_password, create_access_token, create_refresh_token
from ..models.user import User

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> Optional[User]:
        """Authentifie un utilisateur par username/password"""
        user = db.query(User).filter(User.username == username).first()
        if user is None or not verify_password(password, user.password_hash):
            logger.warning(f"Tentative de connexion échouée pour: {username}")
            return None
        if not user.is_active:
            logger.warning(f"Connexion refusée (compte désactivé): {username}")
            return None

        # Mettre à jour la dernière connexion
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Connexion réussie: {username}")
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
    def create_user(db: Session, username: str, email: str, password: str,
                    full_name: str = None, role: str = "auditeur") -> User:
        """Crée un nouvel utilisateur"""
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Utilisateur créé: {username} (role={role})")
        return user

    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
        """Change le mot de passe d'un utilisateur"""
        if not verify_password(current_password, user.password_hash):
            return False
        user.password_hash = hash_password(new_password)
        db.commit()
        logger.info(f"Mot de passe changé pour: {user.username}")
        return True

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.get(User, user_id)

    @staticmethod
    def list_users(db: Session, offset: int = 0, limit: int = 20) -> tuple[list[User], int]:
        total = db.query(User).count()
        users = db.query(User).offset(offset).limit(limit).all()
        return users, total
