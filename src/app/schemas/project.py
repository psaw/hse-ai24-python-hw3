from pydantic import BaseModel, Field, validator


class ProjectBase(BaseModel):
    """Base project schema"""

    name: str = Field(..., description="Project name")
    default_lifetime_days: int = Field(
        ..., description="Default lifetime for links in days"
    )
    owner_id: int = Field(..., description="Project owner ID")

    @validator("name")
    def validate_name(cls, v):
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @validator("default_lifetime_days")
    def validate_lifetime_days(cls, v):
        if v <= 0:
            raise ValueError("Default lifetime days must be positive")
        return v

    @validator("owner_id")
    def validate_owner_id(cls, v):
        if v <= 0:
            raise ValueError("Owner ID must be positive")
        return v
