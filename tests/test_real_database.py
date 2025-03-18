import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.test import TestTable

# Use real SQLite database
DATABASE_URL = "sqlite:///app.db"

@pytest.fixture
def db_session():
    """Create a database session with real database"""
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        yield session
        # Rollback any changes after test
        session.rollback()

def test_create_and_read_record(db_session):
    """Test creating and reading a record in real database"""
    # Create a test record
    test_record = TestTable(name="Test Record")
    db_session.add(test_record)
    db_session.commit()
    
    created_id = test_record.id
    
    # Query the record
    record = db_session.query(TestTable).filter_by(id=created_id).first()
    
    # Print record details for verification
    print(f"\nCreated record: id={record.id}, name={record.name}")
    
    # Assertions
    assert record is not None
    assert record.name == "Test Record"
    
    # Cleanup - delete the test record
    db_session.delete(record)
    db_session.commit()

def test_list_all_records(db_session):
    """Test listing all records in test_table"""
    # Query all records
    records = db_session.query(TestTable).all()
    
    # Print all records
    print("\nAll records in test_table:")
    for record in records:
        print(f"id={record.id}, name={record.name}") 