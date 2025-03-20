import pytest
import time
from sqlmodel import Session, create_engine, SQLModel
from app.models.user import User


@pytest.mark.performance
def test_bulk_insert_performance():
    """Test performance of bulk user insertion"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    start_time = time.time()
    with Session(engine) as session:
        users = [User(email=f"user{i}@example.com") for i in range(1000)]
        session.add_all(users)
        session.commit()
    end_time = time.time()

    assert end_time - start_time < 1.0  # должно выполняться менее чем за 1 секунду
