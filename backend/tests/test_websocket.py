"""
Tests pour core/websocket_manager.py et api/v1/websocket.py.
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.core.security import create_access_token, create_agent_token
from app.core.websocket_manager import (
    BUFFER_MAX_SIZE,
    BUFFER_TTL_SECONDS,
    ConnectionManager,
)


# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def manager():
    """Fresh ConnectionManager for each test."""
    return ConnectionManager()


# ────────────────────────────────────────────────────────────────────────
# Integration: /ws/user endpoint
# ────────────────────────────────────────────────────────────────────────


class TestUserWebSocket:
    def test_connect_user_valid_token(self, client, admin_user):
        token = create_access_token(subject=admin_user.id)
        with client.websocket_connect(f"/api/v1/ws/user?token={token}") as ws:
            ws.send_json({"command": "ping"})
            resp = ws.receive_json()
            assert resp["type"] == "pong"

    def test_connect_user_invalid_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws/user?token=invalid.jwt") as ws:
                ws.receive_json()

    def test_connect_user_no_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws/user") as ws:
                ws.receive_json()

    def test_connect_user_agent_token_rejected(self, client):
        token = create_agent_token(agent_uuid="fake", owner_id=1)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/ws/user?token={token}") as ws:
                ws.receive_json()


# ────────────────────────────────────────────────────────────────────────
# Integration: /ws/agent endpoint
# ────────────────────────────────────────────────────────────────────────


class TestAgentWebSocket:
    def test_connect_agent_valid_token(self, client, admin_user, db_session):
        from app.models.agent import Agent

        agent = Agent(
            name="WS-Test-Agent",
            user_id=admin_user.id,
            status="active",
            agent_uuid="agent-ws-test",
        )
        db_session.add(agent)
        db_session.commit()

        token = create_agent_token(agent_uuid="agent-ws-test", owner_id=admin_user.id)
        with client.websocket_connect(f"/api/v1/ws/agent?token={token}") as ws:
            ws.send_json({"type": "heartbeat"})
            resp = ws.receive_json()
            assert resp["type"] == "heartbeat_ack"

    def test_connect_agent_user_token_rejected(self, client, admin_user):
        token = create_access_token(subject=admin_user.id)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/ws/agent?token={token}") as ws:
                ws.receive_json()

    def test_connect_agent_no_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws/agent") as ws:
                ws.receive_json()


# ────────────────────────────────────────────────────────────────────────
# Unit: ConnectionManager buffering (async tests)
# ────────────────────────────────────────────────────────────────────────


class TestBuffering:
    @pytest.mark.asyncio
    async def test_buffer_event_when_disconnected(self, manager):
        """Un evenement est bufferise si le user n'est pas connecte."""
        await manager.send_to_user(999, "test_event", {"msg": "hello"})

        assert 999 in manager.user_event_buffer
        assert len(manager.user_event_buffer[999]) == 1
        _, event = manager.user_event_buffer[999][0]
        assert event["type"] == "test_event"
        assert event["data"]["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_event_format(self, manager):
        """Les evenements ont type, data, timestamp."""
        await manager.send_to_user(1, "scan_progress", {"progress": 50})

        _, event = manager.user_event_buffer[1][0]
        assert event["type"] == "scan_progress"
        assert event["data"] == {"progress": 50}
        assert "timestamp" in event
        datetime.fromisoformat(event["timestamp"])

    @pytest.mark.asyncio
    async def test_buffer_ttl_cleanup(self, manager):
        """Les evenements expires sont supprimes du buffer."""
        expired_ts = datetime.now(timezone.utc) - timedelta(seconds=BUFFER_TTL_SECONDS + 1)
        manager.user_event_buffer[1] = [
            (expired_ts, {"type": "old", "data": {}, "timestamp": ""}),
        ]

        await manager.send_to_user(1, "new_event", {"msg": "fresh"})

        assert len(manager.user_event_buffer[1]) == 1
        _, event = manager.user_event_buffer[1][0]
        assert event["type"] == "new_event"

    @pytest.mark.asyncio
    async def test_buffer_max_size_truncation(self, manager):
        """Le buffer est tronque a BUFFER_MAX_SIZE."""
        now = datetime.now(timezone.utc)
        manager.user_event_buffer[1] = [
            (now, {"type": f"event_{i}", "data": {}, "timestamp": ""})
            for i in range(BUFFER_MAX_SIZE)
        ]

        await manager.send_to_user(1, "overflow", {"msg": "last"})

        assert len(manager.user_event_buffer[1]) == BUFFER_MAX_SIZE
        _, last = manager.user_event_buffer[1][-1]
        assert last["type"] == "overflow"

    @pytest.mark.asyncio
    async def test_no_buffer_for_agents(self, manager):
        """Les agents n'ont pas de buffer d'evenements."""
        await manager.send_to_agent("nonexistent-uuid", "task", {"id": 1})
        assert not hasattr(manager, "agent_event_buffer")

    def test_replay_on_reconnect(self, client, admin_user):
        """Les evenements bufferises sont rejoues a la reconnexion."""
        from app.core.websocket_manager import ws_manager

        user_id = admin_user.id

        # Manually buffer events (simulating disconnected state)
        now = datetime.now(timezone.utc)
        ws_manager.user_event_buffer[user_id] = [
            (now, {"type": "event_1", "data": {"n": 1}, "timestamp": now.isoformat()}),
            (now, {"type": "event_2", "data": {"n": 2}, "timestamp": now.isoformat()}),
        ]

        # Reconnect — buffered events should be replayed
        token = create_access_token(subject=user_id)
        with client.websocket_connect(f"/api/v1/ws/user?token={token}") as ws:
            ev1 = ws.receive_json()
            ev2 = ws.receive_json()
            assert ev1["type"] == "event_1"
            assert ev2["type"] == "event_2"

        # Buffer should be cleared after replay
        assert user_id not in ws_manager.user_event_buffer
