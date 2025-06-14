# tests/conftest.py - FIXED VERSION
import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import your app components
from app.database import get_db, Base
from main import app
from app import models, auth, schemas
from app.auth import get_password_hash, create_access_token

# Test database setup with in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # Set to True for SQL debugging
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden database dependency"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": get_password_hash("testpass123"),
        "is_active": True,
        "is_artist": False
    }
    user = models.User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_artist(db_session):
    """Create a test artist user"""
    artist_data = {
        "username": "testartist",
        "email": "artist@example.com",
        "hashed_password": get_password_hash("artistpass123"),
        "is_active": True,
        "is_artist": True
    }
    artist = models.User(**artist_data)
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    return artist


@pytest.fixture
def inactive_user(db_session):
    """Create an inactive user"""
    user_data = {
        "username": "inactiveuser",
        "email": "inactive@example.com",
        "hashed_password": get_password_hash("pass123"),
        "is_active": False,
        "is_artist": False
    }
    user = models.User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create auth headers for test user"""
    access_token = create_access_token(
        data={"sub": test_user.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def artist_auth_headers(test_artist):
    """Create auth headers for test artist"""
    access_token = create_access_token(
        data={"sub": test_artist.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_genre(db_session):
    """Create a test genre"""
    genre = models.Genre(name="Rock", description="Rock music")
    db_session.add(genre)
    db_session.commit()
    db_session.refresh(genre)
    return genre


@pytest.fixture
def test_song(db_session, test_artist, test_genre):
    """Create a test song"""
    song = models.Song(
        title="Test Song",
        file_path="/test/path.mp3",
        duration=180,
        creator_id=test_artist.id,
        like_count=0
    )
    db_session.add(song)
    db_session.commit()

    # Add genre relationship
    song.genres.append(test_genre)
    db_session.commit()
    db_session.refresh(song)
    return song


@pytest.fixture
def test_album(db_session, test_artist):
    """Create a test album with proper creator relationship"""
    album = models.Album(
        title="Test Album",
        release_date=datetime.now(),
        creator_id=test_artist.id,
        like_count=0
    )
    db_session.add(album)
    db_session.commit()
    db_session.refresh(album)
    return album


@pytest.fixture
def test_playlist(db_session, test_user):
    """Create a test playlist"""
    playlist = models.Playlist(
        name="Test Playlist",
        description="Test Description",
        owner_id=test_user.id
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)
    return playlist


# Additional helper fixtures for file testing
@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        # Write some fake audio data
        tmp.write(b'ID3\x03\x00\x00\x00' + b'fake_audio_data' * 100)
        tmp.flush()
        yield tmp.name

    # Cleanup
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        # Write some fake image data (JPEG header)
        tmp.write(b'\xff\xd8\xff\xe0' + b'fake_image_data' * 100)
        tmp.flush()
        yield tmp.name

    # Cleanup
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock upload directory
@pytest.fixture(autouse=True)
def mock_upload_dir():
    """Create temporary upload directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch the upload directory in the songs module
        import app.routers.songs as songs_module
        original_upload_dir = songs_module.UPLOAD_DIR
        songs_module.UPLOAD_DIR = temp_dir

        # Create subdirectories
        os.makedirs(os.path.join(temp_dir, "songs"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "covers"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "song_covers"), exist_ok=True)

        yield temp_dir

        # Restore original
        songs_module.UPLOAD_DIR = original_upload_dir