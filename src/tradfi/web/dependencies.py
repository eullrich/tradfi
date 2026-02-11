"""Authentication dependencies for the web frontend."""

from fastapi import Request
from fastapi.responses import RedirectResponse

from tradfi.utils.cache import validate_session_token


class RequiresLoginException(Exception):
    """Raised when a route requires authentication but no valid session exists."""

    pass


async def get_current_user(request: Request) -> dict:
    """Get current user from session cookie.

    Reads the 'session' HTTP-only cookie, validates it against the database,
    and returns the user dict if valid.

    Args:
        request: The incoming FastAPI request.

    Returns:
        User dict with id, email, created_at, last_login_at.

    Raises:
        RequiresLoginException: If no valid session cookie is present.
    """
    token = request.cookies.get("session")
    if not token:
        raise RequiresLoginException()

    user = validate_session_token(token)
    if not user:
        raise RequiresLoginException()

    return user


def requires_login_exception_handler(request: Request, exc: RequiresLoginException) -> RedirectResponse:
    """Exception handler that redirects unauthenticated users to the entrance page.

    Register this on the FastAPI app:
        app.add_exception_handler(RequiresLoginException, requires_login_exception_handler)
    """
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response
