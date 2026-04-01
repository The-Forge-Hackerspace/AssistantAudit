"""
Tests pour l'upload d'artifacts agent et la reponse d'enrollment enrichie.
"""
import io
from unittest.mock import patch

import pytest

from app.core.security import create_access_token, create_agent_token, hash_password
from app.models import User
from app.models.agent import Agent
from app.models.agent_task import AgentTask

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def owner(db_session):
    user = User(
        username="artifact_owner",
        email="artifact@test.com",
        password_hash=hash_password("pass123"),
        role="auditeur",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    user = User(
        username="other_user",
        email="other@test.com",
        password_hash=hash_password("pass123"),
        role="auditeur",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def agent(db_session, owner):
    a = Agent(
        name="Test Agent",
        user_id=owner.id,
        allowed_tools=["nmap", "oradad"],
        status="active",
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def other_agent(db_session, other_user):
    a = Agent(
        name="Other Agent",
        user_id=other_user.id,
        allowed_tools=["nmap"],
        status="active",
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def completed_task(db_session, agent, owner):
    t = AgentTask(
        agent_id=agent.id,
        owner_id=owner.id,
        tool="nmap",
        parameters={"target": "192.168.1.0/24"},
        status="completed",
        progress=100,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def running_task(db_session, agent, owner):
    t = AgentTask(
        agent_id=agent.id,
        owner_id=owner.id,
        tool="oradad",
        parameters={},
        status="running",
        progress=50,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def cancelled_task(db_session, agent, owner):
    t = AgentTask(
        agent_id=agent.id,
        owner_id=owner.id,
        tool="nmap",
        parameters={},
        status="cancelled",
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def agent_headers(agent):
    token = create_agent_token(agent.agent_uuid, agent.user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_agent_headers(other_agent):
    token = create_agent_token(other_agent.agent_uuid, other_agent.user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner_headers(owner):
    token = create_access_token(subject=owner.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_headers(other_user):
    token = create_access_token(subject=other_user.id)
    return {"Authorization": f"Bearer {token}"}


def _make_file(content: bytes = b"test content", filename: str = "result.xml"):
    return {"file": (filename, io.BytesIO(content), "application/octet-stream")}


# ══════════════════════════════════════════════════════════════════════
# ARTIFACT UPLOAD
# ══════════════════════════════════════════════════════════════════════


class TestArtifactUpload:

    def test_upload_artifact_success(self, client, agent_headers, completed_task, tmp_path):
        """Agent uploade un artifact sur une tache completed → 201."""
        with patch("app.services.agent_service.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)
            mock_settings.CA_CERT_PATH = str(tmp_path / "nonexistent.pem")
            r = client.post(
                f"/api/v1/agents/tasks/{completed_task.task_uuid}/artifacts",
                files=_make_file(b"<xml>nmap output</xml>", "scan_result.xml"),
                headers=agent_headers,
            )
        assert r.status_code == 201
        data = r.json()
        assert data["filename"] == "scan_result.xml"
        assert data["size"] == len(b"<xml>nmap output</xml>")
        assert "file_id" in data

    def test_upload_artifact_running_task(self, client, agent_headers, running_task, tmp_path):
        """Agent uploade un artifact sur une tache running → 201 (autorise)."""
        with patch("app.services.agent_service.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)
            mock_settings.CA_CERT_PATH = str(tmp_path / "nonexistent.pem")
            r = client.post(
                f"/api/v1/agents/tasks/{running_task.task_uuid}/artifacts",
                files=_make_file(),
                headers=agent_headers,
            )
        assert r.status_code == 201

    def test_upload_with_user_token_rejected(self, client, owner_headers, completed_task):
        """Un token user ne doit pas fonctionner sur un endpoint agent."""
        r = client.post(
            f"/api/v1/agents/tasks/{completed_task.task_uuid}/artifacts",
            files=_make_file(),
            headers=owner_headers,
        )
        assert r.status_code == 401

    def test_upload_other_agents_task_404(self, client, other_agent_headers, completed_task):
        """Agent ne peut pas uploader sur la tache d'un autre agent → 404."""
        r = client.post(
            f"/api/v1/agents/tasks/{completed_task.task_uuid}/artifacts",
            files=_make_file(),
            headers=other_agent_headers,
        )
        assert r.status_code == 404

    def test_upload_cancelled_task_400(self, client, agent_headers, cancelled_task, tmp_path):
        """Upload sur une tache annulee → 400."""
        with patch("app.services.agent_service.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)
            r = client.post(
                f"/api/v1/agents/tasks/{cancelled_task.task_uuid}/artifacts",
                files=_make_file(),
                headers=agent_headers,
            )
        assert r.status_code == 400

    def test_upload_too_large_413(self, client, agent_headers, completed_task, tmp_path):
        """Fichier > 100MB → 413."""
        with patch("app.api.v1.agents.MAX_ARTIFACT_SIZE", 1024):  # 1KB limit for test
            with patch("app.services.agent_service.settings") as mock_settings:
                mock_settings.DATA_DIR = str(tmp_path)
                r = client.post(
                    f"/api/v1/agents/tasks/{completed_task.task_uuid}/artifacts",
                    files=_make_file(b"x" * 2048, "big_file.bin"),
                    headers=agent_headers,
                )
        assert r.status_code == 413


# ══════════════════════════════════════════════════════════════════════
# ARTIFACT LISTING
# ══════════════════════════════════════════════════════════════════════


class TestArtifactList:

    def test_list_artifacts_owner(self, client, agent_headers, owner_headers, completed_task, tmp_path):
        """Owner peut lister les artifacts de sa tache."""
        # Upload d'abord
        with patch("app.services.agent_service.settings") as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)
            mock_settings.CA_CERT_PATH = str(tmp_path / "nonexistent.pem")
            client.post(
                f"/api/v1/agents/tasks/{completed_task.task_uuid}/artifacts",
                files=_make_file(b"content1", "file1.xml"),
                headers=agent_headers,
            )
        # Lister
        r = client.get(
            f"/api/v1/agents/tasks/{completed_task.task_uuid}/artifacts",
            headers=owner_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["original_filename"] == "file1.xml"
        assert "download_url" in data[0]

    def test_list_artifacts_other_user_404(self, client, other_user_headers, completed_task):
        """Un autre user ne voit pas les artifacts → 404."""
        r = client.get(
            f"/api/v1/agents/tasks/{completed_task.task_uuid}/artifacts",
            headers=other_user_headers,
        )
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# ENRICHED ENROLLMENT
# ══════════════════════════════════════════════════════════════════════


class TestEnrichedEnrollment:

    def _create_pending_agent(self, db_session, owner):
        from app.core.security import create_enrollment_token
        code, code_hash, expiration = create_enrollment_token()
        a = Agent(
            name="Enrolling Agent",
            user_id=owner.id,
            allowed_tools=["nmap", "oradad"],
            enrollment_token_hash=code_hash,
            enrollment_token_expires=expiration,
            status="pending",
        )
        db_session.add(a)
        db_session.commit()
        db_session.refresh(a)
        return a, code

    def test_enroll_response_has_allowed_tools(self, client, db_session, owner):
        """Enrollment retourne allowed_tools."""
        _, code = self._create_pending_agent(db_session, owner)
        r = client.post("/api/v1/agents/enroll", json={"enrollment_code": code})
        assert r.status_code == 200
        data = r.json()
        assert "allowed_tools" in data
        assert data["allowed_tools"] == ["nmap", "oradad"]

    def test_enroll_response_has_agent_name(self, client, db_session, owner):
        """Enrollment retourne agent_name."""
        _, code = self._create_pending_agent(db_session, owner)
        r = client.post("/api/v1/agents/enroll", json={"enrollment_code": code})
        assert r.status_code == 200
        data = r.json()
        assert data["agent_name"] == "Enrolling Agent"

    def test_enroll_response_has_ca_cert_pem(self, client, db_session, owner, tmp_path):
        """Enrollment retourne ca_cert_pem quand le fichier CA existe."""
        # Creer un faux CA cert
        ca_path = tmp_path / "ca.pem"
        ca_path.write_text("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----\n")

        _, code = self._create_pending_agent(db_session, owner)
        with patch("app.services.agent_service.settings") as mock_settings:
            mock_settings.CA_CERT_PATH = str(ca_path)
            r = client.post("/api/v1/agents/enroll", json={"enrollment_code": code})
        assert r.status_code == 200
        data = r.json()
        assert "BEGIN CERTIFICATE" in data["ca_cert_pem"]

    def test_enroll_response_ca_cert_empty_when_no_file(self, client, db_session, owner, tmp_path):
        """Enrollment retourne ca_cert_pem vide si le fichier n'existe pas."""
        _, code = self._create_pending_agent(db_session, owner)
        with patch("app.services.agent_service.settings") as mock_settings:
            mock_settings.CA_CERT_PATH = str(tmp_path / "nonexistent.pem")
            r = client.post("/api/v1/agents/enroll", json={"enrollment_code": code})
        assert r.status_code == 200
        data = r.json()
        assert data["ca_cert_pem"] == ""
