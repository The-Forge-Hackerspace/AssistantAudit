"""Tests d'isolation du ContextVar request_id (TOS-82)."""

from app.core.logging_config import _request_id


def test_two_sequential_requests_have_distinct_request_ids(client):
    """Header X-Request-ID doit différer entre deux requêtes successives."""
    r1 = client.get("/api/v1/auth/me")
    r2 = client.get("/api/v1/auth/me")
    rid1 = r1.headers.get("X-Request-ID")
    rid2 = r2.headers.get("X-Request-ID")
    assert rid1
    assert rid2
    assert rid1 != rid2


def test_request_id_contextvar_is_reset_between_requests(client):
    """Le ContextVar `_request_id` ne doit PAS conserver la valeur de la requête précédente.

    Le test exécute deux requêtes et capture les request_id observés (via header
    `X-Request-ID`), puis vérifie qu'après chaque requête le ContextVar a été
    reset (différent de la valeur active pendant la requête). Sans le `reset(token)`
    en finally, le ContextVar conserverait l'ID de la dernière requête.
    """
    r1 = client.get("/api/v1/auth/me")
    rid1 = r1.headers.get("X-Request-ID")
    # Le ContextVar courant ne doit PAS être égal à rid1 (sinon = fuite).
    assert _request_id.get() != rid1

    r2 = client.get("/api/v1/auth/me")
    rid2 = r2.headers.get("X-Request-ID")
    assert _request_id.get() != rid2
    # Et bien sûr les deux IDs diffèrent.
    assert rid1 != rid2
