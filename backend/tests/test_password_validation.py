"""
Tests pour la validation de complexite des mots de passe.
"""
import pytest
from pydantic import ValidationError

from app.schemas.user import PasswordChange, UserCreate, UserUpdate


class TestPasswordComplexity:
    """Verifie les regles de complexite sur les schemas Pydantic."""

    def test_password123_rejected(self):
        """password123 : trop court (11 chars < 12)."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="password123",
            )
        error_msg = str(exc_info.value)
        assert "12" in error_msg

    def test_long_password_no_upper_no_special_rejected(self):
        """passwordpassword1 : pas de majuscule, pas de special."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="passwordpassword1",
            )
        error_msg = str(exc_info.value)
        assert "majuscule" in error_msg
        assert "special" in error_msg

    def test_short_password_rejected(self):
        """Password1! : trop court (< 12 caracteres)."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="Password1!",
            )
        error_msg = str(exc_info.value)
        assert "12" in error_msg

    def test_valid_password_accepted(self):
        """SecurePass1!xx : 14 chars, maj, min, chiffre, special."""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecurePass1!xx",
        )
        assert user.password == "SecurePass1!xx"

    def test_no_uppercase_rejected(self):
        """Pas de majuscule → rejet."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="securepass1!xx",
            )
        assert "majuscule" in str(exc_info.value)

    def test_no_lowercase_rejected(self):
        """Pas de minuscule → rejet."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="SECUREPASS1!XX",
            )
        assert "minuscule" in str(exc_info.value)

    def test_no_digit_rejected(self):
        """Pas de chiffre → rejet."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="SecurePass!!xx",
            )
        assert "chiffre" in str(exc_info.value)

    def test_no_special_rejected(self):
        """Pas de caractere special → rejet."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="SecurePass1xxx",
            )
        assert "special" in str(exc_info.value)

    def test_multiple_missing_criteria(self):
        """Plusieurs criteres manquants → tous listes dans le message."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="abcdefghijkl",
            )
        error_msg = str(exc_info.value)
        assert "majuscule" in error_msg
        assert "chiffre" in error_msg
        assert "special" in error_msg

    def test_exactly_12_chars_accepted(self):
        """Exactement 12 caracteres avec tous les criteres → accepte."""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="Password123!",
        )
        assert user.password == "Password123!"


class TestUserUpdatePassword:
    """Validation sur UserUpdate.password (optionnel)."""

    def test_none_password_valid(self):
        """UserUpdate.password = None reste valide."""
        update = UserUpdate(password=None)
        assert update.password is None

    def test_omitted_password_valid(self):
        """UserUpdate sans password reste valide."""
        update = UserUpdate()
        assert update.password is None

    def test_weak_password_rejected(self):
        """UserUpdate avec un mot de passe faible est rejete."""
        with pytest.raises(ValidationError):
            UserUpdate(password="weak")

    def test_strong_password_accepted(self):
        """UserUpdate avec un mot de passe fort est accepte."""
        update = UserUpdate(password="NewPassword1!!")
        assert update.password == "NewPassword1!!"


class TestPasswordChangeValidation:
    """Validation sur PasswordChange.new_password."""

    def test_weak_new_password_rejected(self):
        """PasswordChange avec new_password faible est rejete."""
        with pytest.raises(ValidationError):
            PasswordChange(
                current_password="anything",
                new_password="weak",
            )

    def test_strong_new_password_accepted(self):
        """PasswordChange avec new_password fort est accepte."""
        change = PasswordChange(
            current_password="anything",
            new_password="StrongPass1!!x",
        )
        assert change.new_password == "StrongPass1!!x"
