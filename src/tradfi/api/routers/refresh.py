"""Refresh endpoints for scheduled stock data updates."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from tradfi.api.auth import require_admin_key
from tradfi.api.scheduler import (
    get_next_scheduled_refresh,
    get_refresh_state,
    get_scheduler_config,
    refresh_universe,
)
from tradfi.core.screener import AVAILABLE_UNIVERSES, load_tickers
from tradfi.utils.cache import get_batch_cache_freshness, get_cache_stats

router = APIRouter(prefix="/refresh", tags=["refresh"])


class RefreshStatusSchema(BaseModel):
    """Current refresh status."""

    last_refresh: str | None = None
    last_refresh_duration: float | None = None
    last_refresh_stats: dict | None = None
    is_running: bool = False
    current_universe: str | None = None
    progress: dict | None = None


class RefreshTriggerResponse(BaseModel):
    """Response from triggering a refresh."""

    message: str
    universe: str
    estimated_duration_minutes: float


class UniverseStatsSchema(BaseModel):
    """Statistics for a universe."""

    name: str
    description: str
    total: int
    cached: int
    fresh: int = 0
    stale: int = 0
    missing: int
    est_refresh_minutes: float


@router.get("/status", response_model=RefreshStatusSchema)
async def get_status():
    """
    Get the current refresh status.

    Returns information about the last refresh and any currently running refresh.
    """
    state = get_refresh_state()
    return RefreshStatusSchema(**state)


@router.post(
    "/{universe}",
    response_model=RefreshTriggerResponse,
    dependencies=[Depends(require_admin_key)],
)
async def trigger_refresh(
    universe: str,
    background_tasks: BackgroundTasks,
    delay: float = Query(2.0, description="Delay between requests in seconds", ge=0.5, le=30),
):
    """
    Trigger a background refresh for a specific universe.

    Requires X-Admin-Key header with valid admin API key.

    The refresh runs in the background. Check /refresh/status for progress.

    Available universes: dow30, nasdaq100, sp500, russell2000, etc.
    """
    if universe not in AVAILABLE_UNIVERSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown universe: {universe}. Available: {list(AVAILABLE_UNIVERSES.keys())}",
        )

    state = get_refresh_state()
    if state["is_running"]:
        raise HTTPException(
            status_code=409,
            detail=f"Refresh already in progress for {state['current_universe']}",
        )

    # Calculate estimated duration
    try:
        tickers = load_tickers(universe)
        est_minutes = round(len(tickers) * delay / 60, 1)
    except Exception:
        est_minutes = 0

    # Start refresh in background
    background_tasks.add_task(refresh_universe, universe, delay)

    return RefreshTriggerResponse(
        message=f"Refresh started for {universe}",
        universe=universe,
        estimated_duration_minutes=est_minutes,
    )


@router.get("/universes", response_model=list[UniverseStatsSchema])
async def get_universe_stats():
    """
    Get statistics for all available universes.

    Shows how many stocks are cached (fresh vs stale) vs missing for each universe.
    """
    results = []

    for name, description in AVAILABLE_UNIVERSES.items():
        try:
            tickers = load_tickers(name)
            freshness = get_batch_cache_freshness(tickers)

            fresh_count = sum(1 for v in freshness.values() if v == "fresh")
            stale_count = sum(1 for v in freshness.values() if v == "stale")
            missing_count = sum(1 for v in freshness.values() if v == "missing")

            results.append(
                UniverseStatsSchema(
                    name=name,
                    description=description,
                    total=len(tickers),
                    cached=fresh_count + stale_count,
                    fresh=fresh_count,
                    stale=stale_count,
                    missing=missing_count,
                    est_refresh_minutes=round(len(tickers) * 2 / 60, 1),  # 2s default delay
                )
            )
        except Exception:
            pass

    return results


@router.get("/health")
async def refresh_health():
    """
    Health check for the refresh system.

    Returns cache stats, scheduler status, and next scheduled refresh.
    """
    state = get_refresh_state()
    cache_stats = get_cache_stats()
    scheduler_config = get_scheduler_config()

    return {
        "scheduler_running": not state["is_running"],  # Not blocked by a refresh
        "last_refresh": state["last_refresh"],
        "last_refresh_stats": state.get("last_refresh_stats"),
        "next_scheduled_refresh": get_next_scheduled_refresh(),
        "scheduler": scheduler_config,
        "cache_stats": cache_stats,
    }
