"""FastAPI server for TradFi cache status and data."""

from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from tradfi.utils.cache import get_cache_stats

app = FastAPI(title="TradFi API", version="0.1.0")


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
