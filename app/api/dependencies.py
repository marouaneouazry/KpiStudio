try:
    from app.auth.dependencies import get_current_user, get_current_user_optional, get_token_from_request
    from app.auth.models import User
except ModuleNotFoundError:
    from auth.dependencies import get_current_user, get_current_user_optional, get_token_from_request
    from auth.models import User

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_token_from_request",
    "User",
]
