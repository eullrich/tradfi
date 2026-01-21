"""Stock screening logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from tradfi.models.stock import Stock


@dataclass
class ScreenCriteria:
    """Screening criteria for filtering stocks."""

    # Valuation filters
    pe_min: float | None = None
    pe_max: float | None = None
    pb_min: float | None = None
    pb_max: float | None = None
    ps_min: float | None = None
    ps_max: float | None = None
    peg_min: float | None = None
    peg_max: float | None = None

    # Profitability filters
    roe_min: float | None = None
    roe_max: float | None = None  # For finding weak profitability (shorts)
    roa_min: float | None = None
    margin_min: float | None = None  # Net margin
    margin_max: float | None = None  # For finding weak margins (shorts)

    # Financial health filters
    debt_equity_max: float | None = None
    current_ratio_min: float | None = None

    # Growth filters
    revenue_growth_min: float | None = None
    earnings_growth_min: float | None = None

    # Dividend filters
    dividend_yield_min: float | None = None

    # Size filters
    market_cap_min: float | None = None
    market_cap_max: float | None = None

    # Technical / Oversold filters
    rsi_min: float | None = None
    rsi_max: float | None = None
    near_52w_low_pct: float | None = None  # Within X% of 52-week low
    below_200ma: bool = False  # Price below 200-day MA
    below_50ma: bool = False  # Price below 50-day MA
    pct_below_200ma_min: float | None = None  # At least X% below 200 MA

    # Graham special criteria
    pe_pb_product_max: float | None = None  # P/E × P/B < 22.5

    # Buyback potential criteria
    fcf_yield_min: float | None = None  # Free cash flow yield minimum %
    insider_ownership_min: float | None = None  # Insider ownership minimum %
    pct_from_52w_high_max: float | None = None  # Down at least X% from 52W high


# Pre-built screen definitions
PRESET_SCREENS: dict[str, ScreenCriteria] = {
    "graham": ScreenCriteria(
        pe_max=15,
        pb_max=1.5,
        pe_pb_product_max=22.5,
        current_ratio_min=2.0,
        debt_equity_max=50,  # 0.5 ratio = 50%
    ),
    "buffett": ScreenCriteria(
        roe_min=15,
        debt_equity_max=50,
        margin_min=10,
        pe_max=25,
    ),
    "deep-value": ScreenCriteria(
        pb_max=1.0,
        pe_max=10,
    ),
    "oversold-value": ScreenCriteria(
        pe_max=15,
        roe_min=10,
        rsi_max=35,
        near_52w_low_pct=20,
        debt_equity_max=100,
    ),
    "dividend": ScreenCriteria(
        dividend_yield_min=3.0,
        debt_equity_max=100,
        roe_min=10,
    ),
    "quality": ScreenCriteria(
        roe_min=20,
        margin_min=15,
        debt_equity_max=50,
    ),
    "buyback": ScreenCriteria(
        fcf_yield_min=3.0,  # Good free cash flow (3%+)
        debt_equity_max=150,  # Moderate leverage OK
        pct_from_52w_high_max=-10,  # Down at least 10% - management buys dips
    ),
    "short-candidates": ScreenCriteria(
        pe_min=40,  # Very expensive valuation
        roe_max=10,  # Weak profitability for the price
        rsi_min=60,  # Overbought territory
    ),
}


# Preset descriptions and criteria summaries for UI display
PRESET_INFO: dict[str, dict[str, str]] = {
    "graham": {
        "name": "Graham",
        "description": "Benjamin Graham's value criteria",
        "criteria": "P/E<15, P/B<1.5, CR>2",
    },
    "buffett": {
        "name": "Buffett",
        "description": "Quality companies at fair prices",
        "criteria": "ROE>15%, Margin>10%, P/E<25",
    },
    "deep-value": {
        "name": "Deep Value",
        "description": "Extremely cheap stocks",
        "criteria": "P/B<1.0, P/E<10",
    },
    "oversold-value": {
        "name": "Oversold Value",
        "description": "Value stocks at technical lows",
        "criteria": "P/E<15, RSI<35, near 52W low",
    },
    "dividend": {
        "name": "Dividend",
        "description": "High-yield income stocks",
        "criteria": "Yield>3%, ROE>10%",
    },
    "quality": {
        "name": "Quality",
        "description": "High-margin, profitable businesses",
        "criteria": "ROE>20%, Margin>15%",
    },
    "buyback": {
        "name": "Buyback",
        "description": "Cash-rich stocks buying back shares",
        "criteria": "FCF Yield>3%, down 10%+ from high",
    },
    "short-candidates": {
        "name": "Short Candidates",
        "description": "Overvalued, weak stocks",
        "criteria": "P/E>40, ROE<10%, RSI>60",
    },
}


# Available universes with descriptions
AVAILABLE_UNIVERSES: dict[str, str] = {
    "sp500": "S&P 500 (~500 large-cap US stocks)",
    "dow30": "Dow Jones Industrial Average (30 stocks)",
    "nasdaq100": "NASDAQ-100 (100 largest NASDAQ stocks)",
    "russell2000": "Russell 2000 sample (~200 small-cap stocks)",
    "sweetspot": "$2-12B market cap sweet spot (under-followed + fallen angels)",
    "etf": "ETFs (REITs, Commodities, Sectors, International)",
    "dividends": "Dividend Aristocrats & high-yield stocks",
    "value": "Value-focused stocks and ETFs",
}


def get_data_dir() -> Path:
    """Get the data directory path."""
    return Path(__file__).parent.parent.parent.parent / "data"


def list_available_universes() -> dict[str, tuple[str, int]]:
    """
    List all available universes with their descriptions and stock counts.

    Returns:
        Dict mapping universe name to (description, count) tuple
    """
    data_dir = get_data_dir()
    result = {}

    for name, description in AVAILABLE_UNIVERSES.items():
        ticker_file = data_dir / f"{name}.txt"
        if ticker_file.exists():
            with open(ticker_file) as f:
                count = len([line for line in f if line.strip() and not line.startswith("#")])
            result[name] = (description, count)

    return result


def load_tickers(universe: str = "sp500") -> list[str]:
    """
    Load ticker list for a given universe.

    Args:
        universe: Name of the universe (sp500, dow30, nasdaq100, russell2000,
                  sweetspot, etf, dividends, value)

    Returns:
        List of ticker symbols

    Raises:
        FileNotFoundError: If the universe file doesn't exist
    """
    data_dir = get_data_dir()
    ticker_file = data_dir / f"{universe}.txt"

    if not ticker_file.exists():
        available = ", ".join(AVAILABLE_UNIVERSES.keys())
        raise FileNotFoundError(
            f"Universe '{universe}' not found. Available: {available}"
        )

    with open(ticker_file) as f:
        tickers = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    return tickers


def load_tickers_with_categories(universe: str) -> dict[str, list[str]]:
    """
    Load tickers organized by category from a universe file.

    Categories are defined by '## Category Name' headers in the data file.
    Tickers without a category header are placed under 'Uncategorized'.

    Args:
        universe: Name of the universe (e.g., 'etf')

    Returns:
        Dict mapping category names to lists of tickers
    """
    data_dir = get_data_dir()
    ticker_file = data_dir / f"{universe}.txt"

    if not ticker_file.exists():
        available = ", ".join(AVAILABLE_UNIVERSES.keys())
        raise FileNotFoundError(
            f"Universe '{universe}' not found. Available: {available}"
        )

    categories: dict[str, list[str]] = {}
    current_category = "Uncategorized"

    with open(ticker_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Check for category header (## Category Name)
            if line.startswith("## "):
                current_category = line[3:].strip()
                if current_category not in categories:
                    categories[current_category] = []
            # Skip comments
            elif line.startswith("#"):
                continue
            # It's a ticker
            else:
                if current_category not in categories:
                    categories[current_category] = []
                categories[current_category].append(line)

    return categories


def get_universe_categories(universe: str) -> list[str]:
    """
    Get list of category names for a universe.

    Args:
        universe: Name of the universe (e.g., 'etf')

    Returns:
        List of category names, or empty list if no categories
    """
    try:
        categories = load_tickers_with_categories(universe)
        # Return categories in order, excluding 'Uncategorized' if empty
        result = [cat for cat in categories.keys() if cat != "Uncategorized" or categories[cat]]
        return result
    except FileNotFoundError:
        return []


def load_tickers_by_categories(
    universe: str, selected_categories: set[str] | None = None
) -> list[str]:
    """
    Load tickers filtered by selected categories.

    Args:
        universe: Name of the universe
        selected_categories: Set of category names to include, or None for all

    Returns:
        List of tickers from the selected categories
    """
    categories = load_tickers_with_categories(universe)

    if selected_categories is None:
        # Return all tickers
        all_tickers = []
        for tickers in categories.values():
            all_tickers.extend(tickers)
        return all_tickers

    # Filter by selected categories
    filtered_tickers = []
    for cat_name, tickers in categories.items():
        if cat_name in selected_categories:
            filtered_tickers.extend(tickers)

    return filtered_tickers


def screen_stock(stock: Stock, criteria: ScreenCriteria) -> bool:
    """
    Check if a stock passes the screening criteria.

    Args:
        stock: Stock object with all metrics
        criteria: Screening criteria to apply

    Returns:
        True if stock passes all criteria, False otherwise
    """
    # Valuation checks
    if criteria.pe_min is not None:
        pe = stock.valuation.pe_trailing
        # Handle string values like 'Infinity' from yfinance
        if pe is None or not isinstance(pe, (int, float)) or pe < criteria.pe_min:
            return False

    if criteria.pe_max is not None:
        pe = stock.valuation.pe_trailing
        # Handle string values like 'Infinity' from yfinance
        if pe is None or not isinstance(pe, (int, float)) or pe <= 0 or pe > criteria.pe_max:
            return False

    if criteria.pb_min is not None:
        pb = stock.valuation.pb_ratio
        if pb is None or not isinstance(pb, (int, float)) or pb < criteria.pb_min:
            return False

    if criteria.pb_max is not None:
        pb = stock.valuation.pb_ratio
        if pb is None or not isinstance(pb, (int, float)) or pb <= 0 or pb > criteria.pb_max:
            return False

    if criteria.ps_max is not None:
        ps = stock.valuation.ps_ratio
        if ps is None or not isinstance(ps, (int, float)) or ps <= 0 or ps > criteria.ps_max:
            return False

    if criteria.peg_max is not None:
        peg = stock.valuation.peg_ratio
        if peg is None or not isinstance(peg, (int, float)) or peg <= 0 or peg > criteria.peg_max:
            return False

    # Graham's P/E × P/B product check
    if criteria.pe_pb_product_max is not None:
        pe = stock.valuation.pe_trailing
        pb = stock.valuation.pb_ratio
        # Handle string values like 'Infinity' from yfinance
        if pe is None or pb is None:
            return False
        if not isinstance(pe, (int, float)) or not isinstance(pb, (int, float)):
            return False
        if pe <= 0 or pb <= 0:
            return False
        if pe * pb > criteria.pe_pb_product_max:
            return False

    # Profitability checks
    if criteria.roe_min is not None:
        roe = stock.profitability.roe
        if roe is None or roe < criteria.roe_min:
            return False

    if criteria.roe_max is not None:
        roe = stock.profitability.roe
        # For shorts: allow None/negative ROE (that's bad), just cap the good ones
        if roe is not None and roe > criteria.roe_max:
            return False

    if criteria.roa_min is not None:
        roa = stock.profitability.roa
        if roa is None or roa < criteria.roa_min:
            return False

    if criteria.margin_min is not None:
        margin = stock.profitability.net_margin
        if margin is None or margin < criteria.margin_min:
            return False

    if criteria.margin_max is not None:
        margin = stock.profitability.net_margin
        # For shorts: allow None/negative margins, just cap the good ones
        if margin is not None and margin > criteria.margin_max:
            return False

    # Financial health checks
    if criteria.debt_equity_max is not None:
        de = stock.financial_health.debt_to_equity
        # D/E from yfinance is already in percentage form (e.g., 50 = 0.5 ratio)
        if de is not None and de > criteria.debt_equity_max:
            return False

    if criteria.current_ratio_min is not None:
        cr = stock.financial_health.current_ratio
        if cr is None or cr < criteria.current_ratio_min:
            return False

    # Growth checks
    if criteria.revenue_growth_min is not None:
        rg = stock.growth.revenue_growth_yoy
        if rg is None or rg < criteria.revenue_growth_min:
            return False

    if criteria.earnings_growth_min is not None:
        eg = stock.growth.earnings_growth_yoy
        if eg is None or eg < criteria.earnings_growth_min:
            return False

    # Dividend checks
    if criteria.dividend_yield_min is not None:
        dy = stock.dividends.dividend_yield
        if dy is None or dy < criteria.dividend_yield_min:
            return False

    # Size checks
    if criteria.market_cap_min is not None:
        mc = stock.valuation.market_cap
        if mc is None or mc < criteria.market_cap_min:
            return False

    if criteria.market_cap_max is not None:
        mc = stock.valuation.market_cap
        if mc is None or mc > criteria.market_cap_max:
            return False

    # Technical / Oversold checks
    if criteria.rsi_min is not None:
        rsi = stock.technical.rsi_14
        if rsi is None or rsi < criteria.rsi_min:
            return False

    if criteria.rsi_max is not None:
        rsi = stock.technical.rsi_14
        if rsi is None or rsi > criteria.rsi_max:
            return False

    if criteria.near_52w_low_pct is not None:
        pct_from_low = stock.technical.pct_from_52w_low
        if pct_from_low is None or pct_from_low > criteria.near_52w_low_pct:
            return False

    if criteria.below_200ma:
        pct_vs_200 = stock.technical.price_vs_ma_200_pct
        if pct_vs_200 is None or pct_vs_200 >= 0:
            return False

    if criteria.below_50ma:
        pct_vs_50 = stock.technical.price_vs_ma_50_pct
        if pct_vs_50 is None or pct_vs_50 >= 0:
            return False

    if criteria.pct_below_200ma_min is not None:
        pct_vs_200 = stock.technical.price_vs_ma_200_pct
        if pct_vs_200 is None or pct_vs_200 > -criteria.pct_below_200ma_min:
            return False

    # Buyback potential checks
    if criteria.fcf_yield_min is not None:
        fcf_yield = stock.buyback.fcf_yield_pct
        if fcf_yield is None or fcf_yield < criteria.fcf_yield_min:
            return False

    if criteria.insider_ownership_min is not None:
        insider = stock.buyback.insider_ownership_pct
        if insider is None or insider < criteria.insider_ownership_min:
            return False

    if criteria.pct_from_52w_high_max is not None:
        pct_from_high = stock.technical.pct_from_52w_high
        # pct_from_high is negative (e.g., -20 means down 20%)
        # We want stocks down at least X%, so pct_from_high <= max
        if pct_from_high is None or pct_from_high > criteria.pct_from_52w_high_max:
            return False

    # All checks passed
    return True


def get_preset_screen(name: str) -> ScreenCriteria:
    """
    Get a pre-built screen by name.

    Args:
        name: Screen name (graham, buffett, deep-value, oversold-value, dividend, quality)

    Returns:
        ScreenCriteria for the preset

    Raises:
        ValueError: If preset name not found
    """
    name = name.lower().replace("_", "-")
    if name not in PRESET_SCREENS:
        available = ", ".join(PRESET_SCREENS.keys())
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")

    return PRESET_SCREENS[name]
