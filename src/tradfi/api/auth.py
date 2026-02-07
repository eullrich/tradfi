"""Authentication dependencies for TradFi API."""

import hmac
import logging
import os
from typing import Annotated

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

# Admin API key for destructive operations (cache clear, refresh trigger)
ADMIN_API_KEY = os.environ.get("TRADFI_ADMIN_KEY")

# Explicit dev mode opt-in for unauthenticated admin access
_ADMIN_DEV_MODE = os.environ.get("TRADFI_ADMIN_DEV_MODE", "").lower() in ("1", "true", "yes")


def require_admin_key(
    x_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    """Dependency that requires a valid admin API key.

    The admin key must be set via TRADFI_ADMIN_KEY environment variable
    on the server, and passed via X-Admin-Key header from clients.

    If TRADFI_ADMIN_KEY is not set, admin endpoints are blocked unless
    TRADFI_ADMIN_DEV_MODE=1 is explicitly set for local development.
    """
    if not ADMIN_API_KEY:
        if _ADMIN_DEV_MODE:
            return
        logger.warning(
            "Admin endpoint called without TRADFI_ADMIN_KEY configured. "
            "Set TRADFI_ADMIN_DEV_MODE=1 to allow unauthenticated admin access in development."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin key not configured. Set TRADFI_ADMIN_KEY environment variable.",
        )

    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Key header required for this operation",
        )

    if not hmac.compare_digest(x_admin_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )
