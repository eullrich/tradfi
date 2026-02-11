"""Authentication routes for the web frontend (magic link login + registration)."""

import hmac

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from tradfi.utils.cache import (
    create_magic_link_token,
    create_session_token,
    create_user,
    get_user_by_email,
    revoke_session_token,
    verify_magic_link_token,
)

router = APIRouter(tags=["auth"])

# The answer to the puzzle on the entrance page.
# Graham's three words: "Confronted with the need to distill the secret of
# sound investment into three words, we venture the motto: MARGIN OF SAFETY."
# — The Intelligent Investor, Chapter 20
_REGISTRATION_PASSWORD = "marginofsafety"


@router.post("/auth/register", response_class=HTMLResponse)
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
) -> HTMLResponse:
    """Handle registration form submission.

    Validates the password against the puzzle answer and creates a new user
    account. On success, sets a session cookie and returns an HX-Redirect
    header so HTMX navigates to the screener.

    Args:
        request: The incoming request.
        email: Email address from the registration form.
        password: The puzzle answer.

    Returns:
        HTMX partial HTML snippet with status/redirect.
    """
    email = email.lower().strip()
    password = password.lower().strip().replace(" ", "")

    # Constant-time comparison to avoid timing attacks
    if not hmac.compare_digest(password, _REGISTRATION_PASSWORD):
        return HTMLResponse(
            '<div id="auth-message" class="auth-message auth-message--error">'
            "<p>The Queen is not amused.</p>"
            "</div>",
            status_code=200,
        )

    # Check if user already exists
    existing = get_user_by_email(email)
    if existing:
        return HTMLResponse(
            '<div id="auth-message" class="auth-message auth-message--error">'
            "<p>You've been here before, Alice. Try logging in.</p>"
            "</div>",
            status_code=200,
        )

    # Create the user
    user = create_user(email)
    if not user:
        return HTMLResponse(
            '<div id="auth-message" class="auth-message auth-message--error">'
            "<p>Something went wrong down the rabbit hole.</p>"
            "</div>",
            status_code=200,
        )

    # Create session and auto-login
    session_token = create_session_token(user["id"])
    if not session_token:
        return HTMLResponse(
            '<div id="auth-message" class="auth-message auth-message--error">'
            "<p>Something went wrong. Try again.</p>"
            "</div>",
            status_code=200,
        )

    # Return success with HX-Redirect — HTMX will set the cookie from
    # the response and navigate to the screener.
    response = HTMLResponse(
        '<div id="auth-message" class="auth-message auth-message--success">'
        "<p>Welcome to Wonderland.</p>"
        "</div>",
        status_code=200,
    )
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production behind HTTPS
        max_age=30 * 24 * 60 * 60,  # 30 days
    )
    response.headers["HX-Redirect"] = "/screener"
    return response


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
