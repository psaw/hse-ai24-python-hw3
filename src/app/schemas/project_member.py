from pydantic import BaseModel, Field, validator


class ProjectMemberBase(BaseModel):
    """Base project member schema"""

    user_id: int = Field(..., description="User ID")
    project_id: int = Field(..., description="Project ID")
    is_admin: bool = Field(default=False, description="Whether the member is an admin")

    @validator("user_id")
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError("User ID must be positive")
        return v

    @validator("project_id")
    def validate_project_id(cls, v):
        if v <= 0:
            raise ValueError("Project ID must be positive")
        return v
