"""
Tests de base pour l'API AssistantAudit.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import create_all_tables, drop_all_tables, SessionLocal
from app.core.security import hash_password
from app.models.user import User


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Setup : crée les tables et un user de test"""
    create_all_tables()
    db = SessionLocal()
    existing = db.query(User).filter(User.username == "testadmin").first()
    if not existing:
        user = User(
            username="testadmin",
            email="test@test.com",
            password_hash=hash_password("TestPass@2026"),
            full_name="Test Admin",
            role="admin",
        )
        db.add(user)
        db.commit()
    db.close()
    yield
    # Teardown si nécessaire


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Obtient un token JWT pour les tests authentifiés"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin", "password": "TestPass@2026"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Health ---

def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# --- Auth ---

def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin", "password": "TestPass@2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_success_with_email(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@test.com", "password": "TestPass@2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_fail(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_get_me(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"


# --- Entreprises ---

def test_create_entreprise(client, auth_headers):
    response = client.post(
        "/api/v1/entreprises",
        json={
            "nom": "Entreprise Test",
            "adresse": "1 rue du Test",
            "secteur_activite": "IT",
            "contacts": [
                {"nom": "Jean Dupont", "email": "jean@test.com", "is_main_contact": True}
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "Entreprise Test"
    assert len(data["contacts"]) == 1


def test_list_entreprises(client, auth_headers):
    response = client.get("/api/v1/entreprises", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


# --- Frameworks ---

def test_list_frameworks(client, auth_headers):
    response = client.get("/api/v1/frameworks", headers=auth_headers)
    assert response.status_code == 200
