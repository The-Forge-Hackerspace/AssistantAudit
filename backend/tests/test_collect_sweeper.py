"""Tests TOS-16 — sweeper de collectes orphelines.

Verifie que :
- une CollectResult `running` plus ancienne que le timeout passe FAILED,
- une CollectResult recente n'est pas touchee,
- une CollectResult deja terminee (success/failed) est ignoree,
- duration_seconds, completed_at et error_message sont renseignes,
- le owner est notifie via ws_manager.send_to_user quand un AgentTask est lie.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core import collect_sweeper
from app.models.agent import Agent
from app.models.agent_task import AgentTask
from app.models.collect_result import CollectMethod, CollectResult, CollectStatus
from app.models.entreprise import Entreprise
from app.models.equipement import EquipementServeur
from app.models.site import Site
from app.models.user import User
from tests.ws_helpers import FakeSessionLocal


@pytest.fixture()
def equipement(db_session: Session, auditeur_user: User) -> EquipementServeur:
    ent = Entreprise(
        nom="Ent Collect Sweeper",
        secteur_activite="IT",
        adresse="1 rue Sweep",
        siret="12345678900099",
        owner_id=auditeur_user.id,
    )
    db_session.add(ent)
    db_session.flush()
    site = Site(nom="Site Sweep", entreprise_id=ent.id, adresse="2 rue Site")
    db_session.add(site)
    db_session.flush()
    eq = EquipementServeur(
        site_id=site.id,
        type_equipement="serveur",
        ip_address="10.99.0.1",
        hostname="srv-sweep",
    )
    db_session.add(eq)
    db_session.commit()
    db_session.refresh(eq)
    return eq


@pytest.fixture()
def agent(db_session: Session, auditeur_user: User) -> Agent:
    a = Agent(
        name="Sweeper-Agent",
        user_id=auditeur_user.id,
        status="active",
        allowed_tools=["ssh-collect", "winrm-collect"],
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def patch_sweeper_session(db_session):
    fake = FakeSessionLocal(db_session)
    with patch("app.core.collect_sweeper.SessionLocal", fake):
        yield


def _make_collect(
    db: Session,
    equipement_id: int,
    *,
    status: CollectStatus,
    age_seconds: int,
    agent_task_id: int | None = None,
) -> CollectResult:
    """Cree une collecte avec un created_at force a now - age_seconds."""
    created_at = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    collect = CollectResult(
        equipement_id=equipement_id,
        method=CollectMethod.SSH,
        target_host="10.99.0.1",
        target_port=22,
        username="root",
        status=status,
        created_at=created_at,
        agent_task_id=agent_task_id,
    )
    db.add(collect)
    db.commit()
    db.refresh(collect)
    return collect


def _make_agent_task(db: Session, agent: Agent, owner: User) -> AgentTask:
    task = AgentTask(
        agent_id=agent.id,
        owner_id=owner.id,
        tool="ssh-collect",
        parameters={"host": "10.99.0.1"},
        status="dispatched",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


class TestCollectSweeper:
    def test_stale_running_collect_marked_failed(
        self, db_session, equipement, patch_sweeper_session
    ):
        """Collecte running plus ancienne que le timeout -> FAILED."""
        collect = _make_collect(
            db_session, equipement.id, status=CollectStatus.RUNNING, age_seconds=20 * 60
        )

        asyncio.run(collect_sweeper._sweep_once())

        db_session.expire_all()
        reloaded = db_session.get(CollectResult, collect.id)
        assert reloaded.status == CollectStatus.FAILED
        assert reloaded.error_message == "Timeout de la collecte agent"
        assert reloaded.completed_at is not None
        assert reloaded.duration_seconds is not None
        assert reloaded.duration_seconds >= 20 * 60

    def test_recent_running_collect_not_touched(
        self, db_session, equipement, patch_sweeper_session
    ):
        """Collecte running recente -> reste RUNNING."""
        collect = _make_collect(
            db_session, equipement.id, status=CollectStatus.RUNNING, age_seconds=60
        )

        asyncio.run(collect_sweeper._sweep_once())

        db_session.expire_all()
        assert db_session.get(CollectResult, collect.id).status == CollectStatus.RUNNING

    def test_already_finished_collect_ignored(
        self, db_session, equipement, patch_sweeper_session
    ):
        """Une collecte deja success/failed n'est jamais retraitee."""
        old_success = _make_collect(
            db_session, equipement.id, status=CollectStatus.SUCCESS, age_seconds=24 * 3600
        )
        old_failed = _make_collect(
            db_session, equipement.id, status=CollectStatus.FAILED, age_seconds=24 * 3600
        )

        asyncio.run(collect_sweeper._sweep_once())

        db_session.expire_all()
        assert db_session.get(CollectResult, old_success.id).status == CollectStatus.SUCCESS
        assert db_session.get(CollectResult, old_failed.id).status == CollectStatus.FAILED

    def test_owner_notified_when_agent_task_linked(
        self, db_session, equipement, agent, auditeur_user, patch_sweeper_session, monkeypatch
    ):
        """Owner du AgentTask lie -> ws_manager.send_to_user est appele."""
        task = _make_agent_task(db_session, agent, auditeur_user)
        _make_collect(
            db_session,
            equipement.id,
            status=CollectStatus.RUNNING,
            age_seconds=30 * 60,
            agent_task_id=task.id,
        )

        sent: list[tuple[int, str, dict]] = []

        async def fake_send(user_id, event_type, payload):
            sent.append((user_id, event_type, payload))

        monkeypatch.setattr(collect_sweeper.ws_manager, "send_to_user", fake_send)

        asyncio.run(collect_sweeper._sweep_once())

        assert len(sent) == 1
        owner_id, event_type, payload = sent[0]
        assert owner_id == auditeur_user.id
        assert event_type == "collect_status"
        assert payload["status"] == "failed"
