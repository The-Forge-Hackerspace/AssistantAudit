"""
Tests RBAC — Entreprise.owner_id direct ownership.

Vérifie que les entreprises sont visibles dès la création (sans audit),
que l'isolation fonctionne par owner_id, et que l'admin voit tout.
"""


class TestEntrepriseOwnerIsolation:
    def test_new_entreprise_visible_without_audit(
        self,
        client,
        db_session,
        auditeur_headers,
    ):
        """Une entreprise créée est visible dans la liste sans audit lié."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Ent Visible Sans Audit"},
            headers=auditeur_headers,
        )
        assert r.status_code == 201
        ent_id = r.json()["id"]
        assert r.json()["owner_id"] is not None

        r = client.get("/api/v1/entreprises", headers=auditeur_headers)
        assert r.status_code == 200
        ids = [e["id"] for e in r.json()["items"]]
        assert ent_id in ids

    def test_other_user_cannot_see_entreprise_in_list(
        self,
        client,
        db_session,
        auditeur_headers,
        second_auditeur_headers,
    ):
        """Auditeur B ne voit pas les entreprises d'auditeur A."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Ent A Only"},
            headers=auditeur_headers,
        )
        assert r.status_code == 201
        ent_id = r.json()["id"]

        r = client.get("/api/v1/entreprises", headers=second_auditeur_headers)
        ids = [e["id"] for e in r.json()["items"]]
        assert ent_id not in ids

    def test_other_user_get_returns_404(
        self,
        client,
        db_session,
        auditeur_headers,
        second_auditeur_headers,
    ):
        """Auditeur B ne peut pas GET une entreprise d'auditeur A → 404."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Ent Get Cross"},
            headers=auditeur_headers,
        )
        ent_id = r.json()["id"]

        r = client.get(
            f"/api/v1/entreprises/{ent_id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_other_user_update_returns_404(
        self,
        client,
        db_session,
        auditeur_headers,
        second_auditeur_headers,
    ):
        """Auditeur B ne peut pas mettre à jour une entreprise d'auditeur A → 404."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Ent Update Cross"},
            headers=auditeur_headers,
        )
        ent_id = r.json()["id"]

        r = client.put(
            f"/api/v1/entreprises/{ent_id}",
            json={"adresse": "hack"},
            headers=second_auditeur_headers,
        )
        assert r.status_code == 404

    def test_admin_sees_all_entreprises(
        self,
        client,
        db_session,
        auditeur_headers,
        admin_headers,
    ):
        """L'admin voit les entreprises de tous les utilisateurs."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Ent Admin Sees"},
            headers=auditeur_headers,
        )
        ent_id = r.json()["id"]

        r = client.get("/api/v1/entreprises", headers=admin_headers)
        ids = [e["id"] for e in r.json()["items"]]
        assert ent_id in ids

    def test_admin_can_get_any_entreprise(
        self,
        client,
        db_session,
        auditeur_headers,
        admin_headers,
    ):
        """L'admin peut GET n'importe quelle entreprise."""
        r = client.post(
            "/api/v1/entreprises",
            json={"nom": "Ent Admin Get"},
            headers=auditeur_headers,
        )
        ent_id = r.json()["id"]

        r = client.get(
            f"/api/v1/entreprises/{ent_id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
