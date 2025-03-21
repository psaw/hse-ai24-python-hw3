import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.models import __init__  # This will initialize relationships
from app.models.link import Link
from app.schemas.link import LinkBase
from app.core.config import settings


def test_link_creation():
    """Test link creation with valid data"""
    link_data = {
        "original_url": "https://example.com",
        "short_code": "abc123",
        "custom_alias": "example",
        "is_public": True,
        "project_id": 1,
    }
    # Validate data using schema
    LinkBase(**link_data)
    # Create link model
    link = Link(**link_data)

    assert str(link.original_url) == "https://example.com"
    assert link.short_code == "abc123"
    assert link.custom_alias == "example"
    assert link.is_public is True
    assert link.project_id == 1


def test_link_created_at_default():
    """Test default created_at value"""
    link = Link(original_url="https://example.com", short_code="abc123")
    assert isinstance(link.created_at, datetime)


def test_link_visits_count_default():
    """Test default visits_count value"""
    link = Link(original_url="https://example.com", short_code="abc123")
    assert link.visits_count == 0


def test_link_is_public_default():
    """Test default is_public value"""
    link = Link(original_url="https://example.com", short_code="abc123")
    assert link.is_public is False


def test_public_link_expiry():
    """Test that public links get default expiry from settings"""
    link = Link(original_url="https://example.com", short_code="abc123", is_public=True)
    expected_expiry = datetime.now() + timedelta(
        days=settings.PUBLIC_PROJECT_LINK_EXPIRY_DAYS
    )
    assert link.expires_at is not None
    # Compare dates with a tolerance of 1 second
    assert abs((link.expires_at - expected_expiry).total_seconds()) < 1


@pytest.mark.parametrize(
    "url,short_code,custom_alias,is_public,project_id",
    [
        ("https://example.com", "abc123", None, False, None),
        ("https://test.com", "xyz789", "test", True, 1),
        ("https://demo.com", "def456", "demo", False, 2),
    ],
)
def test_valid_link_creation(url, short_code, custom_alias, is_public, project_id):
    """Test link creation with various valid data combinations"""
    link_data = {
        "original_url": url,
        "short_code": short_code,
        "custom_alias": custom_alias,
        "is_public": is_public,
        "project_id": project_id,
    }
    # Validate data using schema
    LinkBase(**link_data)
    # Create link model
    link = Link(**link_data)

    assert str(link.original_url) == url
    assert link.short_code == short_code
    assert link.custom_alias == custom_alias
    assert link.is_public == is_public
    assert link.project_id == project_id


@pytest.mark.parametrize(
    "invalid_data,expected_error",
    [
        (
            {"original_url": "not_a_url", "short_code": "abc123"},
            "Input should be a valid URL",
        ),
        (
            {"original_url": "https://example.com", "short_code": ""},
            "Short code cannot be empty",
        ),
        (
            {"original_url": "https://example.com", "short_code": "a" * 11},
            "Short code cannot be longer than 10 characters",
        ),
        (
            {
                "original_url": "https://example.com",
                "short_code": "abc123",
                "custom_alias": "a" * 51,
            },
            "Custom alias cannot be longer than 50 characters",
        ),
        (
            {
                "original_url": "https://example.com",
                "short_code": "abc123",
                "expires_at": datetime.now() - timedelta(days=1),
            },
            "Expiration date cannot be in the past",
        ),
        (
            {
                "original_url": "https://example.com",
                "short_code": "abc123",
                "project_id": 0,
            },
            "Project ID must be positive",
        ),
    ],
)
def test_invalid_link_creation(invalid_data, expected_error):
    """Test link creation with invalid data"""
    with pytest.raises(ValidationError) as exc_info:
        LinkBase(**invalid_data)

    assert expected_error in str(exc_info.value)


def test_link_expiration():
    """Test link expiration date handling"""
    future_date = datetime.now() + timedelta(days=7)
    link_data = {
        "original_url": "https://example.com",
        "short_code": "abc123",
        "expires_at": future_date,
    }
    # Validate data using schema
    LinkBase(**link_data)
    # Create link model
    link = Link(**link_data)

    assert link.expires_at == future_date


def test_link_last_used():
    """Test link last used date handling"""
    link_data = {"original_url": "https://example.com", "short_code": "abc123"}
    # Validate data using schema
    LinkBase(**link_data)
    # Create link model
    link = Link(**link_data)

    assert link.last_used_at is None
