class BaseError(Exception):
    """Base error class"""

    pass


class UserError(BaseError):
    """Base class for user-related errors"""

    pass


class ProjectError(BaseError):
    """Base class for project-related errors"""

    pass


class LinkError(BaseError):
    """Base class for link-related errors"""

    pass


class UserNotFoundError(UserError):
    """Raised when user is not found"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User with id {user_id} not found")


class ProjectNotFoundError(ProjectError):
    """Raised when project is not found"""

    def __init__(self, project_id: int):
        self.project_id = project_id
        super().__init__(f"Project with id {project_id} not found")


class LinkNotFoundError(LinkError):
    """Raised when link is not found"""

    def __init__(self, link_id: int):
        self.link_id = link_id
        super().__init__(f"Link with id {link_id} not found")


class ProjectAccessError(ProjectError):
    """Raised when user doesn't have access to project"""

    def __init__(self, user_id: int, project_id: int):
        self.user_id = user_id
        self.project_id = project_id
        super().__init__(f"User {user_id} doesn't have access to project {project_id}")


class ProjectAdminError(ProjectError):
    """Raised when user is not admin of project"""

    def __init__(self, user_id: int, project_id: int):
        self.user_id = user_id
        self.project_id = project_id
        super().__init__(f"User {user_id} is not admin of project {project_id}")


class LinkExpiredError(LinkError):
    """Raised when link has expired"""

    def __init__(self, link_id: int):
        self.link_id = link_id
        super().__init__(f"Link {link_id} has expired")
