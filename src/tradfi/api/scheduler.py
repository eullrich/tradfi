"""APScheduler setup for daily stock data refresh."""

import asyncio
import logging
import os
import time
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tradfi.core.data import fetch_stock_from_api_async
from tradfi.core.screener import AVAILABLE_UNIVERSES, load_tickers

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
        delay: Base delay between requests in seconds

    Returns:
        Dict with refresh statistics
    """
    global _refresh_state

    try:
        tickers = load_tickers(universe)
    except FileNotFoundError:
        logger.error(f"Unknown universe: {universe}")
        return {"error": f"Unknown universe: {universe}"}

    ticker_count = len(tickers)

    # Adaptive delay scaling based on universe size
    # Large universes need longer delays to avoid yfinance rate limiting
    if ticker_count > 500:
        delay = max(delay, 3.0) + (ticker_count / 2000)
        per_ticker_timeout = 45.0
    elif ticker_count > 50:
        delay = max(delay, delay * 1.5)
        per_ticker_timeout = 30.0
    else:
        per_ticker_timeout = 30.0

    logger.info(
        f"Starting refresh for {universe} ({ticker_count} tickers, "
        f"delay={delay:.1f}s, timeout={per_ticker_timeout:.0f}s, "
        f"est_duration={ticker_count * delay / 60:.0f}min)"
    )

    _refresh_state["is_running"] = True
    _refresh_state["current_universe"] = universe
    _refresh_state["progress"] = {"total": ticker_count, "completed": 0, "failed": 0}

    start_time = time.time()
    fetched = 0
    failed = 0
    timed_out = 0
    rate_limited = 0
    failed_tickers: list[tuple[str, str]] = []  # (ticker, reason)

    for i, ticker in enumerate(tickers):
        try:
            stock = await fetch_stock_from_api_async(ticker, timeout=per_ticker_timeout)
            if stock:
                fetched += 1
            else:
                failed += 1
                failed_tickers.append((ticker, "no_data"))
                logger.warning(f"No data returned for {ticker}")
        except TimeoutError:
            failed += 1
            timed_out += 1
            failed_tickers.append((ticker, "timeout"))
            logger.warning(f"Timeout fetching {ticker}")
        except Exception as e:
            failed += 1
            error_msg = str(e).lower()
            if "too many requests" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                rate_limited += 1
                failed_tickers.append((ticker, "rate_limit"))
                logger.warning(f"Rate limited on {ticker}: {e}")
                # Extra backoff on rate limit detection
                await asyncio.sleep(delay * 2)
            else:
                failed_tickers.append((ticker, "error"))
                logger.error(f"Error fetching {ticker}: {e}")

        _refresh_state["progress"] = {
            "total": ticker_count,
            "completed": i + 1,
            "fetched": fetched,
            "failed": failed,
            "timed_out": timed_out,
            "rate_limited": rate_limited,
        }

        # Log progress every 50 stocks
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            logger.info(
                f"Progress: {i + 1}/{ticker_count} "
                f"({fetched} ok, {failed} fail, {timed_out} timeout, "
                f"{rate_limited} rate-limited) - {elapsed:.0f}s"
            )

        await asyncio.sleep(delay)

    # Retry pass for failed tickers (only retryable failures)
    retryable = [(t, reason) for t, reason in failed_tickers if reason in ("timeout", "rate_limit")]
    retried = 0

    if retryable:
        retry_delay = delay * 3
        retry_timeout = per_ticker_timeout * 1.5
        logger.info(
            f"Retrying {len(retryable)} failed tickers "
            f"(delay={retry_delay:.1f}s, timeout={retry_timeout:.0f}s)"
        )

        # Cooldown before retry pass to let rate limits reset
        await asyncio.sleep(30)

        for j, (ticker, reason) in enumerate(retryable):
            try:
                stock = await fetch_stock_from_api_async(ticker, timeout=retry_timeout)
                if stock:
                    fetched += 1
                    failed -= 1
                    retried += 1
                    logger.info(f"Retry succeeded for {ticker}")
            except Exception as e:
                logger.debug(f"Retry also failed for {ticker}: {e}")

            if (j + 1) % 50 == 0:
                logger.info(f"Retry progress: {j + 1}/{len(retryable)}")

            await asyncio.sleep(retry_delay)

    elapsed = time.time() - start_time
    stats = {
        "universe": universe,
        "total": ticker_count,
        "fetched": fetched,
        "failed": failed,
        "timed_out": timed_out,
        "rate_limited": rate_limited,
        "retried": retried,
        "effective_delay": round(delay, 2),
        "duration_seconds": round(elapsed, 1),
        "completed_at": datetime.utcnow().isoformat(),
    }

    _refresh_state["is_running"] = False
    _refresh_state["current_universe"] = None
    _refresh_state["progress"] = None
    _refresh_state["last_refresh"] = datetime.utcnow().isoformat()
    _refresh_state["last_refresh_duration"] = round(elapsed, 1)
    _refresh_state["last_refresh_stats"] = stats

    logger.info(
        f"Completed refresh for {universe}: {fetched} fetched, {failed} failed, "
        f"{retried} retried in {elapsed:.0f}s"
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
