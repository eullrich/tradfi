"""Remote data provider that fetches from TradFi API."""

from __future__ import annotations

import json
from typing import Optional

import httpx

from tradfi.models.stock import (
    BuybackInfo,
    DividendInfo,
    FairValueEstimates,
    FinancialHealth,
    GrowthMetrics,
    ProfitabilityMetrics,
    QuarterlyData,
    QuarterlyTrends,
    Stock,
    TechnicalIndicators,
    ValuationMetrics,
)


class RemoteDataProvider:
    """Fetches stock data from a remote TradFi API server."""

    def __init__(self, api_url: str, timeout: float = 30.0, admin_key: str | None = None):
        """Initialize the remote data provider.

        Args:
            api_url: Base URL of the TradFi API (e.g., https://deepvalue.up.railway.app)
            timeout: Request timeout in seconds
            admin_key: Optional admin API key for cache/refresh operations
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.admin_key = admin_key

    def _admin_headers(self) -> dict[str, str]:
        """Get headers for admin operations."""
        if self.admin_key:
            return {"X-Admin-Key": self.admin_key}
        return {}

    def fetch_stock(self, ticker: str, cache_only: bool = True) -> Optional[Stock]:
        """Fetch stock data from the remote API.

        Args:
            ticker: Stock ticker symbol
            cache_only: Only return cached data, don't trigger yfinance calls (default True)

        Returns:
            Stock object or None if not found/error
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.api_url}/api/v1/stocks/{ticker}",
                    params={"cache_only": str(cache_only).lower()},
                )

            if response.status_code == 200:
                data = response.json()
                return self._schema_to_stock(data)
            elif response.status_code == 404:
                return None
            else:
                return None
        except (httpx.RequestError, json.JSONDecodeError):
            return None

    def fetch_all_stocks(self) -> dict[str, Stock]:
        """Fetch all cached stocks in a single request.

        This is optimized for bulk loading - much faster than individual requests.

        Returns:
            Dict mapping ticker to Stock object.
        """
        try:
            with httpx.Client(timeout=60.0) as client:  # Longer timeout for bulk
                response = client.get(f"{self.api_url}/api/v1/stocks/batch/all")

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    result: dict[str, Stock] = {}
                    for ticker, stock_data in data.items():
                        try:
                            result[ticker] = self._schema_to_stock(stock_data)
                        except Exception:
                            pass  # Skip stocks that fail deserialization
                    return result
            return {}
        except (httpx.RequestError, json.JSONDecodeError):
            return {}

    def fetch_stocks_batch(self, tickers: list[str]) -> dict[str, Stock]:
        """Fetch multiple stocks by ticker in a single request.

        The server automatically fetches uncached tickers from yfinance,
        so this may take longer for cold caches.

        For large ticker lists (>500), requests are chunked to avoid
        server-side payload limits and SQLite parameter limits.

        Args:
            tickers: List of ticker symbols to fetch.

        Returns:
            Dict mapping ticker to Stock object. Missing tickers are omitted.
        """
        if not tickers:
            return {}

        # Chunk large requests to avoid payload/SQL parameter limits
        CHUNK_SIZE = 500
        if len(tickers) <= CHUNK_SIZE:
            return self._fetch_stocks_batch_single(tickers)

        result: dict[str, Stock] = {}
        for i in range(0, len(tickers), CHUNK_SIZE):
            chunk = tickers[i : i + CHUNK_SIZE]
            result.update(self._fetch_stocks_batch_single(chunk))
        return result

    def _fetch_stocks_batch_single(self, tickers: list[str]) -> dict[str, Stock]:
        """Fetch a single batch of stocks (internal helper)."""
        try:
            with httpx.Client(timeout=180.0) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/stocks/batch",
                    json=tickers,
                )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    result: dict[str, Stock] = {}
                    for ticker, stock_data in data.items():
                        try:
                            result[ticker] = self._schema_to_stock(stock_data)
                        except Exception:
                            pass  # Skip stocks that fail deserialization
                    return result
            return {}
        except (httpx.RequestError, json.JSONDecodeError):
            return {}

    def fetch_quarterly(self, ticker: str, periods: int = 8) -> Optional[QuarterlyTrends]:
        """Fetch quarterly financial data from the remote API.

        Args:
            ticker: Stock ticker symbol
            periods: Number of quarters to fetch (default 8)

        Returns:
            QuarterlyTrends object or None if not found/error
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.api_url}/api/v1/stocks/{ticker}/quarterly", params={"periods": periods}
                )

            if response.status_code == 200:
                data = response.json()
                return self._schema_to_quarterly_trends(data)
            else:
                return None
        except (httpx.RequestError, json.JSONDecodeError):
            return None

    def _schema_to_quarterly_trends(self, data: dict) -> QuarterlyTrends:
        """Convert API response schema to QuarterlyTrends dataclass."""
        quarters = []
        for q_data in data.get("quarters", []):
            quarters.append(
                QuarterlyData(
                    quarter=q_data.get("quarter", ""),
                    revenue=q_data.get("revenue"),
                    net_income=q_data.get("net_income"),
                    gross_profit=q_data.get("gross_profit"),
                    operating_income=q_data.get("operating_income"),
                    gross_margin=q_data.get("gross_margin"),
                    operating_margin=q_data.get("operating_margin"),
                    net_margin=q_data.get("net_margin"),
                    eps=q_data.get("eps"),
                    free_cash_flow=q_data.get("free_cash_flow"),
                    pe_ratio=q_data.get("pe_ratio"),
                    peg_ratio=q_data.get("peg_ratio"),
                    book_value_per_share=q_data.get("book_value_per_share"),
                    pb_ratio=q_data.get("pb_ratio"),
                    price_at_quarter_end=q_data.get("price_at_quarter_end"),
                    market_cap=q_data.get("market_cap"),
                )
            )
        return QuarterlyTrends(quarters=quarters)

    def _schema_to_stock(self, data: dict) -> Stock:
        """Convert API response schema to Stock dataclass."""
        return Stock(
            ticker=data.get("ticker", ""),
            name=data.get("name"),
            sector=data.get("sector"),
            industry=data.get("industry"),
            current_price=data.get("current_price"),
            currency=data.get("currency", "USD"),
            valuation=self._parse_valuation(data.get("valuation", {})),
            profitability=self._parse_profitability(data.get("profitability", {})),
            financial_health=self._parse_financial_health(data.get("financial_health", {})),
            growth=self._parse_growth(data.get("growth", {})),
            dividends=self._parse_dividends(data.get("dividends", {})),
            technical=self._parse_technical(data.get("technical", {})),
            fair_value=self._parse_fair_value(data.get("fair_value", {})),
            buyback=self._parse_buyback(data.get("buyback", {})),
            eps=data.get("eps"),
            book_value_per_share=data.get("book_value_per_share"),
            shares_outstanding=data.get("shares_outstanding"),
            operating_income=data.get("operating_income"),
        )

    def _parse_valuation(self, data: dict) -> ValuationMetrics:
        return ValuationMetrics(
            pe_trailing=data.get("pe_trailing"),
            pe_forward=data.get("pe_forward"),
            pb_ratio=data.get("pb_ratio"),
            ps_ratio=data.get("ps_ratio"),
            peg_ratio=data.get("peg_ratio"),
            ev_ebitda=data.get("ev_ebitda"),
            market_cap=data.get("market_cap"),
            enterprise_value=data.get("enterprise_value"),
        )

    def _parse_profitability(self, data: dict) -> ProfitabilityMetrics:
        return ProfitabilityMetrics(
            gross_margin=data.get("gross_margin"),
            operating_margin=data.get("operating_margin"),
            net_margin=data.get("net_margin"),
            roe=data.get("roe"),
            roa=data.get("roa"),
        )

    def _parse_financial_health(self, data: dict) -> FinancialHealth:
        return FinancialHealth(
            current_ratio=data.get("current_ratio"),
            quick_ratio=data.get("quick_ratio"),
            debt_to_equity=data.get("debt_to_equity"),
            debt_to_assets=data.get("debt_to_assets"),
            interest_coverage=data.get("interest_coverage"),
            free_cash_flow=data.get("free_cash_flow"),
            operating_cash_flow=data.get("operating_cash_flow"),
            total_debt=data.get("total_debt"),
            total_cash=data.get("total_cash"),
            net_income=data.get("net_income"),
            ebitda=data.get("ebitda"),
        )

    def _parse_growth(self, data: dict) -> GrowthMetrics:
        return GrowthMetrics(
            revenue_growth_yoy=data.get("revenue_growth_yoy"),
            earnings_growth_yoy=data.get("earnings_growth_yoy"),
            eps_growth_5y=data.get("eps_growth_5y"),
        )

    def _parse_dividends(self, data: dict) -> DividendInfo:
        return DividendInfo(
            dividend_yield=data.get("dividend_yield"),
            dividend_rate=data.get("dividend_rate"),
            payout_ratio=data.get("payout_ratio"),
            ex_dividend_date=data.get("ex_dividend_date"),
            dividend_frequency=data.get("dividend_frequency"),
            trailing_annual_dividend_rate=data.get("trailing_annual_dividend_rate"),
            five_year_avg_dividend_yield=data.get("five_year_avg_dividend_yield"),
            last_dividend_value=data.get("last_dividend_value"),
            last_dividend_date=data.get("last_dividend_date"),
        )

    def _parse_technical(self, data: dict) -> TechnicalIndicators:
        return TechnicalIndicators(
            rsi_14=data.get("rsi_14"),
            ma_50=data.get("ma_50"),
            ma_200=data.get("ma_200"),
            price_vs_ma_50_pct=data.get("price_vs_ma_50_pct"),
            price_vs_ma_200_pct=data.get("price_vs_ma_200_pct"),
            high_52w=data.get("high_52w"),
            low_52w=data.get("low_52w"),
            pct_from_52w_high=data.get("pct_from_52w_high"),
            pct_from_52w_low=data.get("pct_from_52w_low"),
            return_1m=data.get("return_1m"),
            return_6m=data.get("return_6m"),
            return_1y=data.get("return_1y"),
        )

    def _parse_fair_value(self, data: dict) -> FairValueEstimates:
        return FairValueEstimates(
            graham_number=data.get("graham_number"),
            dcf_value=data.get("dcf_value"),
            pe_fair_value=data.get("pe_fair_value"),
            epv_value=data.get("epv_value"),
            margin_of_safety_pct=data.get("margin_of_safety_pct"),
        )

    def _parse_buyback(self, data: dict) -> BuybackInfo:
        return BuybackInfo(
            insider_ownership_pct=data.get("insider_ownership_pct"),
            institutional_ownership_pct=data.get("institutional_ownership_pct"),
            fcf_yield_pct=data.get("fcf_yield_pct"),
            cash_per_share=data.get("cash_per_share"),
            shares_outstanding=data.get("shares_outstanding"),
            shares_outstanding_prior=data.get("shares_outstanding_prior"),
        )

    # ==================== Lists ====================

    def get_lists(self) -> list[str]:
        """Get all saved list names."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/lists")
            if response.status_code == 200:
                return response.json()
            return []
        except (httpx.RequestError, json.JSONDecodeError):
            return []

    def get_list(self, name: str) -> dict | None:
        """Get a saved list by name with all items and notes."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/lists/{name}")
            if response.status_code == 200:
                return response.json()
            return None
        except (httpx.RequestError, json.JSONDecodeError):
            return None

    def create_list(self, name: str, tickers: list[str]) -> bool:
        """Create a new stock list."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/lists", json={"name": name, "tickers": tickers}
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def delete_list(self, name: str) -> bool:
        """Delete a saved list."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(f"{self.api_url}/api/v1/lists/{name}")
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def add_to_list(self, name: str, ticker: str) -> bool:
        """Add a ticker to a list."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/lists/{name}/items", json={"ticker": ticker.upper()}
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def remove_from_list(self, name: str, ticker: str) -> bool:
        """Remove a ticker from a list."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(
                    f"{self.api_url}/api/v1/lists/{name}/items/{ticker.upper()}"
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def set_item_note(
        self,
        name: str,
        ticker: str,
        notes: str | None = None,
        thesis: str | None = None,
        entry_price: float | None = None,
        target_price: float | None = None,
    ) -> bool:
        """Update notes for a list item."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.put(
                    f"{self.api_url}/api/v1/lists/{name}/items/{ticker.upper()}/notes",
                    json={
                        "notes": notes,
                        "thesis": thesis,
                        "entry_price": entry_price,
                        "target_price": target_price,
                    },
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    # ==================== Position/Portfolio ====================

    def set_position(
        self,
        list_name: str,
        ticker: str,
        shares: float | None = None,
        entry_price: float | None = None,
        target_price: float | None = None,
        thesis: str | None = None,
    ) -> bool:
        """Set position data for a list item.

        Args:
            list_name: Name of the list
            ticker: Stock ticker symbol
            shares: Number of shares held
            entry_price: Entry price per share
            target_price: Target price
            thesis: Investment thesis

        Returns:
            True if successful
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.put(
                    f"{self.api_url}/api/lists/{list_name}/items/{ticker.upper()}/position",
                    json={
                        "shares": shares,
                        "entry_price": entry_price,
                        "target_price": target_price,
                        "thesis": thesis,
                    },
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def get_position(self, list_name: str, ticker: str) -> dict | None:
        """Get position data for a list item.

        Args:
            list_name: Name of the list
            ticker: Stock ticker symbol

        Returns:
            Position data dict or None
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.api_url}/api/lists/{list_name}/items/{ticker.upper()}/position"
                )
            if response.status_code == 200:
                return response.json()
            return None
        except (httpx.RequestError, json.JSONDecodeError):
            return None

    def clear_position(self, list_name: str, ticker: str) -> bool:
        """Clear position data for a list item.

        Args:
            list_name: Name of the list
            ticker: Stock ticker symbol

        Returns:
            True if successful
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(
                    f"{self.api_url}/api/lists/{list_name}/items/{ticker.upper()}/position"
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def get_portfolio(self, list_name: str) -> dict | None:
        """Get full portfolio view with P&L calculations.

        Args:
            list_name: Name of the list

        Returns:
            Portfolio data dict with items and totals, or None
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/lists/{list_name}/portfolio")
            if response.status_code == 200:
                return response.json()
            return None
        except (httpx.RequestError, json.JSONDecodeError):
            return None

    def has_positions(self, list_name: str) -> bool:
        """Check if a list has any position data.

        Args:
            list_name: Name of the list

        Returns:
            True if list has positions
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/lists/{list_name}/has-positions")
            if response.status_code == 200:
                data = response.json()
                return data.get("has_positions", False)
            return False
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    # ==================== Watchlist ====================

    def get_watchlist(self) -> list[dict]:
        """Get all watchlist items."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/watchlist")
            if response.status_code == 200:
                return response.json()
            return []
        except (httpx.RequestError, json.JSONDecodeError):
            return []

    def add_to_watchlist(self, ticker: str, notes: str | None = None) -> bool:
        """Add a ticker to the watchlist."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/watchlist", json={"ticker": ticker.upper()}
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def remove_from_watchlist(self, ticker: str) -> bool:
        """Remove a ticker from the watchlist."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(f"{self.api_url}/api/v1/watchlist/{ticker.upper()}")
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def update_watchlist_notes(self, ticker: str, notes: str) -> bool:
        """Update notes for a watchlist item."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.put(
                    f"{self.api_url}/api/v1/watchlist/{ticker.upper()}/notes", json={"notes": notes}
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    # ==================== Categories ====================

    def get_categories(self) -> list[dict]:
        """Get all categories."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/lists/categories")
            if response.status_code == 200:
                return response.json()
            return []
        except (httpx.RequestError, json.JSONDecodeError):
            return []

    def create_category(self, name: str, icon: str | None = None) -> bool:
        """Create a new category."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/lists/categories", json={"name": name, "icon": icon}
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def delete_category(self, category_id: int) -> bool:
        """Delete a category."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(f"{self.api_url}/api/v1/lists/categories/{category_id}")
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def add_list_to_category(self, list_name: str, category_id: int) -> bool:
        """Add a list to a category."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/lists/categories/{category_id}/lists/{list_name}"
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def remove_list_from_category(self, list_name: str, category_id: int) -> bool:
        """Remove a list from a category."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(
                    f"{self.api_url}/api/v1/lists/categories/{category_id}/lists/{list_name}"
                )
            return response.status_code == 200
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    # ==================== Cache ====================

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/cache/stats")
            if response.status_code == 200:
                return response.json()
            return {}
        except (httpx.RequestError, json.JSONDecodeError):
            return {}

    def get_sectors(self, tickers: list[str] | None = None) -> list[tuple[str, int]]:
        """Get sectors with their stock counts from cache.

        Args:
            tickers: Optional list of tickers to filter by. If not provided,
                     returns all sectors from cache.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Check explicitly for None to handle empty list [] correctly
                params = {"tickers": tickers} if tickers is not None else None
                response = client.get(
                    f"{self.api_url}/api/v1/cache/sectors",
                    params=params,
                )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return [
                        (item.get("sector", "Unknown"), item.get("count", 0))
                        for item in data
                        if isinstance(item, dict)
                    ]
            return []
        except (httpx.RequestError, json.JSONDecodeError):
            return []

    def clear_cache(self) -> int:
        """Clear all cached stock data. Returns count of cleared entries.

        Requires admin_key to be set if server has TRADFI_ADMIN_KEY configured.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/cache/clear",
                    headers=self._admin_headers(),
                )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    # Extract count from message like "Cleared 500 cached entries"
                    msg = data.get("message", "")
                    try:
                        return int(msg.split()[1])
                    except (IndexError, ValueError):
                        return 0
            return 0
        except (httpx.RequestError, json.JSONDecodeError):
            return 0

    def trigger_refresh(self, universe: str) -> dict:
        """Trigger a refresh for a universe. Returns status dict.

        Requires admin_key to be set if server has TRADFI_ADMIN_KEY configured.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v1/refresh/{universe}",
                    headers=self._admin_headers(),
                )
            if response.status_code == 200:
                return response.json()
            elif response.status_code in (401, 403):
                return {"error": "Admin key required or invalid"}
            return {"error": f"Status {response.status_code}"}
        except httpx.RequestError as e:
            return {"error": str(e)}

    def get_refresh_status(self) -> dict:
        """Get current refresh status (running job info)."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/refresh/status")
            if response.status_code == 200:
                return response.json()
            return {}
        except (httpx.RequestError, json.JSONDecodeError):
            return {}

    def get_universe_stats(self) -> list[dict]:
        """Get cache statistics for all universes."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/refresh/universes")
            if response.status_code == 200:
                return response.json()
            return []
        except (httpx.RequestError, json.JSONDecodeError):
            return []

    def get_refresh_health(self) -> dict:
        """Get refresh system health and next scheduled time."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/refresh/health")
            if response.status_code == 200:
                return response.json()
            return {}
        except (httpx.RequestError, json.JSONDecodeError):
            return {}
