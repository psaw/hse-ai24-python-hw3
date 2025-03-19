import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from tests.integration.test import TestTable

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def engine():
    """Create a test database engine"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine):
    """Create a test database session"""
    with Session(engine) as session:
        yield session
        session.rollback()


def test_create_test_table_record(db_session):
    """Test creating a record in test_table"""
    # Create a test record
    test_record = TestTable(name="test name")
    db_session.add(test_record)
    db_session.commit()

    # Query the record
    record = db_session.query(TestTable).filter_by(name="test name").first()

    # Assertions
    assert record is not None
    assert record.name == "test name"
    assert record.id is not None


def test_update_test_table_record(db_session):
    """Test updating a record in test_table"""
    # Create a test record
    test_record = TestTable(name="old name")
    db_session.add(test_record)
    db_session.commit()

    # Update the record
    test_record.name = "new name"
    db_session.commit()

    # Query the record
    record = db_session.query(TestTable).filter_by(id=test_record.id).first()

    # Assertions
    assert record.name == "new name"


def test_delete_test_table_record(db_session):
    """Test deleting a record from test_table"""
    # Create a test record
    test_record = TestTable(name="to be deleted")
    db_session.add(test_record)
    db_session.commit()

    # Store the ID
    record_id = test_record.id

    # Delete the record
    db_session.delete(test_record)
    db_session.commit()

    # Try to query the deleted record
    record = db_session.query(TestTable).filter_by(id=record_id).first()

    # Assertions
    assert record is None
