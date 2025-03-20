import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.core.exceptions import UserNotFoundError


def test_create_user(session):
    """Test creating a new user in database"""
    user = User(email="test@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert isinstance(user.created_at, datetime)


def test_get_user(session):
    """Test retrieving a user from database"""
    user = User(email="test@example.com")
    session.add(user)
    session.commit()

    db_user = session.get(User, user.id)
    assert db_user is not None
    assert db_user.email == "test@example.com"


def test_update_user(session):
    """Test updating a user in database"""
    user = User(email="old@example.com")
    session.add(user)
    session.commit()

    user.email = "new@example.com"
    session.commit()
    session.refresh(user)

    assert user.email == "new@example.com"


def test_delete_user(session):
    """Test deleting a user from database"""
    user = User(email="test@example.com")
    session.add(user)
    session.commit()

    session.delete(user)
    session.commit()

    deleted_user = session.get(User, user.id)
    assert deleted_user is None


def test_unique_email_constraint(session):
    """Test database unique constraint for email"""
    user1 = User(email="same@example.com")
    session.add(user1)
    session.commit()

    user2 = User(email="same@example.com")
    session.add(user2)

    with pytest.raises(IntegrityError):
        session.commit()
        session.rollback()


def test_get_user_by_email(session):
    """Test retrieving a user by email"""
    user = User(email="test@example.com")
    session.add(user)
    session.commit()

    db_user = session.query(User).filter(User.email == "test@example.com").first()
    assert db_user is not None
    assert db_user.id == user.id


def test_user_created_at_auto_set(session):
    """Test that created_at is automatically set"""
    before = datetime.now()
    user = User(email="test@example.com")
    session.add(user)
    session.commit()
    after = datetime.now()

    assert before <= user.created_at <= after


def test_bulk_user_creation(session):
    """Test creating multiple users at once"""
    users = [User(email=f"test{i}@example.com") for i in range(3)]
    session.add_all(users)
    session.commit()

    db_users = session.query(User).all()
    assert len(db_users) == 3


def test_case_insensitive_email_search(session):
    """Test that email search is case insensitive"""
    user = User(email="Test@Example.com")
    session.add(user)
    session.commit()

    db_user = session.query(User).filter(User.email.ilike("test@example.com")).first()
    assert db_user is not None


def test_update_nonexistent_user(session):
    """Test updating a user that doesn't exist"""
    with pytest.raises(UserNotFoundError) as exc:
        User.update(session, 999, email="test@example.com")
    assert str(exc.value) == "User with id 999 not found"
