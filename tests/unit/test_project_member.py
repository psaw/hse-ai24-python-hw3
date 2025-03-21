import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import __init__  # This will initialize relationships
from app.models.project import ProjectMember
from app.schemas.project_member import ProjectMemberBase


def test_project_member_creation():
    """Test project member creation with valid data"""
    member_data = {"user_id": 1, "project_id": 1, "is_admin": False}
    # Validate data using schema
    ProjectMemberBase(**member_data)
    # Create project member model
    member = ProjectMember(**member_data)

    assert member.user_id == 1
    assert member.project_id == 1
    assert member.is_admin is False


def test_project_member_joined_at_default():
    """Test default joined_at value"""
    member = ProjectMember(user_id=1, project_id=1)
    assert isinstance(member.joined_at, datetime)


def test_project_member_is_admin_default():
    """Test default is_admin value"""
    member = ProjectMember(user_id=1, project_id=1)
    assert member.is_admin is False


@pytest.mark.parametrize(
    "user_id,project_id,is_admin",
    [
        (1, 1, False),
        (2, 1, True),
        (3, 2, False),
    ],
)
def test_valid_project_member_creation(user_id, project_id, is_admin):
    """Test project member creation with various valid data combinations"""
    member_data = {"user_id": user_id, "project_id": project_id, "is_admin": is_admin}
    # Validate data using schema
    ProjectMemberBase(**member_data)
    # Create project member model
    member = ProjectMember(**member_data)

    assert member.user_id == user_id
    assert member.project_id == project_id
    assert member.is_admin == is_admin


@pytest.mark.parametrize(
    "invalid_data,expected_error",
    [
        (
            {"user_id": 0, "project_id": 1, "is_admin": False},
            "User ID must be positive",
        ),
        (
            {"user_id": -1, "project_id": 1, "is_admin": False},
            "User ID must be positive",
        ),
        (
            {"user_id": 1, "project_id": 0, "is_admin": False},
            "Project ID must be positive",
        ),
        (
            {"user_id": 1, "project_id": -1, "is_admin": False},
            "Project ID must be positive",
        ),
    ],
)
def test_invalid_project_member_creation(invalid_data, expected_error):
    """Test project member creation with invalid data"""
    with pytest.raises(ValidationError) as exc_info:
        ProjectMemberBase(**invalid_data)

    assert expected_error in str(exc_info.value)
