"""Tests for universe loading and stock data fetching.

Verifies that all universes load tickers correctly, the TUI calls
the right API path for each selection type, large ticker lists
are chunked to stay under SQLite parameter limits, and the cache
round-trip works for all universe sizes.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Set up test database BEFORE importing cache modules (they read env at import time)
_TEST_DB_DIR = tempfile.mkdtemp()
_TEST_DB_PATH = os.path.join(_TEST_DB_DIR, "test_universe_cache.db")
os.environ["TRADFI_DB_PATH"] = _TEST_DB_PATH
os.environ["TRADFI_DATA_DIR"] = _TEST_DB_DIR
os.environ["TRADFI_CONFIG_PATH"] = os.path.join(_TEST_DB_DIR, "config.json")

from tradfi.core.remote_provider import RemoteDataProvider  # noqa: E402
from tradfi.core.screener import AVAILABLE_UNIVERSES, load_tickers  # noqa: E402
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
from tradfi.utils.cache import (  # noqa: E402
    cache_stock_data,
    clear_cache,
    get_all_cached_sectors,
    get_batch_cached_stocks,
)


def _make_stock(ticker: str) -> Stock:
    """Minimal stock for testing."""
    return Stock(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector="Technology",
        current_price=100.0,
        valuation=ValuationMetrics(),
        profitability=ProfitabilityMetrics(),
        financial_health=FinancialHealth(),
        growth=GrowthMetrics(),
        dividends=DividendInfo(),
        technical=TechnicalIndicators(),
        buyback=BuybackInfo(),
    )


# ---------------------------------------------------------------------------
# 1. TestLoadTickers — verify every universe file loads correctly
# ---------------------------------------------------------------------------


class TestLoadTickers:
    """Verify each universe defined in AVAILABLE_UNIVERSES loads tickers."""

    def test_all_universes_have_data_files(self):
        """Every universe in AVAILABLE_UNIVERSES must have a loadable data file."""
        for name in AVAILABLE_UNIVERSES:
            tickers = load_tickers(name)
            assert len(tickers) > 0, f"Universe '{name}' loaded 0 tickers"

    def test_russell2000_has_substantial_tickers(self):
        """Russell 2000 should have >1000 tickers."""
        tickers = load_tickers("russell2000")
        assert len(tickers) > 1000, f"russell2000 has only {len(tickers)} tickers, expected >1000"

    def test_nasdaq_has_substantial_tickers(self):
        """NASDAQ composite should have >2000 tickers."""
        tickers = load_tickers("nasdaq")
        assert len(tickers) > 2000, f"nasdaq has only {len(tickers)} tickers, expected >2000"

    def test_sp500_has_expected_count(self):
        """S&P 500 should have ~500 tickers."""
        tickers = load_tickers("sp500")
        assert 450 < len(tickers) < 550, f"sp500 has {len(tickers)} tickers, expected ~500"

    def test_dow30_has_expected_count(self):
        """Dow 30 should have ~30 tickers."""
        tickers = load_tickers("dow30")
        assert 25 < len(tickers) < 40, f"dow30 has {len(tickers)} tickers, expected ~30"

    def test_tickers_are_nonempty_strings(self):
        """Every ticker in every universe should be a non-empty string."""
        for name in AVAILABLE_UNIVERSES:
            tickers = load_tickers(name)
            for ticker in tickers:
                assert isinstance(ticker, str) and len(ticker.strip()) > 0, (
                    f"Universe '{name}' has invalid ticker: {ticker!r}"
                )

    def test_no_comment_lines_in_results(self):
        """load_tickers should strip comment lines (starting with #)."""
        for name in AVAILABLE_UNIVERSES:
            tickers = load_tickers(name)
            for ticker in tickers:
                assert not ticker.startswith("#"), (
                    f"Universe '{name}' has comment line in tickers: {ticker!r}"
                )


# ---------------------------------------------------------------------------
# 2. TestFetchStockData — verify TUI's _fetch_stock_data logic
# ---------------------------------------------------------------------------


class TestFetchStockData:
    """Verify _fetch_stock_data calls the correct remote provider method."""

    def _make_app_stub(self, selected_universes, selected_categories=None):
        """Create a minimal object with the attributes _fetch_stock_data reads."""
        stub = MagicMock()
        stub.selected_universes = selected_universes
        stub.selected_categories = selected_categories or set()
        stub.remote_provider = MagicMock(spec=RemoteDataProvider)
        stub.remote_provider.fetch_all_stocks.return_value = {
            "AAPL": _make_stock("AAPL"),
            "MSFT": _make_stock("MSFT"),
        }
        stub.remote_provider.fetch_stocks_batch.return_value = {
            "AAPL": _make_stock("AAPL"),
            "MSFT": _make_stock("MSFT"),
        }
        stub.call_from_thread = MagicMock()
        return stub

    def test_all_universes_uses_fetch_all(self):
        """When selected_universes is empty (= __all__), must use fetch_all_stocks."""
        # Import the unbound method to call it on our stub
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes=set())
        result = ScreenerApp._fetch_stock_data(stub)
        all_stocks, ticker_list = result

        stub.remote_provider.fetch_all_stocks.assert_called_once()
        stub.remote_provider.fetch_stocks_batch.assert_not_called()
        assert len(all_stocks) == 2

    def test_specific_universe_uses_batch_fetch(self):
        """When a specific universe is selected, must use fetch_stocks_batch."""
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes={"dow30"})
        result = ScreenerApp._fetch_stock_data(stub)
        all_stocks, ticker_list = result

        stub.remote_provider.fetch_stocks_batch.assert_called_once()
        stub.remote_provider.fetch_all_stocks.assert_not_called()
        # dow30 tickers should be passed to batch fetch
        called_tickers = stub.remote_provider.fetch_stocks_batch.call_args[0][0]
        assert len(called_tickers) > 20, "dow30 should send >20 tickers"

    def test_large_universe_russell2000_sends_all_tickers(self):
        """russell2000 selection must send all ~1950 tickers to batch fetch."""
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes={"russell2000"})
        ScreenerApp._fetch_stock_data(stub)

        called_tickers = stub.remote_provider.fetch_stocks_batch.call_args[0][0]
        assert len(called_tickers) > 1000, (
            f"russell2000 only sent {len(called_tickers)} tickers, expected >1000"
        )

    def test_large_universe_nasdaq_sends_all_tickers(self):
        """nasdaq selection must send all ~3149 tickers to batch fetch."""
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes={"nasdaq"})
        ScreenerApp._fetch_stock_data(stub)

        called_tickers = stub.remote_provider.fetch_stocks_batch.call_args[0][0]
        assert len(called_tickers) > 2000, (
            f"nasdaq only sent {len(called_tickers)} tickers, expected >2000"
        )

    def test_categories_with_all_universes_uses_batch(self):
        """All universes + category filter must use fetch_stocks_batch, not fetch_all."""
        from tradfi.tui.app import ScreenerApp

        stub = self._make_app_stub(selected_universes=set(), selected_categories={"REITs"})
        ScreenerApp._fetch_stock_data(stub)

        stub.remote_provider.fetch_stocks_batch.assert_called_once()
        stub.remote_provider.fetch_all_stocks.assert_not_called()


