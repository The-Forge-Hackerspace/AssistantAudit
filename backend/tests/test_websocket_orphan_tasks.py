"""
Tests pour le relais task_progress et la detection des taches orphelines
quand un agent se deconnecte du WebSocket.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.security import create_access_token, create_agent_token
from app.core.websocket_manager import ws_manager
from app.models.agent import Agent
from app.models.agent_task import AgentTask


@pytest.fixture
def agent_with_tasks(db_session, auditeur_user):
    """Cree un agent actif avec des taches dans differents statuts."""
    agent = Agent(
        name="Orphan-Test-Agent",
        user_id=auditeur_user.id,
        status="active",
        agent_uuid="agent-orphan-test",
    )
    db_session.add(agent)
    db_session.flush()

    tasks = {}
    for status in ("running", "dispatched", "pending", "completed", "failed"):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=auditeur_user.id,
            tool="nmap",
            parameters={"target": "10.0.0.1"},
            status=status,
        )
        db_session.add(task)
        db_session.flush()
        tasks[status] = task

    db_session.commit()
    for t in tasks.values():
        db_session.refresh(t)
    return agent, tasks


class _NoCloseSession:
    """Proxy qui intercepte close() pour ne pas fermer la session de test."""
    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        if name == "close":
            return lambda: None  # No-op
        return getattr(self._session, name)


class _FakeSessionLocal:
    """Wrapper pour que SessionLocal() retourne la session de test existante."""
    def __init__(self, session):
        self._proxy = _NoCloseSession(session)

    def __call__(self):
        return self._proxy


@pytest.fixture(autouse=True)
def _clear_ws_state():
    """Reset ws_manager entre les tests."""
    ws_manager.user_connections.clear()
    ws_manager.agent_connections.clear()
    ws_manager.agent_owners.clear()
    ws_manager.user_event_buffer.clear()
    yield
    ws_manager.user_connections.clear()
    ws_manager.agent_connections.clear()
    ws_manager.agent_owners.clear()
    ws_manager.user_event_buffer.clear()


@pytest.fixture
def patch_session_local(db_session):
    """Patch SessionLocal dans websocket.py pour utiliser la session de test."""
    fake = _FakeSessionLocal(db_session)
    with patch("app.core.database.SessionLocal", fake):
        yield


class TestTaskProgressRelay:
    """Verifie que task_progress est relaye vers le bon user."""

    def test_task_progress_relayed_to_owner(
        self, client, auditeur_user, agent_with_tasks
    ):
        """Un message task_progress d'un agent est relaye vers le frontend de l'owner."""
        agent, tasks = agent_with_tasks
        agent_token = create_agent_token(
            agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id
        )
        user_token = create_access_token(subject=auditeur_user.id)

        # Connecter le user frontend
        with client.websocket_connect(f"/ws/user?token={user_token}") as user_ws:
            # Connecter l'agent et envoyer task_progress
            with client.websocket_connect(f"/ws/agent?token={agent_token}") as agent_ws:
                agent_ws.send_json({"type": "heartbeat"})
                agent_ws.receive_json()  # heartbeat_ack

                agent_ws.send_json({
                    "type": "task_progress",
                    "data": {
                        "task_uuid": tasks["running"].task_uuid,
                        "progress": 42,
                        "message": "Scanning port 80",
                    },
                })

            # Le user doit recevoir le message relaye
            msg = user_ws.receive_json()
            assert msg["type"] == "task_progress"
            assert msg["data"]["task_uuid"] == tasks["running"].task_uuid
            assert msg["data"]["progress"] == 42

    def test_task_progress_uses_jwt_owner_not_message(
        self, client, auditeur_user, agent_with_tasks
    ):
        """L'owner_id est extrait du JWT agent, pas du message."""
        agent, tasks = agent_with_tasks
        agent_token = create_agent_token(
            agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id
        )

        # Pas de user connecte — le message est bufferise pour le bon owner
        with client.websocket_connect(f"/ws/agent?token={agent_token}") as agent_ws:
            agent_ws.send_json({"type": "heartbeat"})
            agent_ws.receive_json()

            agent_ws.send_json({
                "type": "task_progress",
                "data": {
                    "task_uuid": tasks["running"].task_uuid,
                    "progress": 50,
                },
            })

        # Verifie que le buffer est pour le bon user_id (du JWT, pas du message)
        assert auditeur_user.id in ws_manager.user_event_buffer
        events = ws_manager.user_event_buffer[auditeur_user.id]
        assert any(
            ev["type"] == "task_progress" for _, ev in events
        )


