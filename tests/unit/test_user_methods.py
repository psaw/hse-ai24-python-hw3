import pytest
from app.models.user import User
from app.core.exceptions import UserNotFoundError


def test_get_by_id_not_found(session):
    """Test get_by_id with nonexistent user"""
    with pytest.raises(UserNotFoundError) as exc:
        User.get_by_id(session, 999)
    assert str(exc.value) == "User with id 999 not found"


def test_get_by_id_success(session):
    """Test get_by_id with existing user"""
    user = User(email="test@example.com")
    session.add(user)
    session.commit()

    found_user = User.get_by_id(session, user.id)
    assert found_user.id == user.id
    assert found_user.email == user.email


def test_update_success(session):
    """Test successful user update"""
    user = User(email="old@example.com")
    session.add(user)
    session.commit()

    updated_user = User.update(session, user.id, email="new@example.com")
    assert updated_user.email == "new@example.com"


def test_update_not_found(session):
    """Test update with nonexistent user"""
    with pytest.raises(UserNotFoundError) as exc:
        User.update(session, 999, email="new@example.com")
    assert str(exc.value) == "User with id 999 not found"
