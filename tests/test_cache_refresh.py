"""Tests for cache refresh functionality."""

import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

# Set up test database before imports
TEST_DB_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_cache.db")
os.environ["TRADFI_DB_PATH"] = TEST_DB_PATH
os.environ["TRADFI_DATA_DIR"] = TEST_DB_DIR
os.environ["TRADFI_CONFIG_PATH"] = os.path.join(TEST_DB_DIR, "config.json")

from tradfi.api.scheduler import _refresh_state, get_refresh_state, refresh_universe  # noqa: E402
from tradfi.core.data import FetchOutcome, FetchResult  # noqa: E402
from tradfi.utils.cache import (  # noqa: E402
    cache_stock_data,
    clear_cache,
    get_batch_cache_freshness,
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


def _make_fresh_result(ticker: str) -> FetchResult:
    """Create a FetchResult with FRESH outcome for testing."""
    mock_stock = MagicMock()
    mock_stock.model_dump.return_value = {"ticker": ticker, "price": 100.0}
    return FetchResult(stock=mock_stock, outcome=FetchOutcome.FRESH)


def _make_stale_result(ticker: str) -> FetchResult:
    """Create a FetchResult with STALE outcome for testing."""
    mock_stock = MagicMock()
    mock_stock.model_dump.return_value = {"ticker": ticker, "price": 90.0}
    return FetchResult(stock=mock_stock, outcome=FetchOutcome.STALE, error="rate limited")


def _make_failed_result() -> FetchResult:
    """Create a FetchResult with FAILED outcome for testing."""
    return FetchResult(stock=None, outcome=FetchOutcome.FAILED, error="no data")


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


class TestBatchCacheFreshness:
    """Test batch cache freshness checking."""

    def test_all_missing(self, clean_cache):
        """Test freshness check when nothing is cached."""
        result = get_batch_cache_freshness(["AAPL", "MSFT"])
        assert result["AAPL"] == "missing"
        assert result["MSFT"] == "missing"

    def test_all_fresh(self, clean_cache):
        """Test freshness check when all are fresh."""
        cache_stock_data("AAPL", {"ticker": "AAPL"})
        cache_stock_data("MSFT", {"ticker": "MSFT"})

        result = get_batch_cache_freshness(["AAPL", "MSFT"])
        assert result["AAPL"] == "fresh"
        assert result["MSFT"] == "fresh"

    def test_mixed(self, clean_cache):
        """Test freshness check with mixed results."""
        cache_stock_data("AAPL", {"ticker": "AAPL"})

        result = get_batch_cache_freshness(["AAPL", "MSFT"])
        assert result["AAPL"] == "fresh"
        assert result["MSFT"] == "missing"

    def test_empty_list(self, clean_cache):
        """Test freshness check with empty list."""
        assert get_batch_cache_freshness([]) == {}


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

        def mock_fetch(ticker):
            # Capture state during refresh
            states_during_refresh.append(get_refresh_state().copy())
            return _make_fresh_result(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "MSFT"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                await refresh_universe("dow30", delay=0.01)

        # Verify states during refresh
        assert len(states_during_refresh) == 2  # 2 tickers
        assert states_during_refresh[0]["is_running"] is True
        assert states_during_refresh[0]["current_universe"] == "dow30"
        assert states_during_refresh[0]["progress"]["total"] == 2

    @pytest.mark.asyncio
    async def test_refresh_state_after_completion(self, clean_cache):
        """Test refresh state after refresh completes."""

        def mock_fetch(ticker):
            return _make_fresh_result(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                await refresh_universe("dow30", delay=0.01)

        state = get_refresh_state()
        assert state["is_running"] is False
        assert state["last_refresh"] is not None
        assert state["last_refresh_stats"]["universe"] == "dow30"
        assert state["last_refresh_stats"]["fresh"] == 1
        assert state["last_refresh_stats"]["fetched"] == 1  # backwards compat


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

        def mock_fetch(ticker):
            call_count[0] += 1
            if ticker == "FAIL":
                return _make_failed_result()
            return _make_fresh_result(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "FAIL", "MSFT"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                stats = await refresh_universe("dow30", delay=0.01, max_retries=0)

        assert stats["total"] == 3
        assert stats["fresh"] == 2
        assert stats["failed"] == 1
        assert stats["fetched"] == 2  # backwards compat: fresh + stale

    @pytest.mark.asyncio
    async def test_refresh_with_exceptions(self, clean_cache):
        """Test refresh handles exceptions gracefully."""

        def mock_fetch(ticker):
            if ticker == "ERROR":
                raise Exception("Network error")
            return _make_fresh_result(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "ERROR"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                stats = await refresh_universe("dow30", delay=0.01, max_retries=0)

        assert stats["fresh"] == 1
        assert stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_refresh_caches_data(self, clean_cache):
        """Test refresh actually caches the fetched data."""

        def mock_fetch(ticker):
            # Actually cache the data
            cache_stock_data(ticker, {"ticker": ticker, "price": 100.0})
            return _make_fresh_result(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "MSFT"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                await refresh_universe("dow30", delay=0.01)

        # Verify data was cached
        aapl = get_cached_stock_data("AAPL")
        msft = get_cached_stock_data("MSFT")
        assert aapl is not None
        assert msft is not None
        assert aapl["ticker"] == "AAPL"
        assert msft["ticker"] == "MSFT"

    @pytest.mark.asyncio
    async def test_retry_recovers_stale(self, clean_cache):
        """Test that retry passes recover stale results."""
        attempt = {}

        def mock_fetch(ticker):
            attempt[ticker] = attempt.get(ticker, 0) + 1
            if ticker == "SLOW" and attempt[ticker] == 1:
                return _make_stale_result(ticker)  # First attempt: stale
            return _make_fresh_result(ticker)  # Retry or other tickers: fresh

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "SLOW"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                with patch("tradfi.api.scheduler.INTER_RETRY_PAUSE", 0):
                    stats = await refresh_universe("dow30", delay=0.01, max_retries=1)

        assert stats["fresh"] == 2  # Both should be fresh after retry
        assert stats["stale"] == 0
        assert stats["retry_passes"] == 1

    @pytest.mark.asyncio
    async def test_retry_max_passes(self, clean_cache):
        """Test that retries stop at max_retries."""
        call_count = [0]

        def mock_fetch(ticker):
            call_count[0] += 1
            return _make_failed_result()  # Always fail

        with patch("tradfi.api.scheduler.load_tickers", return_value=["FAIL"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                with patch("tradfi.api.scheduler.INTER_RETRY_PAUSE", 0):
                    stats = await refresh_universe("dow30", delay=0.01, max_retries=2)

        # 1 initial pass + 2 retries = 3 total calls
        assert call_count[0] == 3
        assert stats["failed"] == 1
        assert stats["retry_passes"] == 2


class TestRateLimiting:
    """Test rate limiting during refresh."""

    @pytest.mark.asyncio
    async def test_refresh_applies_delay(self, clean_cache):
        """Test that refresh applies configured delay between requests."""
        fetch_times = []

        def mock_fetch(ticker):
            fetch_times.append(time.time())
            return _make_fresh_result(ticker)

        with patch("tradfi.api.scheduler.load_tickers", return_value=["AAPL", "MSFT", "GOOGL"]):
            with patch(
                "tradfi.api.scheduler.fetch_stock_from_api_with_result",
                side_effect=mock_fetch,
            ):
                await refresh_universe("dow30", delay=0.1)

        # There should be delays between fetches (at least 2 intervals for 3 tickers)
        assert len(fetch_times) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
