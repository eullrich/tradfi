"""APScheduler setup for daily stock data refresh with retry and adaptive delay."""

import asyncio
import logging
import os
import time
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tradfi.core.data import FetchOutcome, fetch_stock_from_api_with_result
from tradfi.core.screener import AVAILABLE_UNIVERSES, load_tickers
from tradfi.utils.cache import get_config

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Retry configuration
MAX_RETRY_PASSES = 3  # Maximum number of retry passes after initial sweep
FAILURE_RATE_THRESHOLD = 0.15  # If >15% of a pass fails, increase delay
DELAY_INCREASE_FACTOR = 1.5  # Multiply delay by this on high failure rate
MAX_DELAY = 15.0  # Never exceed this delay (seconds)
INTER_RETRY_PAUSE = 30  # Seconds to pause between retry passes

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


async def refresh_universe(
    universe: str, delay: float = 2.0, max_retries: int = MAX_RETRY_PASSES
) -> dict:
    """
    Refresh all stocks in a universe with retry and adaptive delay.

    Pass 0: Initial sweep of all tickers.
    Pass 1..N: Retry tickers that were STALE or FAILED.

    Adaptive delay: if failure rate exceeds threshold, delay is increased
    to back off from potential yfinance rate limiting.

    Args:
        universe: Universe name (sp500, dow30, etc.)
        delay: Initial delay between requests in seconds
        max_retries: Maximum number of retry passes (default: 3)

    Returns:
        Dict with detailed refresh statistics
    """
    global _refresh_state

    try:
        tickers = load_tickers(universe)
    except FileNotFoundError:
        logger.error(f"Unknown universe: {universe}")
        return {"error": f"Unknown universe: {universe}"}

    total = len(tickers)
    logger.info(f"Starting refresh for {universe} ({total} stocks)")

    _refresh_state["is_running"] = True
    _refresh_state["current_universe"] = universe
    _refresh_state["progress"] = {"total": total, "completed": 0, "failed": 0}

    # Set rate limit delay in-memory only (no disk I/O)
    config = get_config()
    original_delay = config.rate_limit_delay
    config.rate_limit_delay = delay

    start_time = time.time()
    current_delay = delay

    # Track per-ticker outcomes
    results: dict[str, str] = {}  # ticker -> "fresh" | "stale" | "failed"

    pending = list(tickers)
    pass_num = 0

    while pending and pass_num <= max_retries:
        if pass_num > 0:
            logger.info(
                f"Retry pass {pass_num}/{max_retries}: {len(pending)} tickers "
                f"(delay={current_delay:.1f}s)"
            )
            await asyncio.sleep(INTER_RETRY_PAUSE)

        pass_fresh = 0
        pass_stale = 0
        pass_failed = 0

        for i, ticker in enumerate(pending):
            try:
                result = await asyncio.to_thread(fetch_stock_from_api_with_result, ticker)
                results[ticker] = result.outcome.value

                if result.outcome == FetchOutcome.FRESH:
                    pass_fresh += 1
                elif result.outcome == FetchOutcome.STALE:
                    pass_stale += 1
                    logger.debug(f"Stale fallback for {ticker}: {result.error}")
                else:
                    pass_failed += 1
                    logger.warning(f"Failed {ticker}: {result.error}")
            except Exception as e:
                results[ticker] = "failed"
                pass_failed += 1
                logger.error(f"Exception fetching {ticker}: {e}")

            # Update progress
            fresh_total = sum(1 for v in results.values() if v == "fresh")
            stale_total = sum(1 for v in results.values() if v == "stale")
            failed_total = sum(1 for v in results.values() if v == "failed")

            _refresh_state["progress"] = {
                "total": total,
                "completed": len(results),
                "fresh": fresh_total,
                "stale": stale_total,
                "failed": failed_total,
                "pass": pass_num,
                "pass_progress": f"{i + 1}/{len(pending)}",
            }

            # Log progress every 50 stocks
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start_time
                logger.info(
                    f"Pass {pass_num} progress: {i + 1}/{len(pending)} "
                    f"({pass_fresh} fresh, {pass_stale} stale, {pass_failed} failed) "
                    f"- {elapsed:.0f}s"
                )

        # Adaptive delay: increase on high failure rate
        pass_total = pass_fresh + pass_stale + pass_failed
        if pass_total > 0:
            failure_rate = (pass_stale + pass_failed) / pass_total
            if failure_rate > FAILURE_RATE_THRESHOLD and current_delay < MAX_DELAY:
                new_delay = min(current_delay * DELAY_INCREASE_FACTOR, MAX_DELAY)
                logger.info(
                    f"High failure rate ({failure_rate:.0%}), increasing delay "
                    f"{current_delay:.1f}s -> {new_delay:.1f}s"
                )
                current_delay = new_delay
                config.rate_limit_delay = current_delay

        # Build list of tickers to retry (stale + failed only, not fresh)
        pending = [t for t in pending if results.get(t) in ("stale", "failed")]
        pass_num += 1

    # Restore original delay in-memory
    config.rate_limit_delay = original_delay

    elapsed = time.time() - start_time
    fresh_count = sum(1 for v in results.values() if v == "fresh")
    stale_count = sum(1 for v in results.values() if v == "stale")
    failed_count = sum(1 for v in results.values() if v == "failed")

    stats = {
        "universe": universe,
        "total": total,
        "fresh": fresh_count,
        "stale": stale_count,
        "failed": failed_count,
        "retry_passes": pass_num - 1,
        "final_delay": round(current_delay, 1),
        "duration_seconds": round(elapsed, 1),
        "completed_at": datetime.utcnow().isoformat(),
        # Legacy field for backwards compatibility
        "fetched": fresh_count + stale_count,
    }

    # Log failed/stale tickers for diagnosis
    if failed_count > 0:
        failed_tickers = [t for t, v in results.items() if v == "failed"]
        logger.warning(
            f"Failed tickers ({failed_count}): "
            f"{failed_tickers[:20]}{'...' if failed_count > 20 else ''}"
        )
    if stale_count > 0:
        stale_tickers = [t for t, v in results.items() if v == "stale"]
        logger.warning(
            f"Stale tickers ({stale_count}): "
            f"{stale_tickers[:20]}{'...' if stale_count > 20 else ''}"
        )

    _refresh_state["is_running"] = False
    _refresh_state["current_universe"] = None
    _refresh_state["progress"] = None
    _refresh_state["last_refresh"] = datetime.utcnow().isoformat()
    _refresh_state["last_refresh_duration"] = round(elapsed, 1)
    _refresh_state["last_refresh_stats"] = stats

    logger.info(
        f"Completed refresh for {universe}: "
        f"{fresh_count} fresh, {stale_count} stale, {failed_count} failed "
        f"in {elapsed:.0f}s ({pass_num - 1} retries)"
    )

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
            await asyncio.sleep(5)

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


def get_next_scheduled_refresh() -> str | None:
    """Get the next scheduled refresh time as ISO string."""
    try:
        job = scheduler.get_job("daily_refresh")
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
    except Exception:
        pass
    return None


def get_scheduler_config() -> dict:
    """Get scheduler configuration info."""
    enabled = os.environ.get("TRADFI_REFRESH_ENABLED", "true").lower() != "false"
    hour = int(os.environ.get("TRADFI_REFRESH_HOUR", "5"))
    minute = int(os.environ.get("TRADFI_REFRESH_MINUTE", "0"))

    return {
        "enabled": enabled,
        "schedule_hour_utc": hour,
        "schedule_minute": minute,
        "schedule_display": f"{hour:02d}:{minute:02d} UTC daily",
    }


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
