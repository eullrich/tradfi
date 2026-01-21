"""FastAPI server for TradFi cache status and data."""

import os
from datetime import datetime
from typing import Annotated

# Development mode: returns magic link tokens in response for testing
# In production, set TRADFI_PRODUCTION=1 to disable token exposure
IS_PRODUCTION = os.getenv("TRADFI_PRODUCTION", "").lower() in ("1", "true", "yes")

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from tradfi.utils.cache import (
    create_magic_link_token,
    get_batch_cached_stocks,
    get_cache_stats,
    revoke_session_token,
    user_add_to_list,
    user_add_to_watchlist,
    user_clear_position,
    user_create_list,
    user_delete_list,
    user_get_list,
    user_get_list_items,
    user_get_list_items_with_positions,
    user_get_lists,
    user_get_position,
    user_get_watchlist,
    user_has_positions,
    user_remove_from_list,
    user_remove_from_watchlist,
    user_set_position,
    user_update_list_item_notes,
    user_update_watchlist_notes,
    validate_session_token,
    verify_magic_link_token,
)
from tradfi.core.portfolio import calculate_portfolio_metrics

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
    magic_link_token: str | None = None  # Only populated in development mode


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


# Watchlist models
class WatchlistItemRequest(BaseModel):
    """Request to add/update a watchlist item."""
    ticker: str
    notes: str | None = None


class WatchlistItemResponse(BaseModel):
    """Watchlist item response."""
    ticker: str
    added_at: int
    notes: str | None


# List models
class CreateListRequest(BaseModel):
    """Request to create a new list."""
    name: str
    description: str | None = None


class ListResponse(BaseModel):
    """Saved list response."""
    id: int
    name: str
    description: str | None
    created_at: int
    updated_at: int
    item_count: int | None = None


class ListItemRequest(BaseModel):
    """Request to add/update a list item."""
    ticker: str
    notes: str | None = None


class ListItemResponse(BaseModel):
    """List item response."""
    ticker: str
    added_at: int
    notes: str | None


# Position/Portfolio models
class PositionRequest(BaseModel):
    """Request to set position data for a list item."""
    shares: float | None = None
    entry_price: float | None = None
    target_price: float | None = None
    thesis: str | None = None


class PositionResponse(BaseModel):
    """Position data for a single item."""
    ticker: str
    shares: float | None = None
    entry_price: float | None = None
    target_price: float | None = None
    thesis: str | None = None
    notes: str | None = None
    added_at: int | None = None


class PortfolioItemResponse(BaseModel):
    """Full portfolio item with calculated P&L metrics."""
    ticker: str
    shares: float | None = None
    entry_price: float | None = None
    current_price: float | None = None
    target_price: float | None = None
    cost_basis: float | None = None
    current_value: float | None = None
    gain_loss: float | None = None
    gain_loss_pct: float | None = None
    allocation_pct: float | None = None
    cost_allocation_pct: float | None = None
    target_gain_pct: float | None = None
    distance_to_target_pct: float | None = None
    notes: str | None = None
    thesis: str | None = None


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary with aggregated metrics."""
    list_name: str
    items: list[PortfolioItemResponse]
    total_cost_basis: float
    total_current_value: float
    total_gain_loss: float
    total_gain_loss_pct: float | None
    position_count: int


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
        magic_link_token=None if IS_PRODUCTION else token,
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


# ============================================================================
# Watchlist Endpoints (User-Scoped)
# ============================================================================


@app.get("/api/watchlist", response_model=list[WatchlistItemResponse])
def get_watchlist(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> list[WatchlistItemResponse]:
    """Get the current user's watchlist."""
    items = user_get_watchlist(current_user["id"])
    return [WatchlistItemResponse(**item) for item in items]


