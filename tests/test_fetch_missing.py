"""Tests for batch stock fetching with automatic yfinance fallback.

Verifies that fetch_stocks_batch uses implicit semantics:
  - Specific tickers: cache first, then yfinance for missing
  - tickers=None: cache-only (all cached stocks)
"""

import os
import tempfile
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

# Set up test database BEFORE importing cache modules (they read env at import time)
_TEST_DB_DIR = tempfile.mkdtemp()
_TEST_DB_PATH = os.path.join(_TEST_DB_DIR, "test_fetch_missing.db")
os.environ["TRADFI_DB_PATH"] = _TEST_DB_PATH
os.environ["TRADFI_DATA_DIR"] = _TEST_DB_DIR
os.environ["TRADFI_CONFIG_PATH"] = os.path.join(_TEST_DB_DIR, "config.json")

from tradfi.core.data import fetch_stocks_batch  # noqa: E402
from tradfi.core.remote_provider import RemoteDataProvider  # noqa: E402
from tradfi.models.stock import (  # noqa: E402
    BuybackInfo,
    DividendInfo,
    FinancialHealth,
    GrowthMetrics,
    ProfitabilityMetrics,
    Stock,
    TechnicalIndicators,
    ValuationMetrics,
)
from tradfi.utils.cache import cache_stock_data, clear_cache  # noqa: E402


def _make_stock(ticker: str, sector: str = "Technology") -> Stock:
    """Create a minimal Stock for testing."""
    return Stock(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=sector,
        current_price=100.0,
        valuation=ValuationMetrics(),
        profitability=ProfitabilityMetrics(),
        financial_health=FinancialHealth(),
        growth=GrowthMetrics(),
        dividends=DividendInfo(),
        technical=TechnicalIndicators(),
        buyback=BuybackInfo(),
    )


def _make_stock_dict(ticker: str, sector: str = "Technology") -> dict:
    """Create a stock data dict suitable for cache_stock_data()."""
    stock = _make_stock(ticker, sector)
    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "sector": stock.sector,
        "industry": stock.industry,
        "current_price": stock.current_price,
        "currency": stock.currency,
        "asset_type": stock.asset_type,
        "valuation": asdict(stock.valuation),
        "profitability": asdict(stock.profitability),
        "financial_health": asdict(stock.financial_health),
        "growth": asdict(stock.growth),
        "dividends": asdict(stock.dividends),
        "technical": asdict(stock.technical),
        "fair_value": asdict(stock.fair_value),
        "buyback": asdict(stock.buyback),
        "etf": asdict(stock.etf),
    }


