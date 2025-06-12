import sys

import pytest
import tempfile
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base

# Global test configuration
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment and cleanup"""
    # Create temp directory for test uploads
    temp_dir = tempfile.mkdtemp()

    # Patch the uploads directory
    with patch.dict(os.environ, {"UPLOADS_DIR": temp_dir}):
        yield

    # Cleanup temp directory
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_file_upload():
    """Mock file upload operations"""
    with patch('os.makedirs'), \
            patch('builtins.open'), \
            patch('os.path.exists', return_value=True):
        yield


# Database markers for different test types
pytest_markers = [
    "unit: marks tests as unit tests (fast, no external dependencies)",
    "integration: marks tests as integration tests (slower, with database)",
    "auth: marks tests that require authentication",
    "artist: marks tests that require artist privileges",
    "file_upload: marks tests that involve file uploads"
]


# Add custom pytest options
def pytest_addoption(parser):
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    for marker in pytest_markers:
        config.addinivalue_line("markers", marker)


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        # Don't skip slow tests if --run-slow is given
        return
    skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)