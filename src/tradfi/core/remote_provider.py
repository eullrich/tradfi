"""Remote data provider that fetches from TradFi API."""

from __future__ import annotations

from typing import Optional

import httpx

from tradfi.models.stock import (
    BuybackInfo,
    DividendInfo,
    FairValueEstimates,
    FinancialHealth,
    GrowthMetrics,
    ProfitabilityMetrics,
    Stock,
    TechnicalIndicators,
    ValuationMetrics,
)


class RemoteDataProvider:
    """Fetches stock data from a remote TradFi API server."""

    def __init__(self, api_url: str, timeout: float = 30.0):
        """Initialize the remote data provider.

        Args:
            api_url: Base URL of the TradFi API (e.g., https://deepvalue.up.railway.app)
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def fetch_stock(self, ticker: str) -> Optional[Stock]:
        """Fetch stock data from the remote API.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Stock object or None if not found/error
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.api_url}/api/v1/stocks/{ticker}")

            if response.status_code == 200:
                data = response.json()
                return self._schema_to_stock(data)
            elif response.status_code == 404:
                return None
            else:
                return None
        except httpx.RequestError:
            return None

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
