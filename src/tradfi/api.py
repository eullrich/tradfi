"""FastAPI server for TradFi cache status and data."""

from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from tradfi.utils.cache import (
    create_magic_link_token,
    get_cache_stats,
    revoke_session_token,
    validate_session_token,
    verify_magic_link_token,
)

app = FastAPI(title="TradFi API", version="0.1.0")


# ============================================================================
# Pydantic Models
# ============================================================================


class RegisterRequest(BaseModel):
    """Request to register/login with email."""
    email: EmailStr


class RegisterResponse(BaseModel):
    """Response after requesting magic link."""
    message: str
    email: str
    # In production, don't return token - send via email instead
    # Included here for development/testing
    magic_link_token: str | None = None


class VerifyRequest(BaseModel):
    """Request to verify magic link token."""
    token: str


class AuthResponse(BaseModel):
    """Response with session token and user info."""
    session_token: str
    user: dict


class UserResponse(BaseModel):
    """User information response."""
    id: int
    email: str
    created_at: int
    last_login_at: int | None


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# ============================================================================
# Auth Dependencies
# ============================================================================


def get_current_user(
    authorization: Annotated[str | None, Header()] = None
) -> dict:
    """
    Validate the session token and return the current user.

    Expects header: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Invalid authorization format. Use: Bearer <token>"
        )

    token = parts[1]
    user = validate_session_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return user


def get_optional_user(
    authorization: Annotated[str | None, Header()] = None
) -> dict | None:
    """
    Optionally validate the session token. Returns None if not authenticated.
    """
    if not authorization:
        return None

    try:
        return get_current_user(authorization)
    except HTTPException:
        return None


# ============================================================================
# Auth Endpoints
# ============================================================================


@app.post("/api/auth/register", response_model=RegisterResponse)
def register(request: RegisterRequest) -> RegisterResponse:
    """
    Register a new user or request login for existing user.

    This creates a magic link token. In production, this would be sent
    via email. For development, the token is returned in the response.
    """
    token, user = create_magic_link_token(request.email)

    if not token or not user:
        raise HTTPException(status_code=500, detail="Failed to create account")

    is_new = user.get("last_login_at") is None
    action = "created" if is_new else "login requested"

    return RegisterResponse(
        message=f"Account {action}. Check your email for the magic link.",
        email=request.email,
        magic_link_token=token,  # Remove in production
    )


@app.post("/api/auth/verify", response_model=AuthResponse)
def verify(request: VerifyRequest) -> AuthResponse:
    """
    Verify a magic link token and get a session token.

    Use the session token in the Authorization header for authenticated requests:
    Authorization: Bearer <session_token>
    """
    session_token, user = verify_magic_link_token(request.token)

    if not session_token or not user:
        raise HTTPException(status_code=401, detail="Invalid or expired magic link token")

    return AuthResponse(session_token=session_token, user=user)


@app.post("/api/auth/logout", response_model=MessageResponse)
def logout(
    current_user: Annotated[dict, Depends(get_current_user)],
    authorization: Annotated[str, Header()]
) -> MessageResponse:
    """
    Logout and invalidate the current session token.
    """
    token = authorization.split(" ")[1]
    revoke_session_token(token)
    return MessageResponse(message="Logged out successfully")


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: Annotated[dict, Depends(get_current_user)]) -> UserResponse:
    """
    Get the current authenticated user's information.
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        created_at=current_user["created_at"],
        last_login_at=current_user.get("last_login_at"),
    )


# ============================================================================
# Existing Endpoints
# ============================================================================


@app.get("/api/cache/status")
def cache_status() -> JSONResponse:
    """Get cache status and statistics."""
    stats = get_cache_stats()

    # Format last_updated as ISO string
    last_updated_iso = None
    last_updated_ago = None
    if stats.get("last_updated"):
        last_updated_iso = datetime.fromtimestamp(stats["last_updated"]).isoformat()
        age_seconds = datetime.now().timestamp() - stats["last_updated"]
        if age_seconds < 60:
            last_updated_ago = f"{int(age_seconds)}s ago"
        elif age_seconds < 3600:
            last_updated_ago = f"{int(age_seconds / 60)}m ago"
        elif age_seconds < 86400:
            last_updated_ago = f"{int(age_seconds / 3600)}h ago"
        else:
            last_updated_ago = f"{int(age_seconds / 86400)}d ago"

    return JSONResponse({
        "total_cached": stats["total_cached"],
        "fresh": stats["fresh"],
        "stale": stats["stale"],
        "cache_ttl_minutes": stats["cache_ttl_minutes"],
        "last_updated": last_updated_iso,
        "last_updated_ago": last_updated_ago,
    })


@app.get("/health")
def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})
