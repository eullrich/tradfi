"""Watchlist management endpoints."""

from fastapi import APIRouter

from tradfi.api.schemas import (
    AddTickerSchema,
    MessageSchema,
    WatchlistItemSchema,
    WatchlistNoteSchema,
)
from tradfi.utils.cache import (
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
    update_watchlist_notes,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemSchema])
async def get_watchlist_items():
    """Get all watchlist items."""
    items = get_watchlist()
    return [
        WatchlistItemSchema(
            ticker=item["ticker"],
            added_at=item.get("added_at"),
            notes=item.get("notes"),
        )
        for item in items
    ]


@router.post("", response_model=MessageSchema)
async def add_to_watchlist_endpoint(request: AddTickerSchema):
    """Add a ticker to the watchlist."""
    add_to_watchlist(request.ticker.upper())
    return MessageSchema(message=f"{request.ticker.upper()} added to watchlist")


@router.delete("/{ticker}", response_model=MessageSchema)
async def remove_from_watchlist_endpoint(ticker: str):
    """Remove a ticker from the watchlist."""
    remove_from_watchlist(ticker.upper())
    return MessageSchema(message=f"{ticker.upper()} removed from watchlist")


@router.put("/{ticker}/notes", response_model=MessageSchema)
async def update_watchlist_notes_endpoint(ticker: str, request: WatchlistNoteSchema):
    """Update notes for a watchlist item."""
    update_watchlist_notes(ticker.upper(), request.notes)
    return MessageSchema(message=f"Notes updated for {ticker.upper()}")
