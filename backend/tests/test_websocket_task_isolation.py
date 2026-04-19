"""
Tests d'isolation cross-agent sur les messages WebSocket task_status et task_result.

Verifie qu'un agent ne peut pas modifier les taches d'un autre agent via WebSocket.
"""

import logging

import pytest

from app.core.security import create_agent_token
from app.models.agent import Agent
from app.models.agent_task import AgentTask


@pytest.fixture
def agent_a(db_session, admin_user):
    """Agent A appartenant a admin_user."""
    agent = Agent(
        name="Agent-A",
        user_id=admin_user.id,
        status="active",
        agent_uuid="agent-a-uuid",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def agent_b(db_session, auditeur_user):
    """Agent B appartenant a auditeur_user."""
    agent = Agent(
        name="Agent-B",
        user_id=auditeur_user.id,
        status="active",
        agent_uuid="agent-b-uuid",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def task_for_agent_b(db_session, agent_b, auditeur_user):
    """Tache assignee a agent B."""
    task = AgentTask(
        agent_id=agent_b.id,
        owner_id=auditeur_user.id,
        tool="nmap",
        parameters={"target": "192.168.1.1"},
        status="dispatched",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def task_for_agent_a(db_session, agent_a, admin_user):
    """Tache assignee a agent A."""
    task = AgentTask(
        agent_id=agent_a.id,
        owner_id=admin_user.id,
        tool="nmap",
        parameters={"target": "10.0.0.1"},
        status="dispatched",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture(autouse=True)
def _patch_session_local(db_session, monkeypatch):
    """Redirige SessionLocal vers la session de test."""
    monkeypatch.setattr(
        "app.core.database.SessionLocal",
        lambda: db_session,
    )
    # Empecher db.close() de fermer la session de test
    monkeypatch.setattr(db_session, "close", lambda: None)


@pytest.fixture(autouse=True)
def _clear_global_ws_manager():
    """Reset global ws_manager state entre les tests."""
    from app.core.websocket_manager import ws_manager

    ws_manager.user_connections.clear()
    ws_manager.agent_connections.clear()
    ws_manager.user_event_buffer.clear()
    yield
    ws_manager.user_connections.clear()
    ws_manager.agent_connections.clear()
    ws_manager.user_event_buffer.clear()


class TestTaskStatusCrossAgent:
    """Agent A envoie task_status pour une tache d'agent B → rejete."""

    def test_cross_agent_task_status_rejected(
        self,
        client,
        agent_a,
        agent_b,
        task_for_agent_b,
        db_session,
        admin_user,
    ):
        """Agent A ne peut pas modifier le status d'une tache d'agent B."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with client.websocket_connect(f"/ws/agent?token={token}") as ws:
            ws.send_json(
                {
                    "type": "task_status",
                    "data": {
                        "task_uuid": task_for_agent_b.task_uuid,
                        "status": "running",
                    },
                }
            )
            # Envoyer un heartbeat pour confirmer que la connexion fonctionne
            ws.send_json({"type": "heartbeat"})
            resp = ws.receive_json()
            assert resp["type"] == "heartbeat_ack"

        # Verifier que la tache n'a PAS ete modifiee
        db_session.refresh(task_for_agent_b)
        assert task_for_agent_b.status == "dispatched"

    def test_cross_agent_task_status_logs_warning(
        self,
        client,
        agent_a,
        task_for_agent_b,
        db_session,
        admin_user,
        caplog,
    ):
        """Un warning est emis quand un agent tente de modifier une tache etrangere."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with caplog.at_level(logging.WARNING):
            with client.websocket_connect(f"/ws/agent?token={token}") as ws:
                ws.send_json(
                    {
                        "type": "task_status",
                        "data": {
                            "task_uuid": task_for_agent_b.task_uuid,
                            "status": "running",
                        },
                    }
                )
                ws.send_json({"type": "heartbeat"})
                ws.receive_json()

        assert any("attempted task_status" in r.message for r in caplog.records)


class TestTaskResultCrossAgent:
    """Agent A envoie task_result pour une tache d'agent B → rejete."""

    def test_cross_agent_task_result_rejected(
        self,
        client,
        agent_a,
        agent_b,
        task_for_agent_b,
        db_session,
        admin_user,
    ):
        """Agent A ne peut pas completer une tache d'agent B."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with client.websocket_connect(f"/ws/agent?token={token}") as ws:
            ws.send_json(
                {
                    "type": "task_result",
                    "data": {
                        "task_uuid": task_for_agent_b.task_uuid,
                        "result_summary": {"injected": True},
                    },
                }
            )
            ws.send_json({"type": "heartbeat"})
            resp = ws.receive_json()
            assert resp["type"] == "heartbeat_ack"

        # Tache toujours en status dispatched
        db_session.refresh(task_for_agent_b)
        assert task_for_agent_b.status == "dispatched"
        assert task_for_agent_b.result_summary is None

    def test_cross_agent_task_result_logs_warning(
        self,
        client,
        agent_a,
        task_for_agent_b,
        db_session,
        admin_user,
        caplog,
    ):
        """Un warning est emis pour task_result cross-agent."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with caplog.at_level(logging.WARNING):
            with client.websocket_connect(f"/ws/agent?token={token}") as ws:
                ws.send_json(
                    {
                        "type": "task_result",
                        "data": {
                            "task_uuid": task_for_agent_b.task_uuid,
                            "result_summary": {"injected": True},
                        },
                    }
                )
                ws.send_json({"type": "heartbeat"})
                ws.receive_json()

        assert any("attempted task_result" in r.message for r in caplog.records)


class TestOwnTaskStillWorks:
    """Agent A envoie task_status/task_result pour sa propre tache → fonctionne."""

    def test_own_task_status_succeeds(
        self,
        client,
        agent_a,
        task_for_agent_a,
        db_session,
        admin_user,
    ):
        """Agent A peut modifier le status de sa propre tache."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with client.websocket_connect(f"/ws/agent?token={token}") as ws:
            ws.send_json(
                {
                    "type": "task_status",
                    "data": {
                        "task_uuid": task_for_agent_a.task_uuid,
                        "status": "running",
                    },
                }
            )
            ws.send_json({"type": "heartbeat"})
            resp = ws.receive_json()
            assert resp["type"] == "heartbeat_ack"

        # Note: la deconnexion WS marque les taches "running" comme "failed" (orphan handler)
        # On verifie que started_at a bien ete renseigne (prouve que task_status a ete traite)
        db_session.refresh(task_for_agent_a)
        assert task_for_agent_a.started_at is not None

    def test_own_task_result_succeeds(
        self,
        client,
        agent_a,
        task_for_agent_a,
        db_session,
        admin_user,
    ):
        """Agent A peut envoyer le resultat de sa propre tache."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with client.websocket_connect(f"/ws/agent?token={token}") as ws:
            ws.send_json(
                {
                    "type": "task_result",
                    "data": {
                        "task_uuid": task_for_agent_a.task_uuid,
                        "result_summary": {"hosts_found": 3},
                    },
                }
            )
            ws.send_json({"type": "heartbeat"})
            resp = ws.receive_json()
            assert resp["type"] == "heartbeat_ack"

        db_session.refresh(task_for_agent_a)
        assert task_for_agent_a.status == "completed"
        assert task_for_agent_a.progress == 100
        assert task_for_agent_a.result_summary == {"hosts_found": 3}

    def test_own_task_progress_persists(
        self,
        client,
        agent_a,
        task_for_agent_a,
        db_session,
        admin_user,
    ):
        """Agent A envoie task_progress → AgentTask.progress est mis a jour."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with client.websocket_connect(f"/ws/agent?token={token}") as ws:
            ws.send_json(
                {
                    "type": "task_progress",
                    "data": {
                        "task_uuid": task_for_agent_a.task_uuid,
                        "progress": 42,
                    },
                }
            )
            ws.send_json({"type": "heartbeat"})
            resp = ws.receive_json()
            assert resp["type"] == "heartbeat_ack"

        db_session.refresh(task_for_agent_a)
        assert task_for_agent_a.progress == 42

    def test_own_task_progress_clamped(
        self,
        client,
        agent_a,
        task_for_agent_a,
        db_session,
        admin_user,
    ):
        """task_progress avec valeur hors bornes est clampe a [0, 100]."""
        token = create_agent_token(agent_uuid=agent_a.agent_uuid, owner_id=admin_user.id)
        with client.websocket_connect(f"/ws/agent?token={token}") as ws:
            ws.send_json(
                {
                    "type": "task_progress",
                    "data": {"task_uuid": task_for_agent_a.task_uuid, "percent": 150},
                }
            )
            ws.send_json({"type": "heartbeat"})
            ws.receive_json()

        db_session.refresh(task_for_agent_a)
        assert task_for_agent_a.progress == 100
