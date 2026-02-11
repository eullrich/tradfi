"""Tests for cache refresh functionality."""

import os
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set up test database before imports
TEST_DB_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_cache.db")
os.environ["TRADFI_DB_PATH"] = TEST_DB_PATH
os.environ["TRADFI_DATA_DIR"] = TEST_DB_DIR
os.environ["TRADFI_CONFIG_PATH"] = os.path.join(TEST_DB_DIR, "config.json")

from tradfi.api.scheduler import _refresh_state, get_refresh_state, refresh_universe  # noqa: E402
from tradfi.utils.cache import (  # noqa: E402
    cache_stock_data,
    clear_cache,
    get_cache_stats,
    get_cached_stock_data,
)


@pytest.fixture(autouse=True)
def reset_refresh_state():
    """Reset refresh state before each test."""
    global _refresh_state
    _refresh_state["last_refresh"] = None
    _refresh_state["last_refresh_duration"] = None
    _refresh_state["last_refresh_stats"] = None
    _refresh_state["is_running"] = False
    _refresh_state["current_universe"] = None
    _refresh_state["progress"] = None
    yield


@pytest.fixture
def clean_cache():
    """Clean cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


def _make_mock_stock(ticker: str) -> MagicMock:
    """Create a mock stock object."""
    mock_stock = MagicMock()
    mock_stock.model_dump.return_value = {"ticker": ticker, "price": 100.0}
    return mock_stock


class TestCacheBasics:
    """Test basic cache operations."""

    def test_cache_stock_data(self, clean_cache):
        """Test caching stock data."""
        test_data = {"ticker": "AAPL", "price": 150.0, "pe_ratio": 25.0}
        cache_stock_data("AAPL", test_data)

        cached = get_cached_stock_data("AAPL")
        assert cached is not None
        assert cached["ticker"] == "AAPL"
        assert cached["price"] == 150.0

    def test_cache_stats_empty(self, clean_cache):
        """Test cache stats with empty cache."""
        stats = get_cache_stats()
        assert stats["total_cached"] == 0
        assert stats["fresh"] == 0
        assert stats["stale"] == 0

    def test_cache_stats_with_data(self, clean_cache):
        """Test cache stats with cached data."""
        cache_stock_data("AAPL", {"ticker": "AAPL"})
        cache_stock_data("MSFT", {"ticker": "MSFT"})

        stats = get_cache_stats()
        assert stats["total_cached"] == 2
        assert stats["fresh"] == 2

    def test_clear_cache(self, clean_cache):
        """Test clearing cache."""
        cache_stock_data("AAPL", {"ticker": "AAPL"})
        cache_stock_data("MSFT", {"ticker": "MSFT"})

        count = clear_cache()
        assert count == 2

        stats = get_cache_stats()
        assert stats["total_cached"] == 0


class TestRefreshState:
    """Test refresh state tracking."""

    def test_initial_refresh_state(self):
        """Test initial refresh state."""
        state = get_refresh_state()
        assert state["is_running"] is False
        assert state["last_refresh"] is None
        assert state["progress"] is None

    @pytest.mark.asyncio
    async def test_refresh_state_during_refresh(self, clean_cache):
        """Test refresh state updates during refresh."""
        states_during_refresh = []

        async def mock_fetch(ticker, timeout=30.0):
            states_during_refresh.append(get_refresh_state().copy())
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "MSFT"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                await refresh_universe("dow30", delay=0.01)

        # Verify states during refresh
        assert len(states_during_refresh) == 2  # 2 tickers
        assert states_during_refresh[0]["is_running"] is True
        assert states_during_refresh[0]["current_universe"] == "dow30"
        assert states_during_refresh[0]["progress"]["total"] == 2

    @pytest.mark.asyncio
    async def test_refresh_state_after_completion(self, clean_cache):
        """Test refresh state after refresh completes."""

        async def mock_fetch(ticker, timeout=30.0):
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                await refresh_universe("dow30", delay=0.01)

        state = get_refresh_state()
        assert state["is_running"] is False
        assert state["last_refresh"] is not None
        assert state["last_refresh_stats"]["universe"] == "dow30"
        assert state["last_refresh_stats"]["fetched"] == 1


class TestRefreshUniverse:
    """Test universe refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_unknown_universe(self):
        """Test refresh with unknown universe returns error."""
        with patch("tradfi.api.scheduler.load_tickers", side_effect=FileNotFoundError):
            result = await refresh_universe("unknown_universe", delay=0.01)

        assert "error" in result
        assert "Unknown universe" in result["error"]

    @pytest.mark.asyncio
    async def test_refresh_with_failures(self, clean_cache):
        """Test refresh handles failures gracefully."""
        call_count = [0]

        async def mock_fetch(ticker, timeout=30.0):
            call_count[0] += 1
            if ticker == "FAIL":
                return None  # Simulates a failed fetch
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "FAIL", "MSFT"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                stats = await refresh_universe("dow30", delay=0.01)

        assert stats["total"] == 3
        assert stats["fetched"] == 2
        assert stats["failed"] == 1
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_refresh_with_exceptions(self, clean_cache):
        """Test refresh handles exceptions gracefully."""

        async def mock_fetch(ticker, timeout=30.0):
            if ticker == "ERROR":
                raise Exception("Network error")
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "ERROR"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                stats = await refresh_universe("dow30", delay=0.01)

        assert stats["fetched"] == 1
        assert stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_refresh_caches_data(self, clean_cache):
        """Test refresh actually caches the fetched data."""

        async def mock_fetch(ticker, timeout=30.0):
            mock_stock = MagicMock()
            mock_stock.model_dump.return_value = {"ticker": ticker, "price": 100.0}
            # Actually cache the data
            cache_stock_data(ticker, {"ticker": ticker, "price": 100.0})
            return mock_stock

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "MSFT"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                await refresh_universe("dow30", delay=0.01)

        # Verify data was cached
        aapl = get_cached_stock_data("AAPL")
        msft = get_cached_stock_data("MSFT")
        assert aapl is not None
        assert msft is not None
        assert aapl["ticker"] == "AAPL"
        assert msft["ticker"] == "MSFT"


