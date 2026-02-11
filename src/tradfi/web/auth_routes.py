"""Authentication routes for the web frontend (magic link login)."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from tradfi.utils.cache import (
    create_magic_link_token,
    get_user_by_email,
    revoke_session_token,
    verify_magic_link_token,
)

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...)) -> HTMLResponse:
    """Handle login form submission.

    Checks if the email exists in the allowlist (pre-created users only).
    If found, creates a magic link token. If not, returns a rejection message.

    For now, the token is created but no email is actually sent (Resend
    integration comes later). In dev mode the token can be retrieved from
    the database or logs.

    Args:
        request: The incoming request.
        email: Email address from the login form.

    Returns:
        HTMX partial HTML snippet with status message.
    """
    email = email.lower().strip()

    # Check allowlist: only existing users can log in
    user = get_user_by_email(email)
    if not user:
        return HTMLResponse(
            '<div id="auth-message" class="auth-message auth-message--error">'
            "<p>The door is locked.</p>"
            "</div>",
            status_code=200,
        )

    # Create magic link token (does not send email yet)
    token, _user = create_magic_link_token(email)
    if not token:
        return HTMLResponse(
            '<div id="auth-message" class="auth-message auth-message--error">'
            "<p>Something went wrong. Try again.</p>"
            "</div>",
            status_code=200,
        )

    return HTMLResponse(
        '<div id="auth-message" class="auth-message auth-message--success">'
        "<p>Check your looking glass.</p>"
        "</div>",
        status_code=200,
    )


@router.get("/auth/verify")
async def verify(token: str) -> RedirectResponse:
    """Verify a magic link token and establish a session.

    Validates the magic link token, creates a session token, sets it as
    an HTTP-only cookie, and redirects to the screener.

    Args:
        token: The magic link token from the verification URL.

    Returns:
        Redirect to /screener on success, or / on failure.
    """
    session_token, user = verify_magic_link_token(token)

    if not session_token or not user:
        return RedirectResponse(url="/", status_code=303)

    response = RedirectResponse(url="/screener", status_code=303)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production behind HTTPS
        max_age=30 * 24 * 60 * 60,  # 30 days
    )
    return response


@router.post("/auth/logout")
async def logout(request: Request) -> RedirectResponse:
    """Log out the current user.

    Revokes the session token in the database and clears the session cookie.

    Args:
        request: The incoming request.

    Returns:
        Redirect to the entrance page.
    """
    token = request.cookies.get("session")
    if token:
        revoke_session_token(token)

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response
