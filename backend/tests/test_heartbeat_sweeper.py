"""
Tests pour le sweeper de heartbeat agents (TOS-12).

Verifie que :
- les agents actifs dont last_seen est ancien passent en offline,
- leurs taches running/dispatched/pending passent en failed,
- les agents recents ne sont pas touches,
- les agents avec WS encore vivant sont ignores,
- le owner est notifie via ws_manager.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core import heartbeat_sweeper
from app.core.websocket_manager import ws_manager
from app.models.agent import Agent
from app.models.agent_task import AgentTask
from tests.ws_helpers import FakeSessionLocal, reset_ws_state


@pytest.fixture(autouse=True)
def _clear_ws_state():
    reset_ws_state()
    yield
    reset_ws_state()


@pytest.fixture
def patch_sweeper_session(db_session):
    fake = FakeSessionLocal(db_session)
    with patch("app.core.heartbeat_sweeper.SessionLocal", fake):
        yield


def _make_agent(db_session, user, *, uuid: str, last_seen_offset_seconds: int, status: str = "active") -> Agent:
    agent = Agent(
        name=f"Sweeper-{uuid}",
        user_id=user.id,
        status=status,
        agent_uuid=uuid,
        last_seen=datetime.now(timezone.utc) - timedelta(seconds=last_seen_offset_seconds),
    )
    db_session.add(agent)
    db_session.flush()
    return agent


def _add_task(db_session, agent, user, *, status: str) -> AgentTask:
    task = AgentTask(
        agent_id=agent.id,
        owner_id=user.id,
        tool="nmap",
        parameters={"target": "10.0.0.1"},
        status=status,
    )
    db_session.add(task)
    db_session.flush()
    return task


class TestHeartbeatSweeper:
    def test_stale_agent_marked_offline_and_tasks_failed(
        self, db_session, auditeur_user, patch_sweeper_session
    ):
        """Agent actif avec last_seen > timeout -> offline + taches failed."""
        agent = _make_agent(db_session, auditeur_user, uuid="stale-agent", last_seen_offset_seconds=300)
        running = _add_task(db_session, agent, auditeur_user, status="running")
        dispatched = _add_task(db_session, agent, auditeur_user, status="dispatched")
        completed = _add_task(db_session, agent, auditeur_user, status="completed")
        db_session.commit()

        asyncio.run(heartbeat_sweeper._sweep_once())

        db_session.expire_all()
        assert db_session.get(Agent, agent.id).status == "offline"
        assert db_session.get(AgentTask, running.id).status == "failed"
        assert db_session.get(AgentTask, running.id).error_message == "Agent timeout"
        assert db_session.get(AgentTask, dispatched.id).status == "failed"
        # Les taches deja terminees ne sont pas touchees
        assert db_session.get(AgentTask, completed.id).status == "completed"

    def test_recent_agent_not_touched(self, db_session, auditeur_user, patch_sweeper_session):
        """Agent avec last_seen recent -> rien ne change."""
        agent = _make_agent(db_session, auditeur_user, uuid="fresh-agent", last_seen_offset_seconds=10)
        running = _add_task(db_session, agent, auditeur_user, status="running")
        db_session.commit()

        asyncio.run(heartbeat_sweeper._sweep_once())

        db_session.expire_all()
        assert db_session.get(Agent, agent.id).status == "active"
        assert db_session.get(AgentTask, running.id).status == "running"

    def test_agent_with_live_ws_skipped(self, db_session, auditeur_user, patch_sweeper_session):
        """Un agent encore connecte en WS est ignore par le sweeper."""
        agent = _make_agent(db_session, auditeur_user, uuid="connected-agent", last_seen_offset_seconds=300)
        running = _add_task(db_session, agent, auditeur_user, status="running")
        db_session.commit()

        # Simuler une connexion WS vivante
        ws_manager.agent_connections[agent.agent_uuid] = object()  # type: ignore[assignment]

        asyncio.run(heartbeat_sweeper._sweep_once())

        db_session.expire_all()
        assert db_session.get(Agent, agent.id).status == "active"
        assert db_session.get(AgentTask, running.id).status == "running"

    def test_offline_agent_ignored(self, db_session, auditeur_user, patch_sweeper_session):
        """Un agent deja offline n'est pas retraite."""
        agent = _make_agent(
            db_session, auditeur_user, uuid="already-offline", last_seen_offset_seconds=1000, status="offline"
        )
        db_session.commit()

        asyncio.run(heartbeat_sweeper._sweep_once())

        db_session.expire_all()
        assert db_session.get(Agent, agent.id).status == "offline"

    def test_owner_notification_online(
        self, db_session, auditeur_user, patch_sweeper_session, monkeypatch
    ):
        """Owner en ligne : le sweeper envoie directement via send_to_user."""
        agent = _make_agent(
            db_session, auditeur_user, uuid="notify-agent-online", last_seen_offset_seconds=300
        )
        running = _add_task(db_session, agent, auditeur_user, status="running")
        db_session.commit()

        # Espionner send_to_user et simuler un owner en ligne. ws_manager.send_to_user
        # gere deja le routage online/buffered — on remplace l'implementation pour
        # capturer les appels et verifier le contrat attendu par le sweeper.
        sent: list[tuple[int, str, dict]] = []

        async def fake_send_to_user(user_id, event_type, data):
            sent.append((user_id, event_type, data))

        monkeypatch.setattr(ws_manager, "send_to_user", fake_send_to_user)

        asyncio.run(heartbeat_sweeper._sweep_once())

        task_status_events = [
            (uid, evt, data) for uid, evt, data in sent if evt == "task_status"
        ]
        assert task_status_events, "send_to_user n'a pas ete appele pour task_status"
        owner_ids = {uid for uid, _, _ in task_status_events}
        assert auditeur_user.id in owner_ids
        task_uuids = {data["task_uuid"] for _, _, data in task_status_events}
        assert running.task_uuid in task_uuids
        for _, _, data in task_status_events:
            assert data["status"] == "failed"
            assert data["error_message"] == "Agent timeout"

    def test_owner_notification_buffered(self, db_session, auditeur_user, patch_sweeper_session):
        """Le owner recoit task_status pour chaque tache orpheline (bufferise si hors ligne)."""
        agent = _make_agent(db_session, auditeur_user, uuid="notify-agent", last_seen_offset_seconds=300)
        running = _add_task(db_session, agent, auditeur_user, status="running")
        db_session.commit()

        asyncio.run(heartbeat_sweeper._sweep_once())

        assert auditeur_user.id in ws_manager.user_event_buffer
        events = [ev for _, ev in ws_manager.user_event_buffer[auditeur_user.id]]
        task_uuids = {e["data"]["task_uuid"] for e in events if e["type"] == "task_status"}
        assert running.task_uuid in task_uuids
        for e in events:
            if e["type"] == "task_status":
                assert e["data"]["status"] == "failed"
                assert e["data"]["error_message"] == "Agent timeout"
