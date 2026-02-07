"""Tests for universe loading and stock data fetching.

Verifies that all universes load tickers correctly, the TUI calls
the right API path for each selection type, and large ticker lists
are chunked to stay under SQLite parameter limits.
"""

from unittest.mock import MagicMock, patch

from tradfi.core.remote_provider import RemoteDataProvider
from tradfi.core.screener import AVAILABLE_UNIVERSES, load_tickers
from tradfi.models.stock import (
    BuybackInfo,
    DividendInfo,
    FinancialHealth,
    GrowthMetrics,
    ProfitabilityMetrics,
    Stock,
    TechnicalIndicators,
    ValuationMetrics,
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
        assert len(tickers) > 1000, (
            f"russell2000 has only {len(tickers)} tickers, expected >1000"
        )

    def test_nasdaq_has_substantial_tickers(self):
        """NASDAQ composite should have >2000 tickers."""
        tickers = load_tickers("nasdaq")
        assert len(tickers) > 2000, (
            f"nasdaq has only {len(tickers)} tickers, expected >2000"
        )

    def test_sp500_has_expected_count(self):
        """S&P 500 should have ~500 tickers."""
        tickers = load_tickers("sp500")
        assert 450 < len(tickers) < 550, (
            f"sp500 has {len(tickers)} tickers, expected ~500"
        )

    def test_dow30_has_expected_count(self):
        """Dow 30 should have ~30 tickers."""
        tickers = load_tickers("dow30")
        assert 25 < len(tickers) < 40, (
            f"dow30 has {len(tickers)} tickers, expected ~30"
        )

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

        stub = self._make_app_stub(
            selected_universes=set(), selected_categories={"REITs"}
        )
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
            assert len(chunk) <= 500, (
                f"Chunk has {len(chunk)} tickers, exceeds 500 limit"
            )

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
        def side_effect(chunk):
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
