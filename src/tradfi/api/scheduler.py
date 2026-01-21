"""APScheduler setup for daily stock data refresh."""

import logging
import os
import time
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tradfi.core.data import fetch_stock_from_api
from tradfi.core.screener import AVAILABLE_UNIVERSES, load_tickers
from tradfi.utils.cache import get_config, set_rate_limit_delay

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Track refresh state
_refresh_state = {
    "last_refresh": None,
    "last_refresh_duration": None,
    "last_refresh_stats": None,
    "is_running": False,
    "current_universe": None,
    "progress": None,
}


def get_refresh_state() -> dict:
    """Get the current refresh state."""
    return _refresh_state.copy()


async def refresh_universe(universe: str, delay: float = 2.0) -> dict:
    """
    Refresh all stocks in a universe.

    Args:
        universe: Universe name (sp500, dow30, etc.)
        delay: Delay between requests in seconds

    Returns:
        Dict with refresh statistics
    """
    global _refresh_state

    try:
        tickers = load_tickers(universe)
    except FileNotFoundError:
        logger.error(f"Unknown universe: {universe}")
        return {"error": f"Unknown universe: {universe}"}

    logger.info(f"Starting refresh for {universe} ({len(tickers)} stocks)")

    _refresh_state["is_running"] = True
    _refresh_state["current_universe"] = universe
    _refresh_state["progress"] = {"total": len(tickers), "completed": 0, "failed": 0}

    # Set rate limit delay
    original_config = get_config()
    original_delay = original_config.rate_limit_delay
    set_rate_limit_delay(delay)

    start_time = time.time()
    fetched = 0
    failed = 0

    for i, ticker in enumerate(tickers):
        try:
            stock = fetch_stock_from_api(ticker)
            if stock:
                fetched += 1
            else:
                failed += 1
                logger.warning(f"Failed to fetch {ticker}")
        except Exception as e:
            failed += 1
            logger.error(f"Error fetching {ticker}: {e}")

        _refresh_state["progress"] = {
            "total": len(tickers),
            "completed": i + 1,
            "fetched": fetched,
            "failed": failed,
        }

        # Log progress every 50 stocks
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            logger.info(f"Progress: {i + 1}/{len(tickers)} ({fetched} ok, {failed} failed) - {elapsed:.0f}s")

    # Restore original delay
    set_rate_limit_delay(original_delay)

    elapsed = time.time() - start_time
    stats = {
        "universe": universe,
        "total": len(tickers),
        "fetched": fetched,
        "failed": failed,
        "duration_seconds": round(elapsed, 1),
        "completed_at": datetime.utcnow().isoformat(),
    }

    _refresh_state["is_running"] = False
    _refresh_state["current_universe"] = None
    _refresh_state["progress"] = None
    _refresh_state["last_refresh"] = datetime.utcnow().isoformat()
    _refresh_state["last_refresh_duration"] = round(elapsed, 1)
    _refresh_state["last_refresh_stats"] = stats

    logger.info(f"Completed refresh for {universe}: {fetched} fetched, {failed} failed in {elapsed:.0f}s")

    return stats


async def daily_refresh_job():
    """
    Daily job to refresh all configured universes.

    Runs universes in order with delays between each to avoid rate limiting.
    """
    # Default to all available universes
    default_universes = ",".join(AVAILABLE_UNIVERSES.keys())
    universes = os.environ.get("TRADFI_REFRESH_UNIVERSES", default_universes).split(",")
    delay = float(os.environ.get("TRADFI_REFRESH_DELAY", "2.0"))

    logger.info(f"Starting daily refresh for universes: {universes}")

    all_stats = []
    for universe in universes:
        universe = universe.strip()
        if universe and universe in AVAILABLE_UNIVERSES:
            stats = await refresh_universe(universe, delay=delay)
            all_stats.append(stats)
            # Small pause between universes
            time.sleep(5)

    logger.info(f"Daily refresh completed. Stats: {all_stats}")
    return all_stats


def setup_scheduler():
    """
    Set up the APScheduler with daily refresh job.

    Schedule can be configured via environment variables:
    - TRADFI_REFRESH_HOUR: Hour to run (default: 5, i.e., 5 AM UTC)
    - TRADFI_REFRESH_MINUTE: Minute to run (default: 0)
    - TRADFI_REFRESH_ENABLED: Set to "false" to disable (default: true)
    """
    enabled = os.environ.get("TRADFI_REFRESH_ENABLED", "true").lower() != "false"

    if not enabled:
        logger.info("Scheduled refresh disabled via TRADFI_REFRESH_ENABLED=false")
        return

    hour = int(os.environ.get("TRADFI_REFRESH_HOUR", "5"))
    minute = int(os.environ.get("TRADFI_REFRESH_MINUTE", "0"))

    scheduler.add_job(
        daily_refresh_job,
        CronTrigger(hour=hour, minute=minute),
        id="daily_refresh",
        replace_existing=True,
        name="Daily stock data refresh",
    )

    scheduler.start()
    logger.info(f"Scheduler started. Daily refresh scheduled at {hour:02d}:{minute:02d} UTC")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