@app.post("/api/watchlist", response_model=MessageResponse)
def add_to_watchlist(
    request: WatchlistItemRequest,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """Add a ticker to the current user's watchlist."""
    added = user_add_to_watchlist(current_user["id"], request.ticker, request.notes)
    if added:
        return MessageResponse(message=f"{request.ticker.upper()} added to watchlist")
    return MessageResponse(message=f"{request.ticker.upper()} already in watchlist")


@app.delete("/api/watchlist/{ticker}", response_model=MessageResponse)
def remove_from_watchlist(
    ticker: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """Remove a ticker from the current user's watchlist."""
    removed = user_remove_from_watchlist(current_user["id"], ticker)
    if removed:
        return MessageResponse(message=f"{ticker.upper()} removed from watchlist")
    raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in watchlist")


@app.patch("/api/watchlist/{ticker}", response_model=MessageResponse)
def update_watchlist_notes(
    ticker: str,
    request: WatchlistItemRequest,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """Update notes for a watchlist item."""
    if request.notes is None:
        raise HTTPException(status_code=400, detail="Notes field required")
    updated = user_update_watchlist_notes(current_user["id"], ticker, request.notes)
    if updated:
        return MessageResponse(message=f"Notes updated for {ticker.upper()}")
    raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in watchlist")


# ============================================================================
# Saved Lists Endpoints (User-Scoped)
# ============================================================================


@app.get("/api/lists", response_model=list[ListResponse])
def get_lists(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> list[ListResponse]:
    """Get all saved lists for the current user."""
    lists = user_get_lists(current_user["id"])
    return [ListResponse(**lst) for lst in lists]


@app.post("/api/lists", response_model=ListResponse)
def create_list(
    request: CreateListRequest,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> ListResponse:
    """Create a new saved list."""
    result = user_create_list(current_user["id"], request.name, request.description)
    if result:
        return ListResponse(**result, item_count=0)
    raise HTTPException(status_code=409, detail=f"List '{request.name}' already exists")


@app.get("/api/lists/{list_name}", response_model=ListResponse)
def get_list(
    list_name: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> ListResponse:
    """Get a specific saved list."""
    result = user_get_list(current_user["id"], list_name)
    if result:
        items = user_get_list_items(current_user["id"], list_name)
        return ListResponse(**result, item_count=len(items) if items else 0)
    raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")


@app.delete("/api/lists/{list_name}", response_model=MessageResponse)
def delete_list(
    list_name: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """Delete a saved list."""
    deleted = user_delete_list(current_user["id"], list_name)
    if deleted:
        return MessageResponse(message=f"List '{list_name}' deleted")
    raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")


@app.get("/api/lists/{list_name}/items", response_model=list[ListItemResponse])
def get_list_items(
    list_name: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> list[ListItemResponse]:
    """Get all items in a saved list."""
    items = user_get_list_items(current_user["id"], list_name)
    if items is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    return [ListItemResponse(**item) for item in items]


@app.post("/api/lists/{list_name}/items", response_model=MessageResponse)
def add_to_list(
    list_name: str,
    request: ListItemRequest,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """Add a ticker to a saved list."""
    added = user_add_to_list(
        current_user["id"], list_name, request.ticker, request.notes
    )
    if added:
        return MessageResponse(message=f"{request.ticker.upper()} added to '{list_name}'")
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    return MessageResponse(message=f"{request.ticker.upper()} already in '{list_name}'")


@app.delete("/api/lists/{list_name}/items/{ticker}", response_model=MessageResponse)
def remove_from_list(
    list_name: str,
    ticker: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """Remove a ticker from a saved list."""
    removed = user_remove_from_list(current_user["id"], list_name, ticker)
    if removed:
        return MessageResponse(message=f"{ticker.upper()} removed from '{list_name}'")
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in '{list_name}'")


@app.patch("/api/lists/{list_name}/items/{ticker}", response_model=MessageResponse)
def update_list_item_notes(
    list_name: str,
    ticker: str,
    request: ListItemRequest,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """Update notes for an item in a saved list."""
    if request.notes is None:
        raise HTTPException(status_code=400, detail="Notes field required")
    updated = user_update_list_item_notes(
        current_user["id"], list_name, ticker, request.notes
    )
    if updated:
        return MessageResponse(message=f"Notes updated for {ticker.upper()}")
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in '{list_name}'")


# ============================================================================
# Position/Portfolio Endpoints (User-Scoped)
# ============================================================================


@app.put("/api/lists/{list_name}/items/{ticker}/position", response_model=MessageResponse)
def set_position(
    list_name: str,
    ticker: str,
    request: PositionRequest,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """
    Set position data for a list item (shares, entry_price, target_price, thesis).

    This enables portfolio tracking with P&L calculations.
    """
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")

    # Check if at least one field is provided
    if all(v is None for v in [request.shares, request.entry_price, request.target_price, request.thesis]):
        raise HTTPException(
            status_code=400,
            detail="At least one field (shares, entry_price, target_price, thesis) is required"
        )

    updated = user_set_position(
        current_user["id"],
        list_name,
        ticker,
        shares=request.shares,
        entry_price=request.entry_price,
        target_price=request.target_price,
        thesis=request.thesis,
    )

    if updated:
        return MessageResponse(message=f"Position updated for {ticker.upper()}")
    raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in '{list_name}'")


@app.get("/api/lists/{list_name}/items/{ticker}/position", response_model=PositionResponse)
def get_position(
    list_name: str,
    ticker: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> PositionResponse:
    """Get position data for a specific item in a list."""
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")

    position = user_get_position(current_user["id"], list_name, ticker)
    if position is None:
        raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in '{list_name}'")

    return PositionResponse(**position)


@app.delete("/api/lists/{list_name}/items/{ticker}/position", response_model=MessageResponse)
def clear_position(
    list_name: str,
    ticker: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> MessageResponse:
    """
    Clear position data for a list item (set shares/entry_price to NULL).

    The item remains in the list with notes preserved.
    """
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")

    cleared = user_clear_position(current_user["id"], list_name, ticker)
    if cleared:
        return MessageResponse(message=f"Position cleared for {ticker.upper()}")
    raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in '{list_name}'")


@app.get("/api/lists/{list_name}/portfolio", response_model=PortfolioSummaryResponse)
def get_portfolio(
    list_name: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> PortfolioSummaryResponse:
    """
    Get full portfolio view with P&L calculations for a list.

    Returns all items with position data along with calculated metrics:
    - cost_basis: shares * entry_price
    - current_value: shares * current_price
    - gain_loss: current_value - cost_basis
    - gain_loss_pct: (gain_loss / cost_basis) * 100
    - allocation_pct: (current_value / total_value) * 100
    """
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")

    # Get all items with position data
    items = user_get_list_items_with_positions(current_user["id"], list_name)
    if items is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")

    # Get current prices from cache
    tickers = [item["ticker"] for item in items if item.get("ticker")]
    cached_stocks = get_batch_cached_stocks(tickers) if tickers else {}

    # Build price lookup
    current_prices = {}
    for ticker, data in cached_stocks.items():
        if data and "current_price" in data:
            current_prices[ticker] = data["current_price"]

    # Calculate portfolio metrics
    portfolio = calculate_portfolio_metrics(items, current_prices)
    result = portfolio.to_dict(list_name)

    return PortfolioSummaryResponse(
        list_name=result["list_name"],
        items=[PortfolioItemResponse(**item) for item in result["items"]],
        total_cost_basis=result["total_cost_basis"],
        total_current_value=result["total_current_value"],
        total_gain_loss=result["total_gain_loss"],
        total_gain_loss_pct=result["total_gain_loss_pct"],
        position_count=result["position_count"],
    )


@app.get("/api/lists/{list_name}/has-positions")
def check_has_positions(
    list_name: str,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> JSONResponse:
    """Check if a list has any position data (for determining display mode)."""
    # Check if list exists
    if user_get_list(current_user["id"], list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")

    has_pos = user_has_positions(current_user["id"], list_name)
    return JSONResponse({"has_positions": has_pos})