class TestOrphanTaskDetection:
    """Verifie que les taches running/dispatched sont marquees failed quand l'agent se deconnecte."""

    def test_disconnect_marks_running_tasks_failed(
        self, client, db_session, auditeur_user, agent_with_tasks, patch_session_local
    ):
        """Deconnexion agent -> taches running/dispatched/pending passent en failed."""
        agent, tasks = agent_with_tasks
        agent_token = create_agent_token(
            agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id
        )

        # Connecter puis deconnecter l'agent
        with client.websocket_connect(f"/ws/agent?token={agent_token}") as agent_ws:
            agent_ws.send_json({"type": "heartbeat"})
            agent_ws.receive_json()

        # Apres deconnexion, verifier en base
        db_session.expire_all()

        running_task = db_session.get(AgentTask, tasks["running"].id)
        assert running_task.status == "failed"
        assert "deconnecte" in running_task.error_message.lower()
        assert running_task.completed_at is not None

        dispatched_task = db_session.get(AgentTask, tasks["dispatched"].id)
        assert dispatched_task.status == "failed"
        assert dispatched_task.completed_at is not None

    def test_disconnect_does_not_touch_completed_tasks(
        self, client, db_session, auditeur_user, agent_with_tasks, patch_session_local
    ):
        """Les taches deja completed/failed ne sont pas modifiees."""
        agent, tasks = agent_with_tasks
        agent_token = create_agent_token(
            agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id
        )

        with client.websocket_connect(f"/ws/agent?token={agent_token}") as agent_ws:
            agent_ws.send_json({"type": "heartbeat"})
            agent_ws.receive_json()

        db_session.expire_all()

        completed_task = db_session.get(AgentTask, tasks["completed"].id)
        assert completed_task.status == "completed"

        failed_task = db_session.get(AgentTask, tasks["failed"].id)
        assert failed_task.status == "failed"
        # L'error_message d'origine ne doit pas etre ecrase
        assert failed_task.error_message is None or "deconnecte" not in (failed_task.error_message or "")

    def test_disconnect_notifies_frontend(
        self, client, auditeur_user, agent_with_tasks, patch_session_local
    ):
        """Deconnexion agent -> le frontend est notifie du status failed pour chaque tache orpheline."""
        agent, tasks = agent_with_tasks
        agent_token = create_agent_token(
            agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id
        )

        # Pas de user connecte — les notifications seront bufferisees
        with client.websocket_connect(f"/ws/agent?token={agent_token}") as agent_ws:
            agent_ws.send_json({"type": "heartbeat"})
            agent_ws.receive_json()

        # Verifier les evenements bufferises
        assert auditeur_user.id in ws_manager.user_event_buffer
        events = [ev for _, ev in ws_manager.user_event_buffer[auditeur_user.id]]
        status_events = [e for e in events if e["type"] == "task_status"]

        # Il doit y avoir des notifications pour les taches orphelines
        failed_uuids = {e["data"]["task_uuid"] for e in status_events}
        assert tasks["running"].task_uuid in failed_uuids
        assert tasks["dispatched"].task_uuid in failed_uuids

        # Chaque notification doit contenir le status failed
        for e in status_events:
            assert e["data"]["status"] == "failed"
            assert "deconnecte" in e["data"].get("error_message", "").lower()

    def test_disconnect_handler_uses_session_local(
        self, client, db_session, auditeur_user, agent_with_tasks, patch_session_local
    ):
        """Le handler de deconnexion utilise sa propre session DB (SessionLocal)."""
        agent, tasks = agent_with_tasks
        agent_token = create_agent_token(
            agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id
        )

        with client.websocket_connect(f"/ws/agent?token={agent_token}") as agent_ws:
            agent_ws.send_json({"type": "heartbeat"})
            agent_ws.receive_json()

        # Si on arrive ici sans crash, le handler a reussi a ouvrir
        # sa propre session et a commit les changements
        db_session.expire_all()
        running_task = db_session.get(AgentTask, tasks["running"].id)
        assert running_task.status == "failed"
