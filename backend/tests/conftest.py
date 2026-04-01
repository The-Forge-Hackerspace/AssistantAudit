"""
Pytest fixtures configuration for AssistantAudit backend tests.
Provides database, client, authentication, and factory fixtures.
"""

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Importé depuis app
from app.core.database import Base
from app.core.security import create_access_token, hash_password
from app.models import User

# ────────────────────────────────────────────────────────────────────────
# Database & Session Fixtures
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def db_engine():
    """Create a temporary SQLite database for each test"""
    # Use in-memory SQLite for speed
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Teardown
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a clean database session for each test"""
    TestSessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = TestSessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture(scope="function")
def app(db_session):
    """Create FastAPI application with test database - lazy loaded"""
    # Import here to avoid loading at conftest import time
    from app.core.database import get_db
    from app.main import create_app
    
    # Create app
    app = create_app()
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: db_session
    
    yield app
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(db_session):
    """Provide FastAPI TestClient - lazy loads app"""
    # Import here to avoid loading at conftest import time
    from app.core.database import get_db
    from app.core.task_runner import SyncTaskRunner, set_task_runner
    from app.main import create_app

    # Use synchronous task runner in tests so background tasks
    # complete before assertions run.
    set_task_runner(SyncTaskRunner())

    # Create app
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    # Return test client
    test_client = TestClient(app)

    yield test_client

    # Cleanup
    app.dependency_overrides.clear()
    set_task_runner(SyncTaskRunner())


# ────────────────────────────────────────────────────────────────────────
# Authentication Fixtures
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an admin user"""
    user = User(
        username="admin_test",
        email="admin@test.example.com",
        password_hash=hash_password("AdminPass123!"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auditeur_user(db_session: Session) -> User:
    """Create an auditeur user"""
    user = User(
        username="auditeur_test",
        email="auditeur@test.example.com",
        password_hash=hash_password("AuditeurPass1!"),
        full_name="Test Auditeur",
        role="auditeur",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def lecteur_user(db_session: Session) -> User:
    """Create a lecteur user"""
    user = User(
        username="lecteur_test",
        email="lecteur@test.example.com",
        password_hash=hash_password("LecteurPass1!"),
        full_name="Test Lecteur",
        role="lecteur",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    """Generate valid JWT headers for admin user"""
    token = create_access_token(subject=admin_user.id)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def auditeur_headers(auditeur_user: User) -> dict:
    """Generate valid JWT headers for auditeur user"""
    token = create_access_token(subject=auditeur_user.id)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def lecteur_headers(lecteur_user: User) -> dict:
    """Generate valid JWT headers for lecteur user"""
    token = create_access_token(subject=lecteur_user.id)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def second_auditeur_user(db_session: Session) -> User:
    """Create a second auditeur user for isolation tests"""
    user = User(
        username="auditeur2_test",
        email="auditeur2@test.example.com",
        password_hash=hash_password("Auditeur2Pass1!"),
        full_name="Test Auditeur 2",
        role="auditeur",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_auditeur_headers(second_auditeur_user: User) -> dict:
    """Generate valid JWT headers for second auditeur user"""
    token = create_access_token(subject=second_auditeur_user.id)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def invalid_token_headers() -> dict:
    """Generate invalid JWT headers"""
    return {
        "Authorization": "Bearer invalid.token.here",
        "Content-Type": "application/json",
    }


# ────────────────────────────────────────────────────────────────────────
# Test Data Factories
# ────────────────────────────────────────────────────────────────────────
# Note: Factories are defined in factories.py to avoid circular imports


@pytest.fixture
def entreprise_data() -> dict:
    """Base data for creating an Entreprise"""
    return {
        "nom": "Test Company",
        "secteur": "IT Services",
        "adresse": "123 Test Street",
        "code_postal": "75001",
        "ville": "Paris",
        "pays": "France",
    }


# ────────────────────────────────────────────────────────────────────────
# Cleanup & Teardown
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def cleanup_after_test(db_session: Session):
    """Cleanup after each test"""
    yield
    # All test data is automatically rolled back with in-memory SQLite fixture


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Reset les rate limiters entre chaque test pour eviter les 429 parasites."""
    yield
    from app.core.rate_limit import enroll_rate_limiter, login_rate_limiter
    login_rate_limiter.reset_all()
    enroll_rate_limiter.reset_all()
