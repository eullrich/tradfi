"""Data fetching from yfinance with caching and rate limiting."""

from __future__ import annotations

import time
from dataclasses import asdict

import yfinance as yf
import pandas as pd

from tradfi.models.stock import (
    Stock,
    ValuationMetrics,
    ProfitabilityMetrics,
    FinancialHealth,
    GrowthMetrics,
    DividendInfo,
    TechnicalIndicators,
    FairValueEstimates,
    BuybackInfo,
)
from tradfi.core.technical import (
    calculate_rsi,
    calculate_sma,
    calculate_price_vs_ma_pct,
    calculate_52w_metrics,
)
from tradfi.core.valuation import (
    calculate_graham_number,
    calculate_dcf_fair_value,
    calculate_pe_fair_value,
)
from tradfi.utils.cache import (
    cache_stock_data,
    get_cached_stock_data,
    get_config,
)

# Track last request time for rate limiting
_last_request_time: float = 0


def fetch_stock(ticker_symbol: str, use_cache: bool = True) -> Stock | None:
    """
    Fetch complete stock data from yfinance with caching and rate limiting.

    Args:
        ticker_symbol: Stock ticker (e.g., "AAPL")
        use_cache: Whether to use cached data (default True)

    Returns:
        Stock object with all metrics, or None if fetch failed
    """
    global _last_request_time
    ticker_symbol = ticker_symbol.upper()
    config = get_config()

    # In offline mode, only return cached data (ignore TTL)
    if config.offline_mode:
        cached = get_cached_stock_data(ticker_symbol, ignore_ttl=True)
        if cached:
            return _dict_to_stock(cached)
        return None

    # Try cache first
    if use_cache:
        cached = get_cached_stock_data(ticker_symbol)
        if cached:
            return _dict_to_stock(cached)

    # Rate limiting
    elapsed = time.time() - _last_request_time
    if elapsed < config.rate_limit_delay:
        time.sleep(config.rate_limit_delay - elapsed)

    try:
        _last_request_time = time.time()
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        if not info or "symbol" not in info:
            return None

        # Get price history for technical indicators
        history = ticker.history(period="1y")
        if history.empty:
            return None

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price is None and not history.empty:
            current_price = float(history["Close"].iloc[-1])

        # Build the Stock object
        stock = Stock(
            ticker=ticker_symbol.upper(),
            name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            current_price=current_price,
            currency=info.get("currency", "USD"),
            eps=info.get("trailingEps"),
            book_value_per_share=info.get("bookValue"),
            shares_outstanding=info.get("sharesOutstanding"),
            operating_income=info.get("operatingIncome"),
        )

        # Valuation metrics
        stock.valuation = ValuationMetrics(
            pe_trailing=info.get("trailingPE"),
            pe_forward=info.get("forwardPE"),
            pb_ratio=info.get("priceToBook"),
            ps_ratio=info.get("priceToSalesTrailing12Months"),
            peg_ratio=info.get("pegRatio"),
            ev_ebitda=info.get("enterpriseToEbitda"),
            market_cap=info.get("marketCap"),
            enterprise_value=info.get("enterpriseValue"),
        )

        # Profitability metrics
        stock.profitability = ProfitabilityMetrics(
            gross_margin=_to_pct(info.get("grossMargins")),
            operating_margin=_to_pct(info.get("operatingMargins")),
            net_margin=_to_pct(info.get("profitMargins")),
            roe=_to_pct(info.get("returnOnEquity")),
            roa=_to_pct(info.get("returnOnAssets")),
        )

        # Financial health
        stock.financial_health = FinancialHealth(
            current_ratio=info.get("currentRatio"),
            quick_ratio=info.get("quickRatio"),
            debt_to_equity=info.get("debtToEquity"),
            free_cash_flow=info.get("freeCashflow"),
        )

        # Growth metrics
        stock.growth = GrowthMetrics(
            revenue_growth_yoy=_to_pct(info.get("revenueGrowth")),
            earnings_growth_yoy=_to_pct(info.get("earningsGrowth")),
        )

        # Dividend info (dividendYield from yfinance is already in percentage form, e.g., 1.9 = 1.9%)
        stock.dividends = DividendInfo(
            dividend_yield=info.get("dividendYield"),
            dividend_rate=info.get("dividendRate"),
            payout_ratio=_to_pct(info.get("payoutRatio")),
        )

        # Technical indicators
        close_prices = history["Close"]
        rsi_14 = calculate_rsi(close_prices, 14)
        ma_50 = calculate_sma(close_prices, 50)
        ma_200 = calculate_sma(close_prices, 200)

        high_52w = info.get("fiftyTwoWeekHigh")
        low_52w = info.get("fiftyTwoWeekLow")
        metrics_52w = calculate_52w_metrics(high_52w, low_52w, current_price)

        # Calculate period returns from historical prices
        return_1m = _calculate_return(close_prices, 21)   # ~21 trading days = 1 month
        return_6m = _calculate_return(close_prices, 126)  # ~126 trading days = 6 months
        return_1y = _calculate_return(close_prices, 252)  # ~252 trading days = 1 year

        stock.technical = TechnicalIndicators(
            rsi_14=rsi_14,
            ma_50=ma_50,
            ma_200=ma_200,
            price_vs_ma_50_pct=calculate_price_vs_ma_pct(current_price, ma_50),
            price_vs_ma_200_pct=calculate_price_vs_ma_pct(current_price, ma_200),
            high_52w=high_52w,
            low_52w=low_52w,
            pct_from_52w_high=metrics_52w["pct_from_high"],
            pct_from_52w_low=metrics_52w["pct_from_low"],
            return_1m=return_1m,
            return_6m=return_6m,
            return_1y=return_1y,
        )

        # Fair value estimates
        graham_number = calculate_graham_number(stock.eps, stock.book_value_per_share)
        pe_fair_value = calculate_pe_fair_value(stock.eps, target_pe=15)

        # DCF calculation - estimate growth from earnings growth or use conservative default
        growth_rate = 0.05  # Default 5%
        if stock.growth.earnings_growth_yoy is not None and stock.growth.earnings_growth_yoy > 0:
            # Use half of recent growth as conservative estimate, capped at 15%
            growth_rate = min(stock.growth.earnings_growth_yoy / 100 / 2, 0.15)

        dcf_value = calculate_dcf_fair_value(
            free_cash_flow=stock.financial_health.free_cash_flow,
            shares_outstanding=stock.shares_outstanding,
            growth_rate=growth_rate,
            discount_rate=0.10,
            terminal_growth=0.03,
        )

        # Calculate margin of safety using best available fair value
        # Priority: DCF > Graham Number > P/E Fair Value
        best_fair_value = dcf_value or graham_number or pe_fair_value
        margin_of_safety = None
        if best_fair_value is not None and current_price is not None and current_price > 0:
            margin_of_safety = ((best_fair_value - current_price) / current_price) * 100

        stock.fair_value = FairValueEstimates(
            graham_number=graham_number,
            dcf_value=dcf_value,
            pe_fair_value=pe_fair_value,
            margin_of_safety_pct=margin_of_safety,
        )

        # Buyback info
        market_cap = info.get("marketCap")
        fcf = stock.financial_health.free_cash_flow
        fcf_yield = None
        if fcf and market_cap and market_cap > 0:
            fcf_yield = (fcf / market_cap) * 100

        stock.buyback = BuybackInfo(
            insider_ownership_pct=_to_pct(info.get("heldPercentInsiders")),
            institutional_ownership_pct=_to_pct(info.get("heldPercentInstitutions")),
            fcf_yield_pct=fcf_yield,
            cash_per_share=info.get("totalCashPerShare"),
            shares_outstanding=info.get("sharesOutstanding"),
            shares_outstanding_prior=None,  # Not directly available from yfinance
        )

        # Cache the result
        if use_cache:
            cache_stock_data(ticker_symbol, _stock_to_dict(stock))

        return stock

    except Exception as e:
        # Log error in production, for now just return None
        print(f"Error fetching {ticker_symbol}: {e}")
        return None


