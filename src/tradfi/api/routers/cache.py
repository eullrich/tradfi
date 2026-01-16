"""Cache management endpoints."""

from fastapi import APIRouter

from tradfi.api.schemas import CacheStatsSchema, MessageSchema
from tradfi.utils.cache import clear_cache, get_cache_stats

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats", response_model=CacheStatsSchema)
async def get_stats():
    """Get cache statistics."""
    stats = get_cache_stats()
    return CacheStatsSchema(
        total=stats["total"],
        fresh=stats["fresh"],
        stale=stats["stale"],
    )


@router.post("/clear", response_model=MessageSchema)
async def clear_cache_endpoint():
    """Clear all cached stock data."""
    count = clear_cache()
    return MessageSchema(message=f"Cleared {count} cached entries")
