"""
Tests unitaires — _replay_buffered_events index tracking.

Vérifie que la déconnexion mid-replay re-bufferise correctement les events restants,
et que deux events au même timestamp ne causent pas de confusion d'index.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect

from app.core.websocket_manager import ConnectionManager


def _make_event(n: int) -> dict:
    return {"type": "test", "data": {"n": n}}


def _ts() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def manager():
    return ConnectionManager()


class TestReplayBufferedEvents:
    def test_full_replay_clears_buffer(self, manager):
        """Replay complet sans déconnexion → buffer vidé."""
        user_id = 1
        manager.user_event_buffer[user_id] = [(_ts(), _make_event(i)) for i in range(5)]

        ws = AsyncMock()
        asyncio.run(manager._replay_buffered_events(user_id, ws))

        assert ws.send_json.call_count == 5
        assert user_id not in manager.user_event_buffer

    def test_disconnect_at_third_rebuffers_remaining(self, manager):
        """Déconnexion au 3ème event → les 3 restants (idx 2,3,4) sont re-bufferisés."""
        user_id = 2
        events = [_make_event(i) for i in range(5)]
        manager.user_event_buffer[user_id] = [(_ts(), ev) for ev in events]

        call_count = 0

        async def fail_on_third(event):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise WebSocketDisconnect()

        ws = AsyncMock()
        ws.send_json.side_effect = fail_on_third

        asyncio.run(manager._replay_buffered_events(user_id, ws))

        # 3 appels (0, 1, 2 — le 3ème lève l'exception)
        assert call_count == 3
        # Les events 2, 3, 4 doivent être re-bufferisés
        remaining = manager.user_event_buffer[user_id]
        assert len(remaining) == 3
        remaining_events = [ev for _, ev in remaining]
        assert remaining_events == [events[2], events[3], events[4]]

    def test_same_timestamp_no_index_confusion(self, manager):
        """Deux events au même timestamp → pas de confusion d'index."""
        user_id = 3
        same_ts = _ts()
        events = [_make_event(i) for i in range(4)]
        # Tous au même timestamp
        manager.user_event_buffer[user_id] = [(same_ts, ev) for ev in events]

        call_count = 0

        async def fail_on_second(event):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("connection lost")

        ws = AsyncMock()
        ws.send_json.side_effect = fail_on_second

        asyncio.run(manager._replay_buffered_events(user_id, ws))

        # Events 1, 2, 3 restants (idx 1 a échoué)
        remaining = manager.user_event_buffer[user_id]
        assert len(remaining) == 3
        remaining_events = [ev for _, ev in remaining]
        assert remaining_events == [events[1], events[2], events[3]]
