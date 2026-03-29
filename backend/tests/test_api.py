"""
Tests de base pour l'API AssistantAudit.
Utilise les fixtures de conftest.py (DB in-memory, isolation par test).
"""
import pytest


# --- Health ---

def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# --- Auth ---

def test_login_success(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin_test", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_success_with_email(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.example.com", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_fail(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin_test", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_get_me(client, admin_headers, admin_user):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin_test"
    assert data["role"] == "admin"


# --- Entreprises ---

def test_create_entreprise(client, admin_headers):
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
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "Entreprise Test"
    assert len(data["contacts"]) == 1


def test_list_entreprises(client, admin_headers):
    # Creer une entreprise d'abord (DB in-memory vide)
    client.post(
        "/api/v1/entreprises",
        json={"nom": "Liste Test", "adresse": "1 rue", "secteur_activite": "IT"},
        headers=admin_headers,
    )
    response = client.get("/api/v1/entreprises", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


# --- Frameworks ---

def test_list_frameworks(client, admin_headers):
    response = client.get("/api/v1/frameworks", headers=admin_headers)
    assert response.status_code == 200
