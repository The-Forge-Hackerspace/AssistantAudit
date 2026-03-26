"""
Tests pour api/v1/agents.py et services/task_service.py.
Couvre : creation, enrollment, heartbeat, dispatch, status, resultats.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_agent_token,
    create_enrollment_token,
    hash_password,
)
from app.models.agent import Agent
from app.models.agent_task import AgentTask
from app.models.audit import Audit, AuditStatus
from app.models.entreprise import Entreprise
from app.models.user import User


# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def user2(db_session: Session) -> User:
    """Deuxieme technicien pour les tests d'isolation."""
    user = User(
        username="other_tech",
        email="other@test.com",
        password_hash=hash_password("password"),
        full_name="Other Tech",
        role="auditeur",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user2_headers(user2: User) -> dict:
    token = create_access_token(subject=user2.id)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def entreprise(db_session: Session) -> Entreprise:
    e = Entreprise(nom="AgentTestCorp", secteur_activite="IT")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture
def audit_owned(db_session: Session, auditeur_user: User, entreprise: Entreprise) -> Audit:
    """Audit appartenant au auditeur_user."""
    a = Audit(
        nom_projet="Audit Agent Test",
        entreprise_id=entreprise.id,
        owner_id=auditeur_user.id,
        status=AuditStatus.EN_COURS,
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def audit_other(db_session: Session, user2: User, entreprise: Entreprise) -> Audit:
    """Audit appartenant a user2."""
    a = Audit(
        nom_projet="Audit Autre",
        entreprise_id=entreprise.id,
        owner_id=user2.id,
        status=AuditStatus.EN_COURS,
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def active_agent(db_session: Session, auditeur_user: User) -> Agent:
    """Agent actif appartenant a auditeur_user."""
    agent = Agent(
        name="Active-Agent",
        user_id=auditeur_user.id,
        status="active",
        allowed_tools=["nmap", "oradad", "ad_collector"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def agent_headers(active_agent: Agent, auditeur_user: User) -> dict:
    """JWT headers pour un agent actif."""
    token = create_agent_token(
        agent_uuid=active_agent.agent_uuid,
        owner_id=auditeur_user.id,
    )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ────────────────────────────────────────────────────────────────────────
# POST /agents/create
# ────────────────────────────────────────────────────────────────────────


class TestCreateAgent:
    def test_create_agent_success(self, client, auditeur_headers):
        resp = client.post(
            "/api/v1/agents/create",
            json={"name": "PC-Bureau-Test"},
            headers=auditeur_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "agent_uuid" in data
        assert "enrollment_code" in data
        assert len(data["enrollment_code"]) == 8
        assert "expires_at" in data

    def test_create_agent_custom_tools(self, client, auditeur_headers):
        resp = client.post(
            "/api/v1/agents/create",
            json={"name": "Nmap-Only", "allowed_tools": ["nmap"]},
            headers=auditeur_headers,
        )
        assert resp.status_code == 201

    def test_create_agent_lecteur_forbidden(self, client, lecteur_headers):
        resp = client.post(
            "/api/v1/agents/create",
            json={"name": "Should-Fail"},
            headers=lecteur_headers,
        )
        assert resp.status_code == 403


# ────────────────────────────────────────────────────────────────────────
# GET /agents/
# ────────────────────────────────────────────────────────────────────────


class TestListAgents:
    def test_list_own_agents(self, client, auditeur_headers, active_agent):
        resp = client.get("/api/v1/agents/", headers=auditeur_headers)
        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) >= 1
        uuids = {a["agent_uuid"] for a in agents}
        assert active_agent.agent_uuid in uuids

    def test_list_agents_isolation(self, client, user2_headers, active_agent):
        """user2 ne voit pas les agents de auditeur_user."""
        resp = client.get("/api/v1/agents/", headers=user2_headers)
        assert resp.status_code == 200
        agents = resp.json()
        uuids = {a["agent_uuid"] for a in agents}
        assert active_agent.agent_uuid not in uuids


# ────────────────────────────────────────────────────────────────────────
# DELETE /agents/{uuid}
# ────────────────────────────────────────────────────────────────────────


class TestRevokeAgent:
    def test_revoke_own_agent(self, client, auditeur_headers, active_agent):
        resp = client.delete(
            f"/api/v1/agents/{active_agent.agent_uuid}",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200

    def test_revoke_other_user_agent_404(self, client, user2_headers, active_agent):
        resp = client.delete(
            f"/api/v1/agents/{active_agent.agent_uuid}",
            headers=user2_headers,
        )
        assert resp.status_code == 404


# ────────────────────────────────────────────────────────────────────────
# POST /agents/enroll
# ────────────────────────────────────────────────────────────────────────


class TestEnroll:
    def test_enroll_success(self, client, auditeur_headers, db_session):
        # Create agent first
        create_resp = client.post(
            "/api/v1/agents/create",
            json={"name": "Enroll-Test"},
            headers=auditeur_headers,
        )
        code = create_resp.json()["enrollment_code"]

        # Enroll
        resp = client.post(
            "/api/v1/agents/enroll",
            json={"enrollment_code": code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_token" in data
        assert "agent_uuid" in data

    def test_enroll_wrong_code(self, client, auditeur_headers):
        client.post(
            "/api/v1/agents/create",
            json={"name": "Enroll-Bad"},
            headers=auditeur_headers,
        )
        resp = client.post(
            "/api/v1/agents/enroll",
            json={"enrollment_code": "WRONGCOD"},
        )
        assert resp.status_code == 400

    def test_enroll_expired_code(self, client, db_session, auditeur_user):
        """Code expire → 400."""
        import hashlib

        code = "TESTCODE"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        expired = datetime.now(timezone.utc) - timedelta(minutes=1)

        agent = Agent(
            name="Expired-Agent",
            user_id=auditeur_user.id,
            enrollment_token_hash=code_hash,
            enrollment_token_expires=expired,
            status="pending",
        )
        db_session.add(agent)
        db_session.commit()

        resp = client.post(
            "/api/v1/agents/enroll",
            json={"enrollment_code": code},
        )
        assert resp.status_code == 400

    def test_enroll_already_used(self, client, auditeur_headers):
        """Double enrollment → 400."""
        create_resp = client.post(
            "/api/v1/agents/create",
            json={"name": "Double-Enroll"},
            headers=auditeur_headers,
        )
        code = create_resp.json()["enrollment_code"]

        # First enroll succeeds
        resp1 = client.post("/api/v1/agents/enroll", json={"enrollment_code": code})
        assert resp1.status_code == 200

        # Second enroll fails (enrollment_used=True)
        resp2 = client.post("/api/v1/agents/enroll", json={"enrollment_code": code})
        assert resp2.status_code == 400


# ────────────────────────────────────────────────────────────────────────
# POST /agents/heartbeat
# ────────────────────────────────────────────────────────────────────────


class TestHeartbeat:
    def test_heartbeat_updates_last_seen(self, client, agent_headers, active_agent, db_session):
        resp = client.post(
            "/api/v1/agents/heartbeat",
            json={"agent_version": "1.0.0", "os_info": "Windows 11"},
            headers=agent_headers,
        )
        assert resp.status_code == 200

        db_session.refresh(active_agent)
        assert active_agent.agent_version == "1.0.0"
        assert active_agent.os_info == "Windows 11"
        assert active_agent.last_seen is not None

    def test_heartbeat_revoked_agent_401(self, client, db_session, auditeur_user):
        """Un agent revoque ne peut pas envoyer de heartbeat."""
        agent = Agent(
            name="Revoked-Agent",
            user_id=auditeur_user.id,
            status="revoked",
        )
        db_session.add(agent)
        db_session.commit()

        token = create_agent_token(agent_uuid=agent.agent_uuid, owner_id=auditeur_user.id)
        resp = client.post(
            "/api/v1/agents/heartbeat",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401


# ────────────────────────────────────────────────────────────────────────
# POST /agents/tasks/dispatch — Double verification
# ────────────────────────────────────────────────────────────────────────


class TestDispatchTask:
    def test_dispatch_success(self, client, auditeur_headers, active_agent):
        resp = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": active_agent.agent_uuid,
                "tool": "nmap",
                "parameters": {"target": "192.168.1.0/24"},
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tool"] == "nmap"
        assert data["status"] == "pending"
        assert "task_uuid" in data

    def test_dispatch_with_audit(self, client, auditeur_headers, active_agent, audit_owned):
        resp = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": active_agent.agent_uuid,
                "audit_id": audit_owned.id,
                "tool": "nmap",
                "parameters": {"target": "10.0.0.0/24"},
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["audit_id"] == audit_owned.id

    def test_dispatch_other_user_audit_404(self, client, auditeur_headers, active_agent, audit_other):
        """Un audit appartenant a un autre user → 404."""
        resp = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": active_agent.agent_uuid,
                "audit_id": audit_other.id,
                "tool": "nmap",
                "parameters": {},
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 404

    def test_dispatch_other_user_agent_404(self, client, user2_headers, active_agent):
        """Un agent appartenant a un autre user → 404."""
        resp = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": active_agent.agent_uuid,
                "tool": "nmap",
                "parameters": {},
            },
            headers=user2_headers,
        )
        assert resp.status_code == 404

    def test_dispatch_tool_not_allowed_403(self, client, auditeur_headers, active_agent):
        resp = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": active_agent.agent_uuid,
                "tool": "forbidden_tool",
                "parameters": {},
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 403

    def test_dispatch_lecteur_forbidden(self, client, lecteur_headers, active_agent):
        resp = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": active_agent.agent_uuid,
                "tool": "nmap",
                "parameters": {},
            },
            headers=lecteur_headers,
        )
        assert resp.status_code == 403


# ────────────────────────────────────────────────────────────────────────
# PATCH /agents/tasks/{uuid}/status — Auth agent
# ────────────────────────────────────────────────────────────────────────


class TestUpdateTaskStatus:
    def test_update_status_running(
        self, client, auditeur_headers, agent_headers, active_agent, db_session, auditeur_user
    ):
        # Create a task first
        task = AgentTask(
            agent_id=active_agent.id,
            owner_id=auditeur_user.id,
            tool="nmap",
            parameters={"target": "10.0.0.1"},
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        resp = client.patch(
            f"/api/v1/agents/tasks/{task.task_uuid}/status",
            json={"status": "running", "progress": 30},
            headers=agent_headers,
        )
        assert resp.status_code == 200

        db_session.refresh(task)
        assert task.status == "running"
        assert task.progress == 30
        assert task.started_at is not None

    def test_update_status_completed(
        self, client, agent_headers, active_agent, db_session, auditeur_user
    ):
        task = AgentTask(
            agent_id=active_agent.id,
            owner_id=auditeur_user.id,
            tool="nmap",
            parameters={},
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        resp = client.patch(
            f"/api/v1/agents/tasks/{task.task_uuid}/status",
            json={"status": "completed"},
            headers=agent_headers,
        )
        assert resp.status_code == 200

        db_session.refresh(task)
        assert task.status == "completed"
        assert task.progress == 100
        assert task.completed_at is not None

    def test_update_wrong_agent_404(
        self, client, db_session, auditeur_user, user2
    ):
        """Un agent ne peut pas modifier une tache d'un autre agent."""
        other_agent = Agent(
            name="Other-Agent",
            user_id=user2.id,
            status="active",
        )
        db_session.add(other_agent)
        db_session.commit()

        task = AgentTask(
            agent_id=other_agent.id,
            owner_id=user2.id,
            tool="nmap",
            parameters={},
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Agent de auditeur_user essaie de modifier la tache
        agent_me = Agent(
            name="My-Agent",
            user_id=auditeur_user.id,
            status="active",
        )
        db_session.add(agent_me)
        db_session.commit()

        token = create_agent_token(agent_uuid=agent_me.agent_uuid, owner_id=auditeur_user.id)
        resp = client.patch(
            f"/api/v1/agents/tasks/{task.task_uuid}/status",
            json={"status": "completed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
