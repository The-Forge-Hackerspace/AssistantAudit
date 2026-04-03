"""
Tests sécurité — DomainEntryResponse ne doit jamais exposer le password.

Vérifie que GET /oradad/configs retourne les domaines sans champ password,
et que POST/PUT stockent correctement le password en DB.
"""


class TestDomainPasswordNotExposed:
    def test_get_config_no_password_in_response(
        self,
        client,
        db_session,
        auditeur_headers,
    ):
        """GET une config ORADAD → explicit_domains ne contient pas de champ password."""
        # Créer une config avec un domaine qui a un password
        r = client.post(
            "/api/v1/oradad/configs",
            json={
                "name": "Config Password Test",
                "explicit_domains": [
                    {
                        "server": "10.0.0.1",
                        "port": 389,
                        "domain_name": "test.local",
                        "username": "auditeur",
                        "user_domain": "TEST",
                        "password": "SuperSecret123!",
                    }
                ],
            },
            headers=auditeur_headers,
        )
        assert r.status_code == 201
        config_id = r.json()["id"]

        # Vérifier que la réponse du POST ne contient pas de password
        domains = r.json()["explicit_domains"]
        assert domains is not None
        assert len(domains) == 1
        assert "password" not in domains[0]
        assert domains[0]["server"] == "10.0.0.1"
        assert domains[0]["username"] == "auditeur"

        # Vérifier aussi via GET (liste)
        r = client.get("/api/v1/oradad/configs", headers=auditeur_headers)
        assert r.status_code == 200
        configs = [c for c in r.json() if c["id"] == config_id]
        assert len(configs) == 1
        domains = configs[0]["explicit_domains"]
        assert len(domains) == 1
        assert "password" not in domains[0]

    def test_password_stored_correctly_in_db(
        self,
        client,
        db_session,
        auditeur_headers,
    ):
        """POST une config avec password → le password est stocké en DB."""
        from app.models.oradad_config import OradadConfig

        r = client.post(
            "/api/v1/oradad/configs",
            json={
                "name": "Config Storage Test",
                "explicit_domains": [
                    {
                        "server": "10.0.0.2",
                        "port": 636,
                        "domain_name": "prod.local",
                        "username": "admin",
                        "user_domain": "PROD",
                        "password": "RealPassword456!",
                    }
                ],
            },
            headers=auditeur_headers,
        )
        assert r.status_code == 201
        config_id = r.json()["id"]

        # Vérifier en DB que le password est bien stocké
        config = db_session.get(OradadConfig, config_id)
        assert config is not None
        domains = config.get_domains_list()
        assert len(domains) == 1
        assert domains[0]["password"] == "RealPassword456!"

    def test_list_configs_no_password(
        self,
        client,
        db_session,
        auditeur_headers,
    ):
        """GET /configs (liste) → aucun password dans les domaines."""
        client.post(
            "/api/v1/oradad/configs",
            json={
                "name": "Config List Test",
                "explicit_domains": [
                    {
                        "server": "10.0.0.3",
                        "port": 389,
                        "domain_name": "list.local",
                        "username": "user",
                        "user_domain": "LIST",
                        "password": "HiddenPass!",
                    }
                ],
            },
            headers=auditeur_headers,
        )

        r = client.get("/api/v1/oradad/configs", headers=auditeur_headers)
        assert r.status_code == 200
        for config in r.json():
            if config.get("explicit_domains"):
                for domain in config["explicit_domains"]:
                    assert "password" not in domain
