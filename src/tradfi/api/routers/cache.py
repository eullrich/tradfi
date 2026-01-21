"""Cache management endpoints."""

from fastapi import APIRouter, Query

from tradfi.api.schemas import CacheStatsSchema, MessageSchema
from tradfi.utils.cache import (
    clear_cache,
    get_all_cached_industries,
    get_cache_stats,
    get_industries_for_tickers,
)

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats", response_model=CacheStatsSchema)
async def get_stats():
    """Get cache statistics including last update timestamps."""
    stats = get_cache_stats()
    return CacheStatsSchema(**stats)


@router.post("/clear", response_model=MessageSchema)
async def clear_cache_endpoint():
    """Clear all cached stock data."""
    count = clear_cache()
    return MessageSchema(message=f"Cleared {count} cached entries")


@router.get("/industries")
async def get_industries(tickers: list[str] | None = Query(default=None)):
    """Get industries with their stock counts from cache.

    Args:
        tickers: Optional list of tickers to filter by. If not provided,
                 returns all industries from cache.
    """
    if tickers:
        industries = get_industries_for_tickers(tickers)
    else:
        industries = get_all_cached_industries()
    return [{"industry": ind, "count": count} for ind, count in industries]
