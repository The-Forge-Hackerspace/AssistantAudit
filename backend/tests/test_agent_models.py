"""
Tests unitaires pour les modeles Agent et AgentTask.
CRUD, relations, contraintes d'unicite, valeurs par defaut.
"""
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password
from app.models.agent import Agent
from app.models.agent_task import AgentTask
from app.models.user import User
from app.models.audit import Audit, AuditStatus
from app.models.entreprise import Entreprise


# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    """DB en memoire avec toutes les tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(db: Session) -> User:
    """Technicien de test."""
    u = User(
        username="tech_jean",
        email="jean@test.com",
        password_hash=hash_password("password123"),
        full_name="Jean Technicien",
        role="auditeur",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def user2(db: Session) -> User:
    """Deuxieme technicien."""
    u = User(
        username="tech_marie",
        email="marie@test.com",
        password_hash=hash_password("password456"),
        full_name="Marie Technicienne",
        role="auditeur",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def entreprise(db: Session) -> Entreprise:
    """Entreprise de test."""
    e = Entreprise(nom="TestCorp", secteur_activite="IT")
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@pytest.fixture
def audit(db: Session, entreprise: Entreprise) -> Audit:
    """Audit de test."""
    a = Audit(
        nom_projet="Audit Test",
        entreprise_id=entreprise.id,
        status=AuditStatus.EN_COURS,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@pytest.fixture
def agent(db: Session, user: User) -> Agent:
    """Agent de test."""
    a = Agent(name="PC-Bureau-Jean", user_id=user.id)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ────────────────────────────────────────────────────────────────────────
# Agent — CRUD
# ────────────────────────────────────────────────────────────────────────


class TestAgentCRUD:
    def test_create_agent(self, db: Session, user: User):
        agent = Agent(name="Laptop-Terrain", user_id=user.id)
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.id is not None
        assert agent.agent_uuid is not None
        assert len(agent.agent_uuid) == 36  # UUID format
        assert agent.name == "Laptop-Terrain"
        assert agent.user_id == user.id
        assert agent.status == "pending"
        assert agent.enrollment_used is False

    def test_read_agent(self, db: Session, agent: Agent):
        fetched = db.get(Agent, agent.id)
        assert fetched is not None
        assert fetched.name == "PC-Bureau-Jean"
        assert fetched.agent_uuid == agent.agent_uuid

    def test_list_agents_by_user(self, db: Session, user: User):
        a1 = Agent(name="Agent-1", user_id=user.id)
        a2 = Agent(name="Agent-2", user_id=user.id)
        db.add_all([a1, a2])
        db.commit()

        agents = db.query(Agent).filter(Agent.user_id == user.id).all()
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"Agent-1", "Agent-2"}

    def test_update_agent_status(self, db: Session, agent: Agent):
        agent.status = "active"
        agent.os_info = "Windows 11 Pro 23H2"
        agent.agent_version = "1.0.0"
        db.commit()
        db.refresh(agent)

        assert agent.status == "active"
        assert agent.os_info == "Windows 11 Pro 23H2"

    def test_delete_agent(self, db: Session, agent: Agent):
        agent_id = agent.id
        db.delete(agent)
        db.commit()

        assert db.get(Agent, agent_id) is None


# ────────────────────────────────────────────────────────────────────────
# Agent — Defaults et contraintes
# ────────────────────────────────────────────────────────────────────────


class TestAgentDefaults:
    def test_default_allowed_tools(self, db: Session, user: User):
        agent = Agent(name="Test-Agent", user_id=user.id)
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.allowed_tools == ["nmap", "oradad", "ad_collector"]

    def test_custom_allowed_tools(self, db: Session, user: User):
        agent = Agent(
            name="Nmap-Only",
            user_id=user.id,
            allowed_tools=["nmap"],
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.allowed_tools == ["nmap"]

    def test_agent_uuid_auto_generated(self, db: Session, user: User):
        a1 = Agent(name="A1", user_id=user.id)
        a2 = Agent(name="A2", user_id=user.id)
        db.add_all([a1, a2])
        db.commit()

        assert a1.agent_uuid != a2.agent_uuid

    def test_agent_uuid_unique_constraint(self, db: Session, user: User):
        fixed_uuid = str(uuid.uuid4())
        a1 = Agent(name="A1", user_id=user.id, agent_uuid=fixed_uuid)
        db.add(a1)
        db.commit()

        a2 = Agent(name="A2", user_id=user.id, agent_uuid=fixed_uuid)
        db.add(a2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_cert_fingerprint_unique_constraint(self, db: Session, user: User):
        fp = "a" * 64
        a1 = Agent(name="A1", user_id=user.id, cert_fingerprint=fp)
        db.add(a1)
        db.commit()

        a2 = Agent(name="A2", user_id=user.id, cert_fingerprint=fp)
        db.add(a2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_created_at_auto_set(self, db: Session, user: User):
        agent = Agent(name="Test", user_id=user.id)
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.created_at is not None


# ────────────────────────────────────────────────────────────────────────
# AgentTask — CRUD
# ────────────────────────────────────────────────────────────────────────


class TestAgentTaskCRUD:
    def test_create_task(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="nmap",
            parameters={"target": "192.168.1.0/24", "scan_type": "quick"},
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.id is not None
        assert task.task_uuid is not None
        assert len(task.task_uuid) == 36
        assert task.tool == "nmap"
        assert task.status == "pending"
        assert task.progress == 0
        assert task.parameters["target"] == "192.168.1.0/24"

    def test_read_task(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="oradad",
            parameters={"domain": "corp.local"},
        )
        db.add(task)
        db.commit()

        fetched = db.get(AgentTask, task.id)
        assert fetched is not None
        assert fetched.tool == "oradad"

    def test_update_task_status_and_progress(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="nmap",
            parameters={"target": "10.0.0.0/24"},
        )
        db.add(task)
        db.commit()

        task.status = "running"
        task.progress = 50
        task.status_message = "Scanning in progress..."
        db.commit()
        db.refresh(task)

        assert task.status == "running"
        assert task.progress == 50
        assert task.status_message == "Scanning in progress..."

    def test_update_task_result(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="nmap",
            parameters={"target": "10.0.0.1"},
        )
        db.add(task)
        db.commit()

        task.status = "completed"
        task.progress = 100
        task.result_summary = {"hosts_found": 5, "open_ports": 12}
        task.result_raw = "<nmap_xml>...</nmap_xml>"
        db.commit()
        db.refresh(task)

        assert task.result_summary["hosts_found"] == 5
        assert task.result_raw == "<nmap_xml>...</nmap_xml>"

    def test_task_with_audit(self, db: Session, agent: Agent, user: User, audit: Audit):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            audit_id=audit.id,
            tool="ad_collector",
            parameters={"domain": "corp.local", "collect": ["users", "groups"]},
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.audit_id == audit.id

    def test_task_without_audit(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="nmap",
            parameters={"target": "10.0.0.0/24"},
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.audit_id is None

    def test_task_uuid_unique(self, db: Session, agent: Agent, user: User):
        fixed_uuid = str(uuid.uuid4())
        t1 = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="nmap",
            parameters={},
            task_uuid=fixed_uuid,
        )
        db.add(t1)
        db.commit()

        t2 = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="nmap",
            parameters={},
            task_uuid=fixed_uuid,
        )
        db.add(t2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_task_error_message(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            tool="oradad",
            parameters={"domain": "corp.local"},
        )
        db.add(task)
        db.commit()

        task.status = "failed"
        task.error_message = "ORADAD.exe not found"
        db.commit()
        db.refresh(task)

        assert task.status == "failed"
        assert task.error_message == "ORADAD.exe not found"


# ────────────────────────────────────────────────────────────────────────
# Relations
# ────────────────────────────────────────────────────────────────────────


class TestRelationships:
    def test_user_to_agents(self, db: Session, user: User):
        a1 = Agent(name="Agent-1", user_id=user.id)
        a2 = Agent(name="Agent-2", user_id=user.id)
        db.add_all([a1, a2])
        db.commit()
        db.refresh(user)

        assert len(user.agents) == 2
        names = {a.name for a in user.agents}
        assert names == {"Agent-1", "Agent-2"}

    def test_agent_to_owner(self, db: Session, agent: Agent, user: User):
        db.refresh(agent)
        assert agent.owner is not None
        assert agent.owner.id == user.id
        assert agent.owner.username == "tech_jean"

    def test_agent_to_tasks(self, db: Session, agent: Agent, user: User):
        t1 = AgentTask(
            agent_id=agent.id, owner_id=user.id, tool="nmap", parameters={}
        )
        t2 = AgentTask(
            agent_id=agent.id, owner_id=user.id, tool="oradad", parameters={}
        )
        db.add_all([t1, t2])
        db.commit()
        db.refresh(agent)

        assert len(agent.tasks) == 2
        tools = {t.tool for t in agent.tasks}
        assert tools == {"nmap", "oradad"}

    def test_task_to_agent(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id, owner_id=user.id, tool="nmap", parameters={}
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.agent is not None
        assert task.agent.name == "PC-Bureau-Jean"

    def test_task_to_owner(self, db: Session, agent: Agent, user: User):
        task = AgentTask(
            agent_id=agent.id, owner_id=user.id, tool="nmap", parameters={}
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.owner is not None
        assert task.owner.username == "tech_jean"

    def test_cascade_delete_agent_deletes_tasks(self, db: Session, agent: Agent, user: User):
        t1 = AgentTask(
            agent_id=agent.id, owner_id=user.id, tool="nmap", parameters={}
        )
        db.add(t1)
        db.commit()
        task_id = t1.id

        db.delete(agent)
        db.commit()

        assert db.get(AgentTask, task_id) is None

    def test_different_users_different_agents(self, db: Session, user: User, user2: User):
        a1 = Agent(name="Agent-Jean", user_id=user.id)
        a2 = Agent(name="Agent-Marie", user_id=user2.id)
        db.add_all([a1, a2])
        db.commit()

        jean_agents = db.query(Agent).filter(Agent.user_id == user.id).all()
        marie_agents = db.query(Agent).filter(Agent.user_id == user2.id).all()

        assert len(jean_agents) == 1
        assert jean_agents[0].name == "Agent-Jean"
        assert len(marie_agents) == 1
        assert marie_agents[0].name == "Agent-Marie"
