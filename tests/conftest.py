import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from app.database import Base, get_db
from app.auth import get_current_user, get_current_active_user
from app.models import User

# Test database URL - using SQLite for simplicity
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    # Drop all tables first, then create them
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client for making requests."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async test client for async operations."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user():
    """Mock user for authentication tests."""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        is_active=True,
        is_artist=False
    )


@pytest.fixture
def authenticated_client(client, mock_user):
    """Client with mocked authentication."""

    def mock_get_current_user():
        return mock_user

    def mock_get_current_active_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

    yield client

    # Cleanup
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]


@pytest.fixture
def sample_song_data():
    """Sample song data for testing."""
    return {
        "title": "Test Song",
        "artist": "Test Artist",
        "duration": 180,
        "genre": "Rock"
    }


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "testpassword123",
        "full_name": "New User"
    }