# ---------------------------------------------------------------------------
# 3. TestBatchChunking — verify RemoteProvider chunks large requests
# ---------------------------------------------------------------------------


class TestBatchChunking:
    """Verify fetch_stocks_batch chunks large ticker lists correctly."""

    def _make_provider(self):
        """Create a RemoteDataProvider with mocked HTTP calls."""
        provider = RemoteDataProvider(api_url="http://localhost:8000")
        return provider

    def _make_tickers(self, n: int) -> list[str]:
        """Generate n fake ticker symbols."""
        return [f"T{i:04d}" for i in range(n)]

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_small_batch_no_chunking(self, mock_single):
        """100 tickers should make exactly 1 call."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(100)

        provider.fetch_stocks_batch(tickers)

        assert mock_single.call_count == 1

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_500_tickers_no_chunking(self, mock_single):
        """Exactly 500 tickers should make 1 call (at the boundary)."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(500)

        provider.fetch_stocks_batch(tickers)

        assert mock_single.call_count == 1

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_501_tickers_chunks_to_two(self, mock_single):
        """501 tickers should chunk into 2 calls (500 + 1)."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(501)

        provider.fetch_stocks_batch(tickers)

        assert mock_single.call_count == 2

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_1500_tickers_chunks_to_three(self, mock_single):
        """1500 tickers should chunk into 3 calls of 500."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(1500)

        provider.fetch_stocks_batch(tickers)

        assert mock_single.call_count == 3

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_russell2000_sized_batch(self, mock_single):
        """~1950 tickers (russell2000) should chunk into 4 calls."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(1950)

        provider.fetch_stocks_batch(tickers)

        assert mock_single.call_count == 4  # 500 + 500 + 500 + 450

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_nasdaq_sized_batch(self, mock_single):
        """~3149 tickers (nasdaq) should chunk into 7 calls."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(3149)

        provider.fetch_stocks_batch(tickers)

        assert mock_single.call_count == 7  # 6*500 + 149

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_all_chunks_under_sqlite_limit(self, mock_single):
        """Every chunk passed to _fetch_stocks_batch_single must be ≤500."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(3149)

        provider.fetch_stocks_batch(tickers)

        for c in mock_single.call_args_list:
            chunk = c[0][0]  # First positional arg
            assert len(chunk) <= 500, f"Chunk has {len(chunk)} tickers, exceeds 500 limit"

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_chunking_preserves_all_tickers(self, mock_single):
        """All tickers must be sent across chunks — none dropped."""
        mock_single.return_value = {}
        provider = self._make_provider()
        tickers = self._make_tickers(1950)

        provider.fetch_stocks_batch(tickers)

        all_sent = []
        for c in mock_single.call_args_list:
            all_sent.extend(c[0][0])
        assert len(all_sent) == 1950
        assert set(all_sent) == set(tickers)

    @patch.object(RemoteDataProvider, "_fetch_stocks_batch_single")
    def test_chunked_results_merged(self, mock_single):
        """Results from all chunks must be merged into one dict."""

        def side_effect(chunk, **kwargs):
            return {t: _make_stock(t) for t in chunk[:2]}  # Return 2 per chunk

        mock_single.side_effect = side_effect
        provider = self._make_provider()
        tickers = self._make_tickers(1500)

        result = provider.fetch_stocks_batch(tickers)

        # 3 chunks, 2 results each = 6 total
        assert len(result) == 6

    def test_empty_tickers_returns_empty(self):
        """Empty ticker list should return empty dict without API calls."""
        provider = self._make_provider()
        result = provider.fetch_stocks_batch([])
        assert result == {}


# ---------------------------------------------------------------------------
# 4. TestCacheRoundTrip — verify server-side cache stores/retrieves correctly
# ---------------------------------------------------------------------------

SECTORS = ["Technology", "Healthcare", "Financial Services", "Energy", "Consumer Cyclical"]


def _make_stock_dict(ticker: str, sector: str = "Technology") -> dict:
    """Create a minimal stock data dict suitable for cache_stock_data().

    Mirrors the structure that _stock_to_dict produces, without importing
    core.data (which pulls in yfinance).
    """
    from dataclasses import asdict

    stock = Stock(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=sector,
        industry="Software",
        current_price=100.0,
        valuation=ValuationMetrics(pe_trailing=15.0, pb_ratio=1.5),
        profitability=ProfitabilityMetrics(roe=12.0),
        financial_health=FinancialHealth(),
        growth=GrowthMetrics(),
        dividends=DividendInfo(),
        technical=TechnicalIndicators(rsi_14=50.0),
        buyback=BuybackInfo(),
    )
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


class TestCacheRoundTrip:
    """Verify cache stores and retrieves stock data correctly."""

    def test_cache_and_retrieve_single_stock(self):
        """Cache one stock, retrieve it by ticker."""
        data = _make_stock_dict("AAPL")
        cache_stock_data("AAPL", data)

        result = get_batch_cached_stocks(["AAPL"])
        assert "AAPL" in result
        assert result["AAPL"]["ticker"] == "AAPL"

    def test_cache_and_retrieve_batch(self):
        """Cache 10 stocks, retrieve all 10 in one query."""
        tickers = [f"TEST{i}" for i in range(10)]
        for t in tickers:
            cache_stock_data(t, _make_stock_dict(t))

        result = get_batch_cached_stocks(tickers)
        assert len(result) == 10
        for t in tickers:
            assert t in result

    def test_batch_returns_only_cached(self):
        """Query 10 tickers when only 5 are cached — returns exactly 5."""
        cached = [f"HIT{i}" for i in range(5)]
        missing = [f"MISS{i}" for i in range(5)]
        for t in cached:
            cache_stock_data(t, _make_stock_dict(t))

        result = get_batch_cached_stocks(cached + missing)
        assert len(result) == 5
        for t in cached:
            assert t in result
        for t in missing:
            assert t not in result

    def test_get_all_cached_stocks(self):
        """get_batch_cached_stocks(None) returns all cached stocks."""
        tickers = [f"ALL{i}" for i in range(5)]
        for t in tickers:
            cache_stock_data(t, _make_stock_dict(t))

        result = get_batch_cached_stocks(None)
        assert len(result) >= 5
        for t in tickers:
            assert t in result

    def test_sectors_extracted_from_cache(self):
        """get_all_cached_sectors() returns correct sector counts."""
        # Cache 3 Tech, 2 Healthcare, 1 Energy
        for i in range(3):
            cache_stock_data(f"TECH{i}", _make_stock_dict(f"TECH{i}", "Technology"))
        for i in range(2):
            cache_stock_data(f"HC{i}", _make_stock_dict(f"HC{i}", "Healthcare"))
        cache_stock_data("OIL0", _make_stock_dict("OIL0", "Energy"))

        sectors = get_all_cached_sectors()
        sector_dict = dict(sectors)
        assert sector_dict["Technology"] == 3
        assert sector_dict["Healthcare"] == 2
        assert sector_dict["Energy"] == 1

    def test_large_batch_600_stocks(self):
        """Cache and retrieve 600 stocks — verifies SQLite handles it."""
        tickers = [f"LRG{i:04d}" for i in range(600)]
        for t in tickers:
            cache_stock_data(t, _make_stock_dict(t))

        result = get_batch_cached_stocks(tickers)
        assert len(result) == 600

    def test_dict_round_trip_preserves_fields(self):
        """Stock dict → cache → retrieve preserves key fields."""
        data = _make_stock_dict("AAPL", sector="Healthcare")
        cache_stock_data("AAPL", data)

        cached = get_batch_cached_stocks(["AAPL"])
        assert cached["AAPL"]["ticker"] == "AAPL"
        assert cached["AAPL"]["sector"] == "Healthcare"
        assert cached["AAPL"]["current_price"] == 100.0
        assert isinstance(cached["AAPL"]["valuation"], dict)
        assert cached["AAPL"]["valuation"]["pe_trailing"] == 15.0

    def test_one_bad_stock_does_not_kill_batch(self):
        """If one cached stock has corrupt JSON, others still load."""
        # Cache 2 good stocks
        cache_stock_data("GOOD1", _make_stock_dict("GOOD1"))
        cache_stock_data("GOOD2", _make_stock_dict("GOOD2"))

        # Inject a corrupt entry directly into the DB
        from tradfi.utils.cache import get_db_connection

        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO stock_cache (ticker, data, cached_at) VALUES (?, ?, ?)",
            ("BAD1", "not valid json {{{", 0),
        )
        conn.commit()
        conn.close()

        # get_batch_cached_stocks should skip the corrupt entry
        result = get_batch_cached_stocks(["GOOD1", "GOOD2", "BAD1"])
        assert "GOOD1" in result
        assert "GOOD2" in result
        assert "BAD1" not in result  # Corrupt JSON silently skipped

    def test_batch_with_malformed_stock_data(self):
        """get_batch_cached_stocks returns valid entries even with bad data nearby."""
        cache_stock_data("GOOD", _make_stock_dict("GOOD"))

        # Insert stock with valid JSON but missing required fields
        from tradfi.utils.cache import get_db_connection

        incomplete_data = json.dumps({"name": "Bad Corp", "sector": "Tech"})
        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO stock_cache (ticker, data, cached_at) VALUES (?, ?, ?)",
            ("INCOMPLETE", incomplete_data, 0),
        )
        conn.commit()
        conn.close()

        # Cache layer returns both (it doesn't validate structure, just JSON parse)
        result = get_batch_cached_stocks(["GOOD", "INCOMPLETE"])
        assert "GOOD" in result
        # INCOMPLETE is valid JSON so cache returns it — the bug is in the
        # conversion layer above (core/data.py, api/routers/stocks.py)
        # where one bad conversion kills the entire dict comprehension
        assert "INCOMPLETE" in result

    def test_cache_all_universe_ticker_counts(self):
        """Cache a stock per universe and verify batch retrieval matches."""
        # For each universe, cache one stock using the first ticker
        universe_tickers = {}
        for name in AVAILABLE_UNIVERSES:
            tickers = load_tickers(name)
            first = tickers[0]
            universe_tickers[name] = first
            cache_stock_data(first, _make_stock_dict(first, sector=name[:10]))

        # Retrieve all cached stocks
        all_tickers = list(universe_tickers.values())
        result = get_batch_cached_stocks(all_tickers)

        # Every universe's representative ticker should be present
        for name, ticker in universe_tickers.items():
            assert ticker in result, (
                f"Universe '{name}' ticker '{ticker}' not found in cache results"
            )
