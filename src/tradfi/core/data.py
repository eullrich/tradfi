"""Data fetching from yfinance with caching and rate limiting."""

from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime

import pandas as pd
import yfinance as yf

from tradfi.core.technical import (
    calculate_52w_metrics,
    calculate_price_vs_ma_pct,
    calculate_rsi,
    calculate_sma,
)
from tradfi.core.valuation import (
    calculate_dcf_fair_value,
    calculate_graham_number,
    calculate_pe_fair_value,
)
from tradfi.models.stock import (
    BuybackInfo,
    DividendInfo,
    ETFMetrics,
    FairValueEstimates,
    FinancialHealth,
    GrowthMetrics,
    ProfitabilityMetrics,
    Stock,
    TechnicalIndicators,
    ValuationMetrics,
)
from tradfi.utils.cache import (
    cache_stock_data,
    get_batch_cached_stocks,
    get_cached_stock_data,
    get_config,
)

# Track last request time for rate limiting
_last_request_time: float = 0


def _determine_asset_type(info: dict) -> str:
    """Detect if ticker is ETF or stock from yfinance info.

    Args:
        info: yfinance Ticker.info dictionary

    Returns:
        "etf" or "stock"
    """
    quote_type = info.get("quoteType", "EQUITY")
    return "etf" if quote_type == "ETF" else "stock"


def _extract_etf_metrics(info: dict) -> ETFMetrics:
    """Extract ETF-specific metrics from yfinance info.

    Args:
        info: yfinance Ticker.info dictionary

    Returns:
        ETFMetrics object with populated fields
    """
    # Parse inception date if available
    inception_date = None
    fund_inception = info.get("fundInceptionDate")
    if fund_inception:
        try:
            inception_date = datetime.fromtimestamp(fund_inception).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass

    # Expense ratio - yfinance returns as decimal (0.0003 for 0.03%)
    expense_ratio_raw = info.get("annualReportExpenseRatio")
    expense_ratio = None
    if expense_ratio_raw is not None:
        # Convert to percentage for display (0.0003 -> 0.03)
        expense_ratio = expense_ratio_raw * 100

    # YTD and multi-year returns - yfinance returns as decimals
    ytd_return = _to_pct(info.get("ytdReturn"))
    return_3y = _to_pct(info.get("threeYearAverageReturn"))
    return_5y = _to_pct(info.get("fiveYearAverageReturn"))

    # Calculate premium/discount to NAV
    nav = info.get("navPrice")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    premium_discount = None
    if nav and current_price and nav > 0:
        premium_discount = ((current_price - nav) / nav) * 100

    return ETFMetrics(
        expense_ratio=expense_ratio,
        aum=info.get("totalAssets"),
        avg_volume=info.get("averageVolume"),
        holdings_count=info.get("fundHoldings"),
        nav=nav,
        premium_discount=premium_discount,
        inception_date=inception_date,
        fund_family=info.get("fundFamily"),
        category=info.get("category"),
        legal_type=info.get("legalType"),
        benchmark=info.get("benchmark"),
        ytd_return=ytd_return,
        return_3y=return_3y,
        return_5y=return_5y,
        beta_3y=info.get("beta3Year"),
    )


def fetch_stock(
    ticker_symbol: str, use_cache: bool = True, cache_only: bool = False
) -> Stock | None:
    """
    Fetch stock data from cache only. Does not hit yfinance API.

    Args:
        ticker_symbol: Stock ticker (e.g., "AAPL")
        use_cache: Ignored (always reads from cache)

    Returns:
        Stock object with all metrics, or None if not in cache
    """
    ticker_symbol = ticker_symbol.upper()

    # Only serve from cache - never hit yfinance
    cached = get_cached_stock_data(ticker_symbol, ignore_ttl=True)
    if cached:
        return _dict_to_stock(cached)
    return None


def fetch_stocks_batch(
    tickers: list[str] | None = None, fetch_missing: bool = False
) -> dict[str, Stock]:
    """
    Fetch multiple stocks from cache in a single efficient query.

    When fetch_missing is True and specific tickers are provided, any tickers
    not found in cache will be fetched from yfinance via fetch_stock_from_api().

    Args:
        tickers: List of ticker symbols. If None, returns all cached stocks.
        fetch_missing: If True, fetch uncached tickers from yfinance.

    Returns:
        Dict mapping ticker to Stock object.
    """
    cached_data = get_batch_cached_stocks(tickers)
    result: dict[str, Stock] = {}
    for ticker, data in cached_data.items():
        try:
            result[ticker] = _dict_to_stock(data)
        except Exception:
            pass  # Skip stocks with corrupt/incompatible cached data

    # Fetch missing tickers from yfinance if requested
    if fetch_missing and tickers:
        missing_tickers = [t.upper() for t in tickers if t.upper() not in result]
        for ticker in missing_tickers:
            try:
                stock = fetch_stock_from_api(ticker)
                if stock:
                    result[ticker] = stock
            except Exception:
                pass  # Individual failures don't break the batch

    return result


