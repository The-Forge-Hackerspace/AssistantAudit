"""Tests TOS-16 — dispatch des collectes SSH/WinRM vers un agent on-prem.

Couvre :
  - dispatch_collect_to_agent : creation AgentTask, lien CollectResult,
    parametres SSH/WinRM, refus si outil non autorise ou agent etranger.
  - hydrate_collect_from_agent_result : remplissage des champs sur succes
    et sur echec (renvoi d'une erreur agent ou d'un error_message WebSocket).
  - POST /api/v1/tools/collect : validation agent_uuid + dispatch effectif.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.collect_result import CollectResult, CollectStatus
from app.models.entreprise import Entreprise
from app.models.equipement import EquipementServeur
from app.models.site import Site
from app.models.user import User
from app.services import collect_service

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def equipement(db_session: Session, auditeur_user: User) -> EquipementServeur:
    """Serveur dans un site du auditeur_user (chaine ownership complete)."""
    ent = Entreprise(
        nom="Ent Collect Dispatch",
        secteur_activite="IT",
        adresse="1 rue Collect",
        siret="12345678900011",
        owner_id=auditeur_user.id,
    )
    db_session.add(ent)
    db_session.flush()
    site = Site(nom="Site Collect", entreprise_id=ent.id, adresse="2 rue Site")
    db_session.add(site)
    db_session.flush()
    eq = EquipementServeur(
        site_id=site.id,
        type_equipement="serveur",
        ip_address="10.20.30.40",
        hostname="srv-test",
        mac_address="aa:bb:cc:dd:ee:ff",
    )
    db_session.add(eq)
    db_session.commit()
    db_session.refresh(eq)
    return eq


@pytest.fixture()
def agent(db_session: Session, auditeur_user: User) -> Agent:
    """Agent actif de auditeur_user autorise a executer ssh/winrm-collect."""
    a = Agent(
        name="Collect-Agent",
        user_id=auditeur_user.id,
        status="active",
        allowed_tools=["ssh-collect", "winrm-collect"],
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture()
def agent_no_collect(db_session: Session, auditeur_user: User) -> Agent:
    """Agent actif mais sans l'outil ssh-collect dans allowed_tools."""
    a = Agent(
        name="Agent-Restreint",
        user_id=auditeur_user.id,
        status="active",
        allowed_tools=["nmap"],
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture()
def foreign_agent(db_session: Session, second_auditeur_user: User) -> Agent:
    """Agent actif appartenant a un autre technicien."""
    a = Agent(
        name="Agent-Autre-Tech",
        user_id=second_auditeur_user.id,
        status="active",
        allowed_tools=["ssh-collect", "winrm-collect"],
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


def _pending_collect(
    db: Session, equipement_id: int, method: str = "ssh"
) -> CollectResult:
    return collect_service.create_pending_collect(
        db=db,
        equipement_id=equipement_id,
        method=method,
        target_host="10.20.30.40",
        target_port=22 if method == "ssh" else 5985,
        username="admin",
        device_profile="linux_server",
    )


# ── dispatch_collect_to_agent ───────────────────────────────────────────


class TestDispatchCollectToAgent:
    def test_ssh_dispatch_creates_task_and_links_collect(
        self, db_session, auditeur_user, agent, equipement
    ):
        collect = _pending_collect(db_session, equipement.id, method="ssh")

        task = collect_service.dispatch_collect_to_agent(
            db=db_session,
            collect_id=collect.id,
            agent_uuid=agent.agent_uuid,
            current_user_id=auditeur_user.id,
            password="s3cret",
        )
        db_session.commit()
        db_session.refresh(collect)

        assert task.tool == "ssh-collect"
        assert task.agent_id == agent.id
        assert task.owner_id == auditeur_user.id
        assert task.status == "pending"
        assert task.parameters["host"] == "10.20.30.40"
        assert task.parameters["port"] == 22
        assert task.parameters["username"] == "admin"
        assert task.parameters["device_profile"] == "linux_server"
        assert task.parameters["password"] == "s3cret"
        assert collect.agent_task_id == task.id
        assert collect.status == CollectStatus.RUNNING

    def test_ssh_dispatch_forwards_private_key(
        self, db_session, auditeur_user, agent, equipement
    ):
        collect = _pending_collect(db_session, equipement.id, method="ssh")

        task = collect_service.dispatch_collect_to_agent(
            db=db_session,
            collect_id=collect.id,
            agent_uuid=agent.agent_uuid,
            current_user_id=auditeur_user.id,
            private_key="-----BEGIN KEY-----\nabc\n-----END KEY-----",
            passphrase="pass",
        )

        assert task.parameters["private_key"].startswith("-----BEGIN")
        assert task.parameters["passphrase"] == "pass"
        assert "password" not in task.parameters

    def test_winrm_dispatch_uses_winrm_tool_and_transport(
        self, db_session, auditeur_user, agent, equipement
    ):
        collect = _pending_collect(db_session, equipement.id, method="winrm")

        task = collect_service.dispatch_collect_to_agent(
            db=db_session,
            collect_id=collect.id,
            agent_uuid=agent.agent_uuid,
            current_user_id=auditeur_user.id,
            password="WinPass!",
            use_ssl=True,
            transport="kerberos",
        )

        assert task.tool == "winrm-collect"
        assert task.parameters["use_ssl"] is True
        assert task.parameters["transport"] == "kerberos"
        assert task.parameters["password"] == "WinPass!"

    def test_dispatch_raises_value_error_when_collect_missing(
        self, db_session, auditeur_user, agent
    ):
        with pytest.raises(ValueError, match="introuvable"):
            collect_service.dispatch_collect_to_agent(
                db=db_session,
                collect_id=999_999,
                agent_uuid=agent.agent_uuid,
                current_user_id=auditeur_user.id,
            )

    def test_dispatch_rejects_foreign_agent(
        self, db_session, auditeur_user, foreign_agent, equipement
    ):
        collect = _pending_collect(db_session, equipement.id, method="ssh")

        with pytest.raises(HTTPException) as exc:
            collect_service.dispatch_collect_to_agent(
                db=db_session,
                collect_id=collect.id,
                agent_uuid=foreign_agent.agent_uuid,
                current_user_id=auditeur_user.id,
            )
        assert exc.value.status_code == 404

    def test_dispatch_rejects_when_tool_not_allowed(
        self, db_session, auditeur_user, agent_no_collect, equipement
    ):
        collect = _pending_collect(db_session, equipement.id, method="ssh")

        with pytest.raises(HTTPException) as exc:
            collect_service.dispatch_collect_to_agent(
                db=db_session,
                collect_id=collect.id,
                agent_uuid=agent_no_collect.agent_uuid,
                current_user_id=auditeur_user.id,
            )
        assert exc.value.status_code == 403


# ── hydrate_collect_from_agent_result ───────────────────────────────────


class TestHydrateCollectFromAgentResult:
    def test_success_hydrates_all_fields(self, db_session, equipement):
        collect = _pending_collect(db_session, equipement.id, method="ssh")
        payload = {
            "hostname": "srv-prod-01",
            "os_info": {"distro": "Debian", "version_id": "12", "kernel": "6.1.0"},
            "network": {"interfaces": [{"name": "eth0"}]},
            "users": {"local": []},
            "services": {"running": ["sshd"]},
            "security": {"firewall": "active"},
            "storage": {"disks": []},
            "updates": {"pending": 0},
        }

        collect_service.hydrate_collect_from_agent_result(
            db_session, collect, payload, None
        )
        db_session.flush()

        assert collect.status == CollectStatus.SUCCESS
        assert collect.hostname_collected == "srv-prod-01"
        assert collect.os_info["distro"] == "Debian"
        assert collect.services["running"] == ["sshd"]
        assert collect.completed_at is not None
        assert collect.findings is not None
        assert collect.summary is not None
        assert collect.duration_seconds is not None
        assert collect.duration_seconds >= 0

    def test_success_propagates_hostname_to_equipement(
        self, db_session, equipement
    ):
        equipement.hostname = None
        db_session.commit()
        collect = _pending_collect(db_session, equipement.id, method="ssh")
        payload = {
            "hostname": "new-host",
            "os_info": {"distro": "Ubuntu", "version_id": "22.04", "kernel": "5.15"},
            "network": {},
            "users": {},
            "services": {},
            "security": {},
            "storage": {},
            "updates": {},
        }

        collect_service.hydrate_collect_from_agent_result(
            db_session, collect, payload, None
        )
        db_session.flush()
        db_session.refresh(equipement)

        assert equipement.hostname == "new-host"
        assert equipement.os_detected == "Ubuntu"

    def test_error_message_marks_failed(self, db_session, equipement):
        collect = _pending_collect(db_session, equipement.id, method="ssh")

        collect_service.hydrate_collect_from_agent_result(
            db_session, collect, None, "connexion refusee"
        )

        assert collect.status == CollectStatus.FAILED
        assert collect.error_message == "connexion refusee"
        assert collect.completed_at is not None

    def test_agent_success_false_marks_failed(self, db_session, equipement):
        collect = _pending_collect(db_session, equipement.id, method="ssh")

        collect_service.hydrate_collect_from_agent_result(
            db_session,
            collect,
            {"success": False, "error": "timeout ssh"},
            None,
        )

        assert collect.status == CollectStatus.FAILED
        assert collect.error_message == "timeout ssh"

    def test_agent_error_only_marks_failed(self, db_session, equipement):
        """Payload {"error": "..."} sans flag success doit etre traite comme echec."""
        collect = _pending_collect(db_session, equipement.id, method="ssh")

        collect_service.hydrate_collect_from_agent_result(
            db_session,
            collect,
            {"error": "auth refused"},
            None,
        )

        assert collect.status == CollectStatus.FAILED
        assert collect.error_message == "auth refused"


# ── POST /api/v1/tools/collect ──────────────────────────────────────────


class TestCollectEndpoint:
    def test_post_collect_dispatches_and_returns_running(
        self, client, auditeur_headers, agent, equipement
    ):
        resp = client.post(
            "/api/v1/tools/collect",
            headers=auditeur_headers,
            json={
                "equipement_id": equipement.id,
                "agent_uuid": agent.agent_uuid,
                "method": "ssh",
                "target_host": "10.20.30.40",
                "target_port": 22,
                "username": "admin",
                "password": "secret",
                "device_profile": "linux_server",
            },
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "running"
        assert body["method"] == "ssh"

    def test_post_collect_without_agent_uuid_is_rejected(
        self, client, auditeur_headers, equipement
    ):
        resp = client.post(
            "/api/v1/tools/collect",
            headers=auditeur_headers,
            json={
                "equipement_id": equipement.id,
                "method": "ssh",
                "target_host": "10.20.30.40",
                "target_port": 22,
                "username": "admin",
            },
        )
        assert resp.status_code == 422

    def test_post_collect_rejects_agent_without_tool(
        self, client, auditeur_headers, agent_no_collect, equipement
    ):
        resp = client.post(
            "/api/v1/tools/collect",
            headers=auditeur_headers,
            json={
                "equipement_id": equipement.id,
                "agent_uuid": agent_no_collect.agent_uuid,
                "method": "ssh",
                "target_host": "10.20.30.40",
                "target_port": 22,
                "username": "admin",
            },
        )
        assert resp.status_code == 403