def _to_pct(value: float | None) -> float | None:
    """Convert decimal to percentage (0.15 -> 15.0)."""
    if value is None:
        return None
    return value * 100


def _calculate_return(close_prices: pd.Series, days: int) -> float | None:
    """Calculate return over a given number of trading days.

    Args:
        close_prices: Series of closing prices
        days: Number of trading days to look back

    Returns:
        Percentage return (e.g., 15.5 for 15.5% gain), or None if not enough data
    """
    if len(close_prices) < days + 1:
        return None

    try:
        current_price = float(close_prices.iloc[-1])
        past_price = float(close_prices.iloc[-days - 1])

        if past_price <= 0:
            return None

        return ((current_price - past_price) / past_price) * 100
    except (IndexError, TypeError):
        return None


def _stock_to_dict(stock: Stock) -> dict:
    """Convert Stock object to dictionary for caching."""
    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "sector": stock.sector,
        "industry": stock.industry,
        "current_price": stock.current_price,
        "currency": stock.currency,
        "eps": stock.eps,
        "book_value_per_share": stock.book_value_per_share,
        "shares_outstanding": stock.shares_outstanding,
        "operating_income": stock.operating_income,
        "valuation": asdict(stock.valuation),
        "profitability": asdict(stock.profitability),
        "financial_health": asdict(stock.financial_health),
        "growth": asdict(stock.growth),
        "dividends": asdict(stock.dividends),
        "technical": asdict(stock.technical),
        "fair_value": asdict(stock.fair_value),
        "buyback": asdict(stock.buyback),
    }


def _dict_to_stock(data: dict) -> Stock:
    """Convert cached dictionary back to Stock object."""
    return Stock(
        ticker=data["ticker"],
        name=data.get("name"),
        sector=data.get("sector"),
        industry=data.get("industry"),
        current_price=data.get("current_price"),
        currency=data.get("currency", "USD"),
        eps=data.get("eps"),
        book_value_per_share=data.get("book_value_per_share"),
        shares_outstanding=data.get("shares_outstanding"),
        operating_income=data.get("operating_income"),
        valuation=ValuationMetrics(**data.get("valuation", {})),
        profitability=ProfitabilityMetrics(**data.get("profitability", {})),
        financial_health=FinancialHealth(**data.get("financial_health", {})),
        growth=GrowthMetrics(**data.get("growth", {})),
        dividends=DividendInfo(**data.get("dividends", {})),
        technical=TechnicalIndicators(**data.get("technical", {})),
        fair_value=FairValueEstimates(**data.get("fair_value", {})),
        buyback=BuybackInfo(**data.get("buyback", {})),
    )