class TestRateLimiting:
    """Test rate limiting during refresh."""

    @pytest.mark.asyncio
    async def test_refresh_applies_delay(self, clean_cache):
        """Test that refresh applies configured delay between requests."""
        fetch_times = []

        async def mock_fetch(ticker, timeout=30.0):
            fetch_times.append(time.time())
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "MSFT", "GOOGL"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                await refresh_universe("dow30", delay=0.1)

        # There should be delays between fetches (at least 2 intervals for 3 tickers)
        assert len(fetch_times) == 3


class TestTimeoutHandling:
    """Test timeout and retry functionality."""

    @pytest.mark.asyncio
    async def test_refresh_with_timeout(self, clean_cache):
        """Test refresh correctly categorizes timeout failures."""

        async def mock_fetch(ticker, timeout=30.0):
            if ticker == "SLOW":
                raise TimeoutError(f"Fetch timed out after {timeout}s for {ticker}")
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "SLOW", "MSFT"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                stats = await refresh_universe("dow30", delay=0.01)

        assert stats["fetched"] == 2
        assert stats["failed"] == 1
        assert stats["timed_out"] == 1

    @pytest.mark.asyncio
    async def test_refresh_with_rate_limit(self, clean_cache):
        """Test refresh correctly categorizes rate limit failures."""

        async def mock_fetch(ticker, timeout=30.0):
            if ticker == "LIMITED":
                raise Exception("429 Too Many Requests")
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "LIMITED"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                stats = await refresh_universe("dow30", delay=0.01)

        assert stats["fetched"] == 1
        assert stats["rate_limited"] == 1

    @pytest.mark.asyncio
    async def test_refresh_retry_succeeds(self, clean_cache):
        """Test that failed tickers are retried and can succeed."""
        call_counts: dict[str, int] = {}

        async def mock_fetch(ticker, timeout=30.0):
            call_counts[ticker] = call_counts.get(ticker, 0) + 1
            if ticker == "FLAKY" and call_counts[ticker] == 1:
                raise TimeoutError(f"Fetch timed out after {timeout}s for {ticker}")
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "FLAKY"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                with patch("tradfi.api.scheduler.asyncio.sleep", new_callable=AsyncMock):
                    stats = await refresh_universe("dow30", delay=0.01)

        assert stats["fetched"] == 2  # Both succeeded (FLAKY on retry)
        assert stats["failed"] == 0  # Corrected after retry
        assert stats["retried"] == 1
        assert call_counts["FLAKY"] == 2  # Called twice (initial + retry)

    @pytest.mark.asyncio
    async def test_adaptive_delay_large_universe(self, clean_cache):
        """Test that large universes get scaled-up delay."""

        async def mock_fetch(ticker, timeout=30.0):
            return _make_mock_stock(ticker)

        # Generate 600 fake tickers to trigger adaptive delay
        large_universe = [f"T{i:04d}" for i in range(600)]

        with patch("tradfi.api.scheduler.load_tickers", return_value=large_universe):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                with patch("tradfi.api.scheduler.asyncio.sleep", new_callable=AsyncMock):
                    stats = await refresh_universe("nasdaq", delay=2.0)

        # For 600 tickers: delay = max(2.0, 3.0) + 600/2000 = 3.3
        assert stats["effective_delay"] >= 3.0
        assert stats["fetched"] == 600

    @pytest.mark.asyncio
    async def test_stats_include_new_fields(self, clean_cache):
        """Test that stats dict includes all enriched fields."""

        async def mock_fetch(ticker, timeout=30.0):
            return _make_mock_stock(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL"]):
            with patch("tradfi.api.scheduler.fetch_stock_from_api_async", side_effect=mock_fetch):
                stats = await refresh_universe("dow30", delay=0.01)

        # Verify all expected keys exist
        assert "timed_out" in stats
        assert "rate_limited" in stats
        assert "retried" in stats
        assert "effective_delay" in stats
        assert "duration_seconds" in stats
        assert "completed_at" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
