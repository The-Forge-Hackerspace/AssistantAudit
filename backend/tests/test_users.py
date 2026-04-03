"""
Tests CRUD pour les endpoints de gestion des utilisateurs (/api/v1/users/).
"""


class TestListUsers:
    def test_admin_can_list_users(self, client, admin_headers):
        response = client.get("/api/v1/users/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1  # au moins l'admin

    def test_auditeur_cannot_list_users(self, client, auditeur_headers):
        response = client.get("/api/v1/users/", headers=auditeur_headers)
        assert response.status_code == 403

    def test_lecteur_cannot_list_users(self, client, lecteur_headers):
        response = client.get("/api/v1/users/", headers=lecteur_headers)
        assert response.status_code == 403

    def test_unauthenticated_cannot_list_users(self, client):
        response = client.get("/api/v1/users/")
        assert response.status_code == 401


class TestCreateUser:
    def test_admin_can_create_user(self, client, admin_headers):
        payload = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "Password123!",
            "full_name": "New User",
            "role": "auditeur",
        }
        response = client.post("/api/v1/users/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "auditeur"
        assert data["is_active"] is True
        assert "password" not in data
        assert "password_hash" not in data

    def test_duplicate_username_returns_400(self, client, admin_headers):
        payload = {
            "username": "dupuser",
            "email": "dup1@test.com",
            "password": "Password123!",
            "full_name": "Dup User",
            "role": "lecteur",
        }
        response = client.post("/api/v1/users/", json=payload, headers=admin_headers)
        assert response.status_code == 201

        payload2 = {
            "username": "dupuser",
            "email": "dup2@test.com",
            "password": "Password123!",
            "full_name": "Dup User 2",
            "role": "lecteur",
        }
        response2 = client.post("/api/v1/users/", json=payload2, headers=admin_headers)
        assert response2.status_code == 400
        assert "nom d'utilisateur" in response2.json()["detail"].lower()

    def test_duplicate_email_returns_400(self, client, admin_headers):
        payload = {
            "username": "emailuser1",
            "email": "same@test.com",
            "password": "Password123!",
            "full_name": "Email User 1",
            "role": "lecteur",
        }
        response = client.post("/api/v1/users/", json=payload, headers=admin_headers)
        assert response.status_code == 201

        payload2 = {
            "username": "emailuser2",
            "email": "same@test.com",
            "password": "Password123!",
            "full_name": "Email User 2",
            "role": "lecteur",
        }
        response2 = client.post("/api/v1/users/", json=payload2, headers=admin_headers)
        assert response2.status_code == 400
        assert "email" in response2.json()["detail"].lower()

    def test_auditeur_cannot_create_user(self, client, auditeur_headers):
        payload = {
            "username": "blocked",
            "email": "blocked@test.com",
            "password": "Password123!",
            "full_name": "Blocked",
            "role": "lecteur",
        }
        response = client.post("/api/v1/users/", json=payload, headers=auditeur_headers)
        assert response.status_code == 403

    def test_short_password_returns_422(self, client, admin_headers):
        payload = {
            "username": "shortpw",
            "email": "shortpw@test.com",
            "password": "short",
            "full_name": "Short PW",
            "role": "lecteur",
        }
        response = client.post("/api/v1/users/", json=payload, headers=admin_headers)
        assert response.status_code == 422


class TestUpdateUser:
    def test_admin_can_update_user(self, client, admin_headers, auditeur_user):
        payload = {
            "full_name": "Updated Name",
            "role": "lecteur",
        }
        response = client.put(f"/api/v1/users/{auditeur_user.id}", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["role"] == "lecteur"

    def test_admin_can_change_user_password(self, client, admin_headers, lecteur_user):
        payload = {"password": "NewPassword123!"}
        response = client.put(f"/api/v1/users/{lecteur_user.id}", json=payload, headers=admin_headers)
        assert response.status_code == 200

    def test_update_nonexistent_user_returns_404(self, client, admin_headers):
        response = client.put("/api/v1/users/99999", json={"full_name": "Ghost"}, headers=admin_headers)
        assert response.status_code == 404

    def test_auditeur_cannot_update_user(self, client, auditeur_headers, lecteur_user):
        response = client.put(
            f"/api/v1/users/{lecteur_user.id}",
            json={"full_name": "Hacked"},
            headers=auditeur_headers,
        )
        assert response.status_code == 403


class TestDeleteUser:
    def test_admin_can_deactivate_user(self, client, admin_headers, lecteur_user):
        response = client.delete(f"/api/v1/users/{lecteur_user.id}", headers=admin_headers)
        assert response.status_code == 200
        assert "désactivé" in response.json()["message"]

    def test_admin_cannot_deactivate_self(self, client, admin_headers, admin_user):
        response = client.delete(f"/api/v1/users/{admin_user.id}", headers=admin_headers)
        assert response.status_code == 400
        assert "vous-même" in response.json()["detail"].lower()

    def test_delete_nonexistent_user_returns_404(self, client, admin_headers):
        response = client.delete("/api/v1/users/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_auditeur_cannot_delete_user(self, client, auditeur_headers, lecteur_user):
        response = client.delete(f"/api/v1/users/{lecteur_user.id}", headers=auditeur_headers)
        assert response.status_code == 403
