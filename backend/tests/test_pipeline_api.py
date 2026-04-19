"""Tests endpoints API pipeline (TOS-13 / T005).

Couvre :
  - POST /pipelines : création + lancement background
  - GET /pipelines : liste paginée, scope owner
  - GET /pipelines/{id} : détail, isolation inter-utilisateur
  - Validation credentials, RBAC, 404 sur site/pipeline introuvable
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.collect_pipeline import CollectPipeline, PipelineStatus, PipelineStepStatus
from app.models.entreprise import Entreprise
from app.models.site import Site

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def _site(db_session: Session, auditeur_user):
    """Cree Entreprise + Site appartenant a auditeur_user."""
    ent = Entreprise(
        nom="Ent Pipeline Test",
        secteur_activite="IT",
        adresse="1 rue du Test",
        siret="99999999900010",
        owner_id=auditeur_user.id,
    )
    db_session.add(ent)
    db_session.flush()
    site = Site(
        nom="Site Pipeline Test",
        entreprise_id=ent.id,
        adresse="2 rue du Site",
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


@pytest.fixture()
def _agent(db_session: Session, auditeur_user):
    """Agent actif du auditeur_user autorisé à exécuter nmap."""
    agent = Agent(
        name="Agent Pipeline Test",
        user_id=auditeur_user.id,
        status="active",
        allowed_tools=["nmap"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture()
def _pipeline(db_session: Session, _site, _agent, auditeur_user):
    """Pipeline pre-existant en statut completed pour les tests GET."""
    p = CollectPipeline(
        site_id=_site.id,
        agent_id=_agent.id,
        target="10.0.0.0/24",
        created_by=auditeur_user.id,
        status=PipelineStatus.COMPLETED,
        scan_status=PipelineStepStatus.COMPLETED,
        equipments_status=PipelineStepStatus.COMPLETED,
        collects_status=PipelineStepStatus.COMPLETED,
        hosts_discovered=3,
        equipments_created=2,
        hosts_skipped=1,
        collects_total=2,
        collects_done=2,
        collects_failed=0,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


# ── POST /pipelines ─────────────────────────────────────────────────────────


class TestCreatePipeline:
    """Tests de creation et lancement du pipeline."""

    @patch("app.services.pipeline_service.execute_pipeline_background")
    def test_create_pipeline_returns_202(
        self, mock_exec, client, auditeur_headers, _site, _agent
    ):
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": _agent.id,
                "target": "192.168.1.0/24",
                "username": "root",
                "password": "secret",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "pending"
        assert data["target"] == "192.168.1.0/24"
        assert data["site_id"] == _site.id
        assert data["agent_id"] == _agent.id
        # L'orchestrateur est lance via SyncTaskRunner (conftest)
        mock_exec.assert_called_once()
        call_kwargs = mock_exec.call_args
        assert call_kwargs.kwargs["username"] == "root"
        assert call_kwargs.kwargs["password"] == "secret"

    @patch("app.services.pipeline_service.execute_pipeline_background")
    def test_create_pipeline_with_private_key(
        self, mock_exec, client, auditeur_headers, _site, _agent
    ):
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": _agent.id,
                "target": "10.0.0.1",
                "username": "deploy",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 202
        assert mock_exec.call_args.kwargs["private_key"] is not None

    def test_create_pipeline_missing_credentials_returns_422(
        self, client, auditeur_headers, _site, _agent
    ):
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": _agent.id,
                "target": "10.0.0.0/24",
                "username": "root",
                # ni password ni private_key
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 422

    def test_create_pipeline_unknown_site_returns_404(
        self, client, auditeur_headers, _agent
    ):
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": 999999,
                "agent_id": _agent.id,
                "target": "10.0.0.0/24",
                "username": "root",
                "password": "pass",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 404

    def test_create_pipeline_unknown_agent_returns_404(
        self, client, auditeur_headers, _site
    ):
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": 999999,
                "target": "10.0.0.0/24",
                "username": "root",
                "password": "pass",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 404

    def test_create_pipeline_inactive_agent_returns_404(
        self, client, auditeur_headers, _site, db_session, auditeur_user
    ):
        agent = Agent(
            name="Agent inactif",
            user_id=auditeur_user.id,
            status="pending",
            allowed_tools=["nmap"],
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": agent.id,
                "target": "10.0.0.0/24",
                "username": "root",
                "password": "pass",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 404
        assert "inactif" in resp.json()["detail"].lower()

    def test_create_pipeline_agent_without_nmap_returns_404(
        self, client, auditeur_headers, _site, db_session, auditeur_user
    ):
        agent = Agent(
            name="Agent sans nmap",
            user_id=auditeur_user.id,
            status="active",
            allowed_tools=["oradad"],
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": agent.id,
                "target": "10.0.0.0/24",
                "username": "root",
                "password": "pass",
            },
            headers=auditeur_headers,
        )
        assert resp.status_code == 404

    def test_create_pipeline_lecteur_forbidden(
        self, client, lecteur_headers, _site, _agent
    ):
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": _agent.id,
                "target": "10.0.0.0/24",
                "username": "root",
                "password": "pass",
            },
            headers=lecteur_headers,
        )
        assert resp.status_code == 403

    def test_create_pipeline_unauthenticated_returns_401(self, client, _site, _agent):
        resp = client.post(
            "/api/v1/pipelines",
            json={
                "site_id": _site.id,
                "agent_id": _agent.id,
                "target": "10.0.0.0/24",
                "username": "root",
                "password": "pass",
            },
        )
        assert resp.status_code == 401


# ── GET /pipelines/{id} ─────────────────────────────────────────────────────


class TestGetPipeline:
    def test_get_pipeline_owner(self, client, auditeur_headers, _pipeline):
        resp = client.get(
            f"/api/v1/pipelines/{_pipeline.id}",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == _pipeline.id
        assert data["hosts_discovered"] == 3
        assert data["collects_done"] == 2

    def test_get_pipeline_admin_sees_all(
        self, client, admin_headers, _pipeline
    ):
        resp = client.get(
            f"/api/v1/pipelines/{_pipeline.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_get_pipeline_other_user_returns_404(
        self, client, second_auditeur_headers, _pipeline
    ):
        resp = client.get(
            f"/api/v1/pipelines/{_pipeline.id}",
            headers=second_auditeur_headers,
        )
        assert resp.status_code == 404

    def test_get_pipeline_not_found(self, client, auditeur_headers):
        resp = client.get(
            "/api/v1/pipelines/999999",
            headers=auditeur_headers,
        )
        assert resp.status_code == 404


# ── GET /pipelines ──────────────────────────────────────────────────────────────


class TestListPipelines:
    def test_list_pipelines_owner(self, client, auditeur_headers, _pipeline):
        resp = client.get("/api/v1/pipelines", headers=auditeur_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        ids = [p["id"] for p in data["items"]]
        assert _pipeline.id in ids

    def test_list_pipelines_other_user_empty(
        self, client, second_auditeur_headers, _pipeline
    ):
        resp = client.get(
            "/api/v1/pipelines", headers=second_auditeur_headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_pipelines_filter_by_site(
        self, client, auditeur_headers, _pipeline
    ):
        resp = client.get(
            f"/api/v1/pipelines?site_id={_pipeline.site_id}",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_pipelines_admin_sees_all(
        self, client, admin_headers, _pipeline
    ):
        resp = client.get("/api/v1/pipelines", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ── Service helpers unitaires ─────────────────────────────────────────────────


class TestPipelineServiceHelpers:
    """Tests directs get_pipeline / list_pipelines (sans HTTP)."""

    def test_get_pipeline_returns_none_for_wrong_owner(
        self, db_session, _pipeline, second_auditeur_user
    ):
        from app.services.pipeline_service import get_pipeline

        result = get_pipeline(
            db_session, _pipeline.id, owner_id=second_auditeur_user.id
        )
        assert result is None

    def test_list_pipelines_scoped_by_owner(
        self, db_session, _pipeline, auditeur_user, second_auditeur_user
    ):
        from app.services.pipeline_service import list_pipelines

        items_owner, total_owner = list_pipelines(
            db_session, owner_id=auditeur_user.id
        )
        items_other, total_other = list_pipelines(
            db_session, owner_id=second_auditeur_user.id
        )
        assert total_owner >= 1
        assert total_other == 0
        assert all(p.created_by == auditeur_user.id for p in items_owner)

    def test_create_pipeline_unknown_site_raises(
        self, db_session, auditeur_user, _agent
    ):
        from app.services.pipeline_service import create_pending_pipeline

        with pytest.raises(ValueError, match="introuvable"):
            create_pending_pipeline(
                db_session,
                site_id=999999,
                agent_id=_agent.id,
                target="10.0.0.0/24",
                created_by=auditeur_user.id,
            )

    def test_create_pipeline_wrong_owner_raises(
        self, db_session, _site, _agent, second_auditeur_user
    ):
        from app.services.pipeline_service import create_pending_pipeline

        with pytest.raises(ValueError, match="introuvable"):
            create_pending_pipeline(
                db_session,
                site_id=_site.id,
                agent_id=_agent.id,
                target="10.0.0.0/24",
                created_by=second_auditeur_user.id,
            )

    def test_create_pipeline_unknown_agent_raises(
        self, db_session, _site, auditeur_user
    ):
        from app.services.pipeline_service import create_pending_pipeline

        with pytest.raises(ValueError, match="Agent.*introuvable"):
            create_pending_pipeline(
                db_session,
                site_id=_site.id,
                agent_id=999999,
                target="10.0.0.0/24",
                created_by=auditeur_user.id,
            )

    def test_create_pipeline_inactive_agent_raises(
        self, db_session, _site, auditeur_user
    ):
        from app.services.pipeline_service import create_pending_pipeline

        agent = Agent(
            name="Agent pending",
            user_id=auditeur_user.id,
            status="pending",
            allowed_tools=["nmap"],
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        with pytest.raises(ValueError, match="inactif"):
            create_pending_pipeline(
                db_session,
                site_id=_site.id,
                agent_id=agent.id,
                target="10.0.0.0/24",
                created_by=auditeur_user.id,
            )

    def test_create_pipeline_agent_without_nmap_raises(
        self, db_session, _site, auditeur_user
    ):
        from app.services.pipeline_service import create_pending_pipeline

        agent = Agent(
            name="Agent sans nmap",
            user_id=auditeur_user.id,
            status="active",
            allowed_tools=["oradad"],
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        with pytest.raises(ValueError, match="non autoris"):
            create_pending_pipeline(
                db_session,
                site_id=_site.id,
                agent_id=agent.id,
                target="10.0.0.0/24",
                created_by=auditeur_user.id,
            )
