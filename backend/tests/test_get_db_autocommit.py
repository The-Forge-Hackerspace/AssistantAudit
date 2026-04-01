"""
Tests unitaires — get_db() auto-commit on success, auto-rollback on exception.

Teste le générateur get_db() directement (pas via le client HTTP,
car conftest override get_db avec lambda: db_session).
"""
from unittest.mock import MagicMock, patch

import pytest


class TestGetDbAutoCommit:

    def test_commit_on_success(self):
        """get_db() commit la session quand le générateur se termine normalement."""
        mock_session = MagicMock()

        with patch("app.core.database.SessionLocal", return_value=mock_session):
            from app.core.database import get_db

            gen = get_db()
            db = next(gen)
            assert db is mock_session

            # Terminer le générateur normalement (simule la fin de la requête)
            try:
                next(gen)
            except StopIteration:
                pass

            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_session.close.assert_called_once()

    def test_rollback_on_exception(self):
        """get_db() rollback la session quand une exception est levée."""
        mock_session = MagicMock()

        with patch("app.core.database.SessionLocal", return_value=mock_session):
            from app.core.database import get_db

            gen = get_db()
            db = next(gen)
            assert db is mock_session

            # Injecter une exception dans le générateur (simule une erreur dans la route)
            with pytest.raises(ValueError, match="boom"):
                gen.throw(ValueError("boom"))

            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()
            mock_session.close.assert_called_once()

    def test_close_always_called(self):
        """get_db() ferme toujours la session, même après exception."""
        mock_session = MagicMock()

        with patch("app.core.database.SessionLocal", return_value=mock_session):
            from app.core.database import get_db

            gen = get_db()
            next(gen)

            # Fermer le générateur sans terminer proprement
            gen.close()

            mock_session.close.assert_called_once()
