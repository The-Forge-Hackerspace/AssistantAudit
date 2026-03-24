# BACKEND TEST SUITE

Pytest-based integration and unit tests for the FastAPI application.

## STRUCTURE

```text
backend/tests/
├── conftest.py               # Shared fixtures (DB, TestClient, Auth)
├── factories.py              # SQLModel/SQLAlchemy data factories
├── test_api.py               # Core REST endpoint tests
├── test_monkey365_*.py       # 7 files covering Monkey365 integration
└── test_{service}.py         # Specific service/logic tests (metrics, scoring)
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add API Test | `test_api.py` | Use `client` + `admin_token` fixtures |
| Add Tool Test | `test_monkey365_*.py`| Follow existing executor/auth patterns |
| Modify Fixtures | `conftest.py` | In-memory SQLite + Dep overrides |
| Generate Data | `factories.py` | Use `UserFactory` or `create_full_assessment_scenario` |

## CONVENTIONS

- **Style**: Use plain functions and standard `assert`. No classes.
- **Fixtures**: Request `client` for API calls; it uses a `StaticPool` SQLite DB.
- **Auth**: Use `admin_token`, `auditeur_token`, or `lecteur_token` for headers.
- **Isolation**: Each test runs in a transaction. `autouse` fixtures handle cleanup.
- **Data**: Avoid manual DB inserts. Use `factories.py` for consistent state.
- **Mocking**: Minimize mocks. Prefer dependency overrides in `conftest.py`.

## HOW TO ADD A TEST

1. Create `tests/test_{feature}.py`.
2. Import needed factories: `from .factories import EntrepriseFactory`.
3. Define test function: `def test_feature_access(client, admin_token):`.
4. Create data: `org = EntrepriseFactory(db=session)`.
5. Execute: `response = client.get("/api/v1/...", headers=admin_token)`.
6. Verify: `assert response.status_code == 200`.

## RUNNING

Run from `backend/`: `pytest -q`