def fetch_stock_from_api(ticker_symbol: str) -> Stock | None:
    """
    Fetch stock data directly from yfinance API and cache it.
    Used only for cache population (prefetch command).

    Args:
        ticker_symbol: Stock ticker (e.g., "AAPL")

    Returns:
        Stock object with all metrics, or None if fetch failed
    """
    global _last_request_time
    ticker_symbol = ticker_symbol.upper()
    config = get_config()

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

        # Detect asset type (stock vs ETF)
        asset_type = _determine_asset_type(info)

        # Build the Stock object
        stock = Stock(
            ticker=ticker_symbol.upper(),
            name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector") or info.get("category"),  # ETFs use category
            industry=info.get("industry"),
            current_price=current_price,
            currency=info.get("currency", "USD"),
            asset_type=asset_type,
            eps=info.get("trailingEps"),
            book_value_per_share=info.get("bookValue"),
            shares_outstanding=info.get("sharesOutstanding"),
            operating_income=info.get("operatingIncome"),
        )

        # Extract ETF-specific metrics if this is an ETF
        if asset_type == "etf":
            stock.etf = _extract_etf_metrics(info)

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

        # Dividend info
        ex_div_date = info.get("exDividendDate")
        ex_div_str = None
        if ex_div_date:
            # yfinance returns this as a Unix timestamp
            try:
                ex_div_str = datetime.fromtimestamp(ex_div_date).strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                ex_div_str = None

        # Parse lastDividendDate (Unix timestamp like exDividendDate)
        last_div_date = info.get("lastDividendDate")
        last_div_str = None
        if last_div_date:
            try:
                last_div_str = datetime.fromtimestamp(last_div_date).strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                last_div_str = None

        # Calculate dividend yield from rate and price (more reliable than yfinance's dividendYield
        # which can be returned in inconsistent formats)
        dividend_rate = info.get("dividendRate")
        dividend_yield = None
        if dividend_rate and current_price and current_price > 0:
            raw_yield = dividend_rate / current_price
            # Sanity check: real dividend yields are typically 0-20%, rarely above 50%
            # If raw_yield > 0.50, it likely means there's a unit mismatch (e.g., rate in cents,
            # price in dollars) and the value is already percentage-like
            if raw_yield > 0.50:
                dividend_yield = raw_yield  # Already percentage-like
            else:
                dividend_yield = raw_yield * 100  # Convert decimal to percentage

        # Calculate 5-year average dividend yield from historical data if available
        # yfinance's fiveYearAvgDividendYield can also be inconsistent
        five_year_avg_yield_raw = info.get("fiveYearAvgDividendYield")
        five_year_avg_yield = None
        if five_year_avg_yield_raw is not None:
            # Check if value is likely already a percentage (> 1) or decimal (< 1)
            # Real dividend yields are typically < 20% (0.20 as decimal)
            if five_year_avg_yield_raw > 1:
                # Already a percentage
                five_year_avg_yield = five_year_avg_yield_raw
            else:
                # Decimal format, convert to percentage
                five_year_avg_yield = five_year_avg_yield_raw * 100

        stock.dividends = DividendInfo(
            dividend_yield=dividend_yield,
            dividend_rate=dividend_rate,
            payout_ratio=_to_pct(info.get("payoutRatio")),
            ex_dividend_date=ex_div_str,
            dividend_frequency=_detect_dividend_frequency(ticker),
            trailing_annual_dividend_rate=info.get("trailingAnnualDividendRate"),
            five_year_avg_dividend_yield=five_year_avg_yield,
            last_dividend_value=info.get("lastDividendValue"),
            last_dividend_date=last_div_str,
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
        return_1m = _calculate_return(close_prices, 21)
        return_6m = _calculate_return(close_prices, 126)
        return_1y = _calculate_return(close_prices, 252)

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

        growth_rate = 0.05
        if stock.growth.earnings_growth_yoy is not None and stock.growth.earnings_growth_yoy > 0:
            growth_rate = min(stock.growth.earnings_growth_yoy / 100 / 2, 0.15)

        dcf_value = calculate_dcf_fair_value(
            free_cash_flow=stock.financial_health.free_cash_flow,
            shares_outstanding=stock.shares_outstanding,
            growth_rate=growth_rate,
            discount_rate=0.10,
            terminal_growth=0.03,
        )

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
            shares_outstanding_prior=None,
        )

        # Cache the result
        cache_stock_data(ticker_symbol, _stock_to_dict(stock))

        return stock

    except Exception as e:
        # Log error
        print(f"Error fetching {ticker_symbol}: {e}")

        # Fallback to stale cache if available (better than returning nothing)
        stale_cached = get_cached_stock_data(ticker_symbol, ignore_ttl=True)
        if stale_cached:
            print(f"Returning stale cached data for {ticker_symbol}")
            return _dict_to_stock(stale_cached)

        return None


def _to_pct(value: float | None) -> float | None:
    """Convert decimal to percentage (0.15 -> 15.0)."""
    if value is None:
        return None
    return value * 100


def _detect_dividend_frequency(ticker: yf.Ticker) -> str | None:
    """Infer dividend frequency from historical payment intervals."""
    try:
        dividends = ticker.dividends
        if dividends.empty or len(dividends) < 2:
            return None

        # Get intervals between last several dividends
        recent = dividends.tail(6)  # Last ~1.5 years of data
        if len(recent) < 2:
            return None

        intervals = recent.index[1:] - recent.index[:-1]
        avg_days = intervals.mean().days

        if avg_days <= 45:
            return "monthly"
        elif avg_days <= 100:
            return "quarterly"
        elif avg_days <= 200:
            return "semi-annual"
        else:
            return "annual"
    except Exception:
        return None


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
        "asset_type": stock.asset_type,
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
        "etf": asdict(stock.etf),
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
        asset_type=data.get("asset_type", "stock"),
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
        etf=ETFMetrics(**data.get("etf", {})),
    )
