"""User management endpoints (admin only)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from tradfi.api.auth import require_admin_key
from tradfi.utils.cache import create_user, get_user_by_email

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    """Request to create a new user."""

    email: EmailStr


class UserResponse(BaseModel):
    """User response."""

    id: int
    email: str
    created_at: int
    last_login_at: int | None = None


@router.post(
    "/",
    response_model=UserResponse,
    dependencies=[Depends(require_admin_key)],
)
async def create_user_endpoint(request: CreateUserRequest) -> UserResponse:
    """Create a new user account.

    Requires X-Admin-Key header with valid admin API key.
    """
    user = create_user(request.email)
    if not user:
        # create_user returns None on IntegrityError (duplicate email)
        existing = get_user_by_email(request.email)
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")
        raise HTTPException(status_code=500, detail="Failed to create user")
    return UserResponse(**user)
