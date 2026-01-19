"""Cache management endpoints."""

from fastapi import APIRouter

from tradfi.api.schemas import CacheStatsSchema, MessageSchema
from tradfi.utils.cache import clear_cache, get_cache_stats, get_all_cached_industries

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
async def get_industries():
    """Get all industries from cached stocks with counts."""
    industries = get_all_cached_industries()
    return [{"name": name, "count": count} for name, count in industries]
