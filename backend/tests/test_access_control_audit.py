"""
Audit securite 4/8 : Controle d'acces — tests d'integration reels.

Verifie l'isolation inter-roles (admin/auditeur/lecteur) et inter-tenants
sur tous les endpoints critiques.
"""
import pytest
from app.core.security import create_access_token, hash_password, create_agent_token
from app.models import User
from app.models.audit import Audit
from app.models.entreprise import Entreprise
from app.models.agent import Agent


# ── Fixtures supplementaires ─────────────────────────────────────────


@pytest.fixture
def auditeur2_user(db_session):
    """Second auditeur pour tester l'isolation inter-tenants."""
    user = User(
        username="auditeur2_test",
        email="auditeur2@test.example.com",
        password_hash=hash_password("auditeur2_password_123"),
        full_name="Test Auditeur 2",
        role="auditeur",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auditeur2_headers(auditeur2_user):
    token = create_access_token(subject=auditeur2_user.id)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def entreprise(db_session, auditeur_user):
    e = Entreprise(nom="Entreprise Test", owner_id=auditeur_user.id)
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture
def audit(db_session, auditeur_user, entreprise):
    a = Audit(
        nom_projet="Audit Securite Test",
        entreprise_id=entreprise.id,
        owner_id=auditeur_user.id,
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def agent(db_session, auditeur_user):
    a = Agent(
        name="Agent Test",
        user_id=auditeur_user.id,
        allowed_tools=["nmap", "oradad"],
        status="active",
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


# ══════════════════════════════════════════════════════════════════════
# 1. AUDITS — Isolation par role
# ══════════════════════════════════════════════════════════════════════


class TestAuditAccess:

    def test_admin_sees_all_audits(self, client, admin_headers, audit):
        """Admin voit tous les audits, y compris ceux d'autres users."""
        r = client.get("/api/v1/audits", headers=admin_headers)
        assert r.status_code == 200
        # L'audit de auditeur_test est visible
        assert r.json()["total"] >= 1

    def test_lecteur_can_list_audits(self, client, lecteur_headers, audit):
        """Lecteur peut lister les audits (get_current_user) — voit uniquement les siens."""
        r = client.get("/api/v1/audits", headers=lecteur_headers)
        assert r.status_code == 200

    def test_lecteur_cannot_get_other_audit_detail(self, client, lecteur_headers, audit):
        """Lecteur ne voit pas l'audit d'un autre user (owner_id filtering)."""
        r = client.get(f"/api/v1/audits/{audit.id}", headers=lecteur_headers)
        assert r.status_code == 404

    def test_lecteur_cannot_create_audit(self, client, lecteur_headers, entreprise):
        """Lecteur ne peut pas creer d'audit (require_auditeur)."""
        r = client.post(
            "/api/v1/audits",
            json={"nom_projet": "Hack Audit", "entreprise_id": entreprise.id},
            headers=lecteur_headers,
        )
        assert r.status_code == 403

    def test_lecteur_cannot_update_audit(self, client, lecteur_headers, audit):
        """Lecteur ne peut pas modifier un audit."""
        r = client.put(
            f"/api/v1/audits/{audit.id}",
            json={"nom_projet": "Modified"},
            headers=lecteur_headers,
        )
        assert r.status_code == 403

    def test_auditeur_cannot_delete_audit(self, client, auditeur_headers, audit):
        """Auditeur ne peut pas supprimer un audit (admin only)."""
        r = client.delete(f"/api/v1/audits/{audit.id}", headers=auditeur_headers)
        assert r.status_code == 403

    def test_no_auth_rejected(self, client, audit):
        """Sans token, tout est rejete."""
        r = client.get("/api/v1/audits")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# 2. AUDITS — PAS d'isolation par owner (FINDING)
# ══════════════════════════════════════════════════════════════════════


class TestAuditOwnership:

    def test_audits_owner_filtering(self, client, auditeur_headers, auditeur2_headers, audit):
        """
        FIXED: GET /audits filtre par owner_id.
        auditeur2 ne voit PAS les audits de auditeur1.
        """
        r = client.get("/api/v1/audits", headers=auditeur2_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        audit_ids = [a["id"] for a in items]
        assert audit.id not in audit_ids, "audits should be filtered by owner_id"


# ══════════════════════════════════════════════════════════════════════
# 3. AGENTS — Isolation par owner
# ══════════════════════════════════════════════════════════════════════


class TestAgentAccess:

    def test_lecteur_cannot_create_agent(self, client, lecteur_headers):
        """Lecteur ne peut pas creer d'agent."""
        r = client.post(
            "/api/v1/agents/create",
            json={"name": "Evil Agent", "allowed_tools": ["nmap"]},
            headers=lecteur_headers,
        )
        assert r.status_code == 403

    def test_auditeur_sees_own_agents_only(
        self, client, auditeur_headers, auditeur2_headers, agent
    ):
        """Auditeur ne voit que ses propres agents."""
        # auditeur_test voit son agent
        r = client.get("/api/v1/agents/", headers=auditeur_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

        # auditeur2_test ne voit PAS les agents de auditeur_test
        r2 = client.get("/api/v1/agents/", headers=auditeur2_headers)
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    def test_admin_sees_all_agents(self, client, admin_headers, agent):
        """Admin voit tous les agents."""
        r = client.get("/api/v1/agents/", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_auditeur_cannot_revoke_other_agent(
        self, client, auditeur2_headers, agent
    ):
        """Auditeur ne peut pas revoquer l'agent d'un autre — retourne 404."""
        r = client.delete(
            f"/api/v1/agents/{agent.agent_uuid}", headers=auditeur2_headers
        )
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# 4. TASK DISPATCH — Triple verification
# ══════════════════════════════════════════════════════════════════════


class TestTaskDispatch:

    def test_dispatch_to_other_users_agent_returns_404(
        self, client, auditeur2_headers, agent
    ):
        """
        auditeur2 dispatch vers l'agent de auditeur1 → 404 (agent introuvable).
        Pas 403, pour ne pas reveler l'existence de l'agent.
        """
        r = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": agent.agent_uuid,
                "tool": "nmap",
                "parameters": {"target": "192.168.1.1"},
            },
            headers=auditeur2_headers,
        )
        assert r.status_code == 404

    def test_dispatch_tool_not_allowed_returns_403(
        self, client, auditeur_headers, agent
    ):
        """
        FINDING: dispatch avec un outil non autorise retourne 403.
        Ceci revele que l'agent existe.
        """
        r = client.post(
            "/api/v1/agents/tasks/dispatch",
            json={
                "agent_uuid": agent.agent_uuid,
                "tool": "evil_tool",
                "parameters": {},
            },
            headers=auditeur_headers,
        )
        # L'agent est bien au user, mais l'outil n'est pas dans allowed_tools
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════
# 5. USERS — Admin only
# ══════════════════════════════════════════════════════════════════════


class TestUserAccess:

    def test_lecteur_cannot_list_users(self, client, lecteur_headers):
        """Lecteur ne peut pas lister les utilisateurs."""
        r = client.get("/api/v1/users/", headers=lecteur_headers)
        assert r.status_code == 403

    def test_auditeur_cannot_list_users(self, client, auditeur_headers):
        """Auditeur ne peut pas lister les utilisateurs."""
        r = client.get("/api/v1/users/", headers=auditeur_headers)
        assert r.status_code == 403

    def test_auditeur_cannot_delete_user(self, client, auditeur_headers, lecteur_user):
        """Auditeur ne peut pas supprimer un utilisateur."""
        r = client.delete(
            f"/api/v1/users/{lecteur_user.id}", headers=auditeur_headers
        )
        assert r.status_code == 403

    def test_admin_can_list_users(self, client, admin_headers, auditeur_user):
        """Admin peut lister les utilisateurs."""
        r = client.get("/api/v1/users/", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1


# ══════════════════════════════════════════════════════════════════════
# 6. ORADAD CONFIGS — Auditeur only + isolation par owner
# ══════════════════════════════════════════════════════════════════════


class TestOradadAccess:

    def test_lecteur_cannot_create_config(self, client, lecteur_headers):
        """Lecteur ne peut pas creer de config ORADAD."""
        r = client.post(
            "/api/v1/oradad/configs",
            json={"name": "Evil Config"},
            headers=lecteur_headers,
        )
        assert r.status_code == 403

    def test_lecteur_cannot_list_configs(self, client, lecteur_headers):
        """Lecteur ne peut pas lister les configs ORADAD."""
        r = client.get("/api/v1/oradad/configs", headers=lecteur_headers)
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════
# 7. ENROLL — seul endpoint public
# ══════════════════════════════════════════════════════════════════════


class TestPublicEndpoints:

    def test_enroll_is_public(self, client):
        """POST /agents/enroll est accessible sans auth (retourne 400, pas 401)."""
        r = client.post(
            "/api/v1/agents/enroll",
            json={"enrollment_code": "FAKECODE", "device_name": "test-pc"},
        )
        # 400 = code invalide, mais pas 401 = pas d'auth requise
        assert r.status_code in (400, 422), f"Expected 400/422, got {r.status_code}"

    def test_health_is_public(self, client):
        """GET /health accessible sans auth."""
        r = client.get("/api/v1/health")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# 8. TOKEN TYPE ISOLATION
# ══════════════════════════════════════════════════════════════════════


class TestTokenTypeIsolation:

    def test_agent_token_rejected_on_user_route(self, client, agent):
        """Un token agent ne doit pas fonctionner sur une route user."""
        agent_token = create_agent_token(agent.agent_uuid, agent.user_id)
        headers = {"Authorization": f"Bearer {agent_token}"}
        r = client.get("/api/v1/audits", headers=headers)
        assert r.status_code == 401

    def test_user_token_rejected_on_agent_route(self, client, auditeur_headers, agent):
        """Un token user ne doit pas fonctionner sur une route agent (heartbeat)."""
        r = client.post(
            "/api/v1/agents/heartbeat",
            json={},
            headers=auditeur_headers,
        )
        assert r.status_code == 401
