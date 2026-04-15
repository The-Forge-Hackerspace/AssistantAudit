"""
Tests pour la reconnexion agent (TOS-12).

Verifie que :
- un agent offline qui se reconnecte est restaure en active,
- une seconde connexion pour le meme agent_uuid remplace la premiere.
"""

from unittest.mock import patch

import pytest

from app.core.security import create_agent_token
from app.models.agent import Agent

from tests.ws_helpers import FakeSessionLocal, reset_ws_state


@pytest.fixture(autouse=True)
def _clear_ws_state():
    reset_ws_state()
    yield
    reset_ws_state()


@pytest.fixture
def patch_session_local(db_session):
    fake = FakeSessionLocal(db_session)
    with patch("app.core.database.SessionLocal", fake):
        yield


class TestAgentReconnect:
    def test_offline_agent_restored_on_reconnect(
        self, client, db_session, auditeur_user, patch_session_local
    ):
        """Un agent marque offline (sweeper) qui se reconnecte repasse en active."""
        agent = Agent(
            name="Reconnect-Agent",
            user_id=auditeur_user.id,
            status="offline",
            agent_uuid="agent-reconnect-offline",
        )
        db_session.add(agent)
        db_session.commit()
        agent_id = agent.id

        token = create_agent_token(agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id)

        with client.websocket_connect(f"/ws/agent?token={token}") as ws:
            ws.send_json({"type": "heartbeat"})
            ws.receive_json()

            # Verifier l'etat AVANT que le WS se ferme (sinon _handle_agent_disconnect
            # remarque l'agent offline en reaction a la deconnexion).
            db_session.expire_all()
            restored = db_session.get(Agent, agent_id)
            assert restored.status == "active"
            assert restored.last_seen is not None