@pytest.fixture(autouse=True)
def clean_test_cache():
    """Clear the test cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# 1. TestFetchStocksBatch — core data layer implicit semantics
# ---------------------------------------------------------------------------


class TestFetchStocksBatch:
    """Test fetch_stocks_batch with implicit fetch-missing semantics."""

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_specific_tickers_fetches_uncached(self, mock_api):
        """Specific tickers: cached ones from cache, missing ones from yfinance."""
        cache_stock_data("AAPL", _make_stock_dict("AAPL"))
        mock_api.return_value = _make_stock("GOOGL")

        result = fetch_stocks_batch(["AAPL", "GOOGL"])

        assert "AAPL" in result
        assert "GOOGL" in result
        mock_api.assert_called_once_with("GOOGL")

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_none_tickers_does_not_call_yfinance(self, mock_api):
        """tickers=None returns all cached stocks without hitting yfinance."""
        cache_stock_data("AAPL", _make_stock_dict("AAPL"))

        result = fetch_stocks_batch(tickers=None)

        mock_api.assert_not_called()
        assert "AAPL" in result

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_empty_list_does_not_call_yfinance(self, mock_api):
        """Empty list returns empty dict without hitting yfinance."""
        result = fetch_stocks_batch([])

        mock_api.assert_not_called()
        assert result == {}

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_only_fetches_missing_tickers(self, mock_api):
        """fetch_stock_from_api is only called for tickers NOT in cache."""
        cache_stock_data("AAPL", _make_stock_dict("AAPL"))
        cache_stock_data("MSFT", _make_stock_dict("MSFT"))
        mock_api.return_value = _make_stock("GOOGL")

        result = fetch_stocks_batch(["AAPL", "MSFT", "GOOGL"])

        assert len(result) == 3
        mock_api.assert_called_once_with("GOOGL")

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_multiple_uncached(self, mock_api):
        """Multiple missing tickers are each fetched from yfinance."""
        cache_stock_data("AAPL", _make_stock_dict("AAPL"))
        mock_api.side_effect = lambda t: _make_stock(t)

        result = fetch_stocks_batch(["AAPL", "GOOGL", "AMZN", "NFLX"])

        assert len(result) == 4
        assert mock_api.call_count == 3  # GOOGL, AMZN, NFLX

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_handles_none_return(self, mock_api):
        """If fetch_stock_from_api returns None, ticker is skipped."""
        cache_stock_data("AAPL", _make_stock_dict("AAPL"))
        mock_api.return_value = None

        result = fetch_stocks_batch(["AAPL", "FAIL"])

        assert "AAPL" in result
        assert "FAIL" not in result

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_handles_exception(self, mock_api):
        """If fetch_stock_from_api raises, ticker is skipped."""
        cache_stock_data("AAPL", _make_stock_dict("AAPL"))
        mock_api.side_effect = Exception("Network error")

        result = fetch_stocks_batch(["AAPL", "ERROR"])

        assert "AAPL" in result
        assert "ERROR" not in result

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_partial_failure(self, mock_api):
        """Some missing tickers fail, others succeed."""
        cache_stock_data("CACHED", _make_stock_dict("CACHED"))

        def mock_fetch(ticker):
            if ticker == "FAIL":
                return None
            if ticker == "ERROR":
                raise Exception("Timeout")
            return _make_stock(ticker)

        mock_api.side_effect = mock_fetch

        result = fetch_stocks_batch(["CACHED", "OK1", "FAIL", "ERROR", "OK2"])

        assert "CACHED" in result
        assert "OK1" in result
        assert "OK2" in result
        assert "FAIL" not in result
        assert "ERROR" not in result

    @patch("tradfi.core.data.fetch_stock_from_api")
    def test_all_cached_no_yfinance_call(self, mock_api):
        """When all requested tickers are cached, yfinance is not called."""
        cache_stock_data("AAPL", _make_stock_dict("AAPL"))
        cache_stock_data("MSFT", _make_stock_dict("MSFT"))

        result = fetch_stocks_batch(["AAPL", "MSFT"])

        mock_api.assert_not_called()
        assert len(result) == 2


# ---------------------------------------------------------------------------
# 2. TestBatchEndpoint — API router layer
# ---------------------------------------------------------------------------


class TestBatchEndpoint:
    """Test POST /api/v1/stocks/batch calls fetch_stocks_batch."""

    @patch("tradfi.api.routers.stocks.fetch_stocks_batch")
    def test_batch_forwards_tickers(self, mock_batch):
        """POST /batch forwards tickers to fetch_stocks_batch."""
        from fastapi.testclient import TestClient

        from tradfi.api.main import app

        client = TestClient(app)

        mock_batch.return_value = {}
        client.post("/api/v1/stocks/batch", json=["AAPL", "GOOGL"])

        mock_batch.assert_called_once_with(["AAPL", "GOOGL"])


# ---------------------------------------------------------------------------
# 3. TestRemoteProviderBatch — client HTTP layer
# ---------------------------------------------------------------------------


class TestRemoteProviderBatch:
    """Test RemoteDataProvider batch fetch behavior."""

    @patch("httpx.Client")
    def test_batch_uses_180s_timeout(self, mock_client_cls):
        """Batch requests use 180s timeout to allow yfinance fetches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider = RemoteDataProvider(api_url="http://localhost:8000")
        provider._fetch_stocks_batch_single(["AAPL"])

        mock_client_cls.assert_called_once_with(timeout=180.0)

    @patch("httpx.Client")
    def test_batch_sends_no_query_params(self, mock_client_cls):
        """Batch POST sends no extra query params."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider = RemoteDataProvider(api_url="http://localhost:8000")
        provider._fetch_stocks_batch_single(["AAPL"])

        call_kwargs = mock_client.post.call_args
        # No params kwarg should be passed
        assert "params" not in call_kwargs.kwargs


# ---------------------------------------------------------------------------
# 4. TestTUIFetchStockData — TUI uses correct fetch methods
# ---------------------------------------------------------------------------


class TestTUIFetchStockData:
    """Test TUI's _fetch_stock_data uses the right provider method."""

    def _make_app_stub(self, selected_universes, selected_categories=None):
        """Create a minimal stub with attributes _fetch_stock_data reads."""
        stub = MagicMock()
        stub.selected_universes = selected_universes
        stub.selected_categories = selected_categories or set()
        stub.remote_provider = MagicMock(spec=RemoteDataProvider)
        stub.remote_provider.fetch_all_stocks.return_value = {
            "AAPL": _make_stock("AAPL"),
        }
        stub.remote_provider.fetch_stocks_batch.return_value = {
            "AAPL": _make_stock("AAPL"),
        }
        stub.call_from_thread = MagicMock()
        return stub

    def test_specific_universe_calls_batch(self):
        """When a universe is selected, fetch_stocks_batch is called."""
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes={"dow30"})
        ScreenerApp._fetch_stock_data(stub)

        stub.remote_provider.fetch_stocks_batch.assert_called_once()
        # No fetch_missing kwarg — implicit semantics
        call_args = stub.remote_provider.fetch_stocks_batch.call_args
        assert call_args.kwargs == {}

    def test_all_universes_uses_fetch_all(self):
        """When no universe is selected, fetch_all_stocks is used (cache-only)."""
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes=set())
        ScreenerApp._fetch_stock_data(stub)

        stub.remote_provider.fetch_all_stocks.assert_called_once()
        stub.remote_provider.fetch_stocks_batch.assert_not_called()

    def test_category_filter_calls_batch(self):
        """Category filter with no universe uses fetch_stocks_batch."""
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes=set(), selected_categories={"REITs"})
        ScreenerApp._fetch_stock_data(stub)

        stub.remote_provider.fetch_stocks_batch.assert_called_once()
        call_args = stub.remote_provider.fetch_stocks_batch.call_args
        assert call_args.kwargs == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
