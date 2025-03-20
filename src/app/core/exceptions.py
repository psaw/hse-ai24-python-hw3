class UserError(Exception):
    """Base exception for user-related errors"""

    pass


class UserNotFoundError(UserError):
    """Raised when user is not found"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User with id {user_id} not found")
