import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse


def test_user_creation():
    """Test user creation with valid data"""
    user = User(email="test@example.com", created_at=datetime.now())

    assert user.email == "test@example.com"
    assert isinstance(user.created_at, datetime)
    assert user.id is None  # ID will be set by database



def test_user_update_validation():
    """Test user update validation with Pydantic"""
    # Valid update
    update_data = UserUpdate(email="new@example.com")
    assert update_data.email == "new@example.com"

    # Valid empty update (all fields optional)
    update_data = UserUpdate()
    assert update_data.email is None

    # Invalid email
    with pytest.raises(ValidationError):
        UserUpdate(email="invalid-email")


def test_user_created_at_default():
    """Test default created_at value"""
    user = User(email="test@example.com")
    assert isinstance(user.created_at, datetime)


def test_user_response_schema():
    """Test UserResponse schema"""
    user = User(id=1, email="test@example.com", created_at=datetime.now())
    response = UserResponse.model_validate(user)

    assert response.id == 1
    assert response.email == user.email
    assert response.created_at == user.created_at


def test_user_create_schema_strip_whitespace():
    """Test that UserCreate schema strips whitespace from email"""
    user_data = UserCreate(email=" test@example.com ")
    assert user_data.email == "test@example.com"


def test_user_base_schema_lowercase_email():
    """Test that email is converted to lowercase"""
    user_data = UserCreate(email="TEST@EXAMPLE.COM")
    assert user_data.email == "test@example.com"


def test_user_update_partial():
    """Test partial update with UserUpdate schema"""
    # Empty update should be valid
    update_data = UserUpdate()
    assert update_data.model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize(
    "email",
    [
        "test@example.com",
        "user.name+tag@domain.com",
        "very.common@example.com",
        "disposable.style.email.with+symbol@example.com",
    ],
)
def test_valid_email_formats(email):
    """Test various valid email formats"""
    user = UserCreate(email=email)
    assert user.email == email.lower()


@pytest.mark.parametrize(
    "invalid_email,description",
    [
        ("invalid-email", "Invalid format"),
        ("", "Empty string"),
        (123, "Non-string value"),
        (None, "Missing email"),
        ("a" * 65 + "@example.com", "Too long local part (>64 chars)"),
    ],
)
def test_invalid_user_email_validation(invalid_email, description):
    """Test user email validation rejects invalid formats"""
    with pytest.raises(ValidationError):
        if invalid_email is None:
            UserCreate()
        else:
            UserCreate(email=invalid_email)