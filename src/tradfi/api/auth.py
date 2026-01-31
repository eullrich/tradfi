"""Authentication dependencies for TradFi API."""

import os
from typing import Annotated

from fastapi import Header, HTTPException, status

# Admin API key for destructive operations (cache clear, refresh trigger)
ADMIN_API_KEY = os.environ.get("TRADFI_ADMIN_KEY")


def require_admin_key(
    x_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    """Dependency that requires a valid admin API key.

    The admin key must be set via TRADFI_ADMIN_KEY environment variable
    on the server, and passed via X-Admin-Key header from clients.

    If TRADFI_ADMIN_KEY is not set, admin endpoints are open (for local dev).
    """
    if not ADMIN_API_KEY:
        # No admin key configured - allow access (local dev mode)
        return

    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Key header required for this operation",
        )

    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )
