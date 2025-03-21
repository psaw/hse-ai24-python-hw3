import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import __init__  # This will initialize relationships
from app.models.project import Project
from app.schemas.project import ProjectBase


def test_project_creation():
    """Test project creation with valid data"""
    project_data = {"name": "Test Project", "default_lifetime_days": 7, "owner_id": 1}
    # Validate data using schema
    ProjectBase(**project_data)
    # Create project model
    project = Project(**project_data)

    assert project.name == "Test Project"
    assert project.default_lifetime_days == 7
    assert project.owner_id == 1


def test_project_created_at_default():
    """Test default created_at value"""
    project = Project(name="Test Project", default_lifetime_days=30, owner_id=1)
    assert isinstance(project.created_at, datetime)


@pytest.mark.parametrize(
    "name,default_lifetime_days,owner_id",
    [
        ("Valid Project", 30, 1),
        ("Another Project", 7, 2),
        ("Third Project", 365, 3),
    ],
)
def test_valid_project_creation(name, default_lifetime_days, owner_id):
    """Test project creation with various valid data combinations"""
    project_data = {
        "name": name,
        "default_lifetime_days": default_lifetime_days,
        "owner_id": owner_id,
    }
    # Validate data using schema
    ProjectBase(**project_data)
    # Create project model
    project = Project(**project_data)

    assert project.name == name
    assert project.default_lifetime_days == default_lifetime_days
    assert project.owner_id == owner_id


@pytest.mark.parametrize(
    "invalid_data,expected_error",
    [
        (
            {"name": "", "default_lifetime_days": 7, "owner_id": 1},
            "Name cannot be empty",
        ),
        (
            {"name": "Test", "default_lifetime_days": 0, "owner_id": 1},
            "Default lifetime days must be positive",
        ),
        (
            {"name": "Test", "default_lifetime_days": -1, "owner_id": 1},
            "Default lifetime days must be positive",
        ),
        (
            {"name": "Test", "default_lifetime_days": 7, "owner_id": 0},
            "Owner ID must be positive",
        ),
        (
            {"name": "Test", "default_lifetime_days": 7, "owner_id": -1},
            "Owner ID must be positive",
        ),
    ],
)
def test_invalid_project_creation(invalid_data, expected_error):
    """Test project creation with invalid data"""
    with pytest.raises(ValidationError) as exc_info:
        ProjectBase(**invalid_data)

    assert expected_error in str(exc_info.value)
