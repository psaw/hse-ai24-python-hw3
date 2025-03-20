import sys
from pathlib import Path
from datetime import datetime
import pytest
from sqlmodel import Session, create_engine, SQLModel

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.append(src_path)

# Используем SQLite в памяти для тестов
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(name="session")
def session_fixture():
    """Create a new database session for a test"""
    engine = create_engine(TEST_DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def sample_user_data():
    """Sample user data for tests"""
    return {"email": "test@example.com", "created_at": datetime.now()}


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
