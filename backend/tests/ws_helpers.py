"""
Helpers partages pour les tests qui manipulent le WebSocketManager et
injectent une session SQLAlchemy factice via `SessionLocal`.

Centralise la duplication entre les modules de test (sweeper, reconnexion…)
pour eviter les divergences au fil du temps.
"""

from __future__ import annotations

from typing import Any

from app.core.websocket_manager import ws_manager


class NoCloseSession:
    """Proxy sur une Session SQLAlchemy qui ignore `close()`.

    Utilise pour empecher les services (qui appellent `db.close()` en `finally`)
    de fermer la session de test partagee par la fixture `db_session`.
    """

    def __init__(self, session: Any):
        self._session = session

    def __getattr__(self, name: str) -> Any:
        if name == "close":
            return lambda: None
        return getattr(self._session, name)


class FakeSessionLocal:
    """Callable qui retourne toujours le meme proxy NoCloseSession.

    A patcher sur `app.core.database.SessionLocal` (ou ses re-exports) pour que
    le code sous test utilise la session de test au lieu d'en creer une neuve.
    """

    def __init__(self, session: Any):
        self._proxy = NoCloseSession(session)

    def __call__(self) -> NoCloseSession:
        return self._proxy


def reset_ws_state() -> None:
    """Remet a zero toutes les structures partagees de `ws_manager`."""
    ws_manager.user_connections.clear()
    ws_manager.agent_connections.clear()
    ws_manager.agent_owners.clear()
    ws_manager.user_event_buffer.clear()
