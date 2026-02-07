"""Stock screening logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
# Streamlined to 7 focused presets - each with a distinct purpose
PRESET_SCREENS: dict[str, ScreenCriteria] = {
    # === VALUE PRESETS ===
    "graham": ScreenCriteria(
        # Benjamin Graham's classic value criteria
        pe_max=15,
        pb_max=1.5,
        pe_pb_product_max=22.5,
        current_ratio_min=2.0,
        debt_equity_max=50,  # 0.5 ratio = 50%
    ),
    "buffett": ScreenCriteria(
        # Warren Buffett's quality-at-fair-price approach
        roe_min=15,
        debt_equity_max=50,
        margin_min=10,
        pe_max=25,
    ),
    # === INCOME PRESET ===
    "dividend": ScreenCriteria(
        # High-yield income stocks with quality filters
        dividend_yield_min=3.0,
        debt_equity_max=100,
        roe_min=10,
    ),
    # === DISCOVERY PRESETS ===
    "fallen-angels": ScreenCriteria(
        # Quality stocks that have fallen hard - contrarian opportunities
        roe_min=15,  # Still profitable (quality)
        margin_min=10,  # Decent margins
        pct_from_52w_high_max=-30,  # Down at least 30% from high
        debt_equity_max=100,  # Not overleveraged
    ),
    "hidden-gems": ScreenCriteria(
        # Small/mid caps with strong fundamentals - beaten down, out of favor
        market_cap_min=2_000_000_000,  # At least $2B
        market_cap_max=10_000_000_000,  # Under $10B (less covered)
        pe_max=18,  # Reasonable valuation
        roe_min=12,  # Quality business
        debt_equity_max=75,  # Conservative
        rsi_max=40,  # Weak momentum (out of favor)
        below_200ma=True,  # Trading below 200-day MA
    ),
    # === CONTRARIAN PRESETS ===
    "oversold": ScreenCriteria(
        # Pure technical oversold - combine with value presets for best results
        rsi_max=30,
        near_52w_low_pct=15,  # Within 15% of 52-week low
        below_200ma=True,  # Below 200-day moving average
    ),
    "turnaround": ScreenCriteria(
        # Beaten down value stocks with recovery potential
        pe_max=12,  # Cheap valuation
        pct_from_52w_high_max=-25,  # Significant drawdown
        rsi_max=40,  # Weak momentum (potential bottom)
        current_ratio_min=1.5,  # Can survive
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
    "dividend": {
        "name": "Dividend",
        "description": "High-yield income stocks",
        "criteria": "Yield>3%, ROE>10%",
    },
    "fallen-angels": {
        "name": "Fallen Angels",
        "description": "Quality stocks down 30%+",
        "criteria": "ROE>15%, Margin>10%, down 30%+",
    },
    "hidden-gems": {
        "name": "Hidden Gems",
        "description": "Quality small/mid caps beaten down",
        "criteria": "$2-10B, P/E<18, ROE>12%, RSI<40, below 200MA",
    },
    "oversold": {
        "name": "Oversold",
        "description": "Technical oversold signals",
        "criteria": "RSI<30, near 52W low, below 200MA",
    },
    "turnaround": {
        "name": "Turnaround",
        "description": "Beaten down, recovery potential",
        "criteria": "P/E<12, down 25%+, RSI<40",
    },
}


# Available universes with descriptions
AVAILABLE_UNIVERSES: dict[str, str] = {
    # US Markets
    "sp500": "S&P 500 (~500 large-cap US stocks)",
    "dow30": "Dow Jones Industrial Average (30 stocks)",
    "nasdaq100": "NASDAQ-100 (100 largest NASDAQ stocks)",
    "nasdaq": "NASDAQ Composite (~3,100 NASDAQ-listed stocks)",
    "russell2000": "Russell 2000 sample (~200 small-cap stocks)",
    "etf": "ETFs (REITs, Commodities, Sectors, International)",
    # Regional Groupings
    "europe": "Major European markets (UK, DE, FR, CH, NL, ES, IT)",
    "asia": "Major Asian markets (JP, HK, CN, KR, TW, IN, SG, AU)",
    "emerging": "Emerging markets (BR, MX, ZA, IN, ID, TH, MY)",
    # Western Europe
    "uk": "London Stock Exchange - FTSE (GBP)",
    "germany": "Frankfurt/XETRA - DAX (EUR)",
    "france": "Euronext Paris - CAC 40 (EUR)",
    "switzerland": "SIX Swiss Exchange - SMI (CHF)",
    "netherlands": "Euronext Amsterdam - AEX (EUR)",
    "spain": "Bolsa de Madrid - IBEX 35 (EUR)",
    "italy": "Borsa Italiana - FTSE MIB (EUR)",
    "belgium": "Euronext Brussels - BEL 20 (EUR)",
    "austria": "Vienna Stock Exchange - ATX (EUR)",
    "portugal": "Euronext Lisbon - PSI 20 (EUR)",
    # Nordics
    "sweden": "Nasdaq Stockholm - OMX 30 (SEK)",
    "norway": "Oslo Bors - OBX (NOK)",
    "denmark": "Nasdaq Copenhagen - OMXC25 (DKK)",
    "finland": "Nasdaq Helsinki - OMXH25 (EUR)",
    # Asia-Pacific Developed
    "japan": "Tokyo Stock Exchange - Nikkei/TOPIX (JPY)",
    "hongkong": "Hong Kong Exchange - Hang Seng (HKD)",
    "australia": "ASX - ASX 200 (AUD)",
    "singapore": "Singapore Exchange - STI (SGD)",
    "newzealand": "NZX - NZX 50 (NZD)",
    # Asia-Pacific Emerging
    "china": "Shanghai & Shenzhen - CSI 300 (CNY)",
    "korea": "Korea Exchange - KOSPI (KRW)",
    "taiwan": "Taiwan Stock Exchange - TWSE (TWD)",
    "india": "National Stock Exchange - NIFTY 50 (INR)",
    "indonesia": "Indonesia Stock Exchange - LQ45 (IDR)",
    "malaysia": "Bursa Malaysia - KLCI (MYR)",
    "thailand": "Stock Exchange of Thailand - SET50 (THB)",
    # Americas
    "canada": "Toronto Stock Exchange - TSX 60 (CAD)",
    "brazil": "B3 Sao Paulo - Ibovespa (BRL)",
    "mexico": "Bolsa Mexicana - IPC (MXN)",
    # Middle East & Africa
    "southafrica": "Johannesburg Stock Exchange - JSE Top 40 (ZAR)",
    "israel": "Tel Aviv Stock Exchange - TA-35 (ILS)",
    "turkey": "Borsa Istanbul - BIST 30 (TRY)",
}


# Market currency mapping for international universes
MARKET_CURRENCIES: dict[str, str] = {
    # US Markets
    "sp500": "USD",
    "dow30": "USD",
    "nasdaq100": "USD",
    "nasdaq": "USD",
    "russell2000": "USD",
    "sweetspot": "USD",
    "etf": "USD",
    "dividends": "USD",
    "value": "USD",
    # Regional (mixed currencies)
    "europe": "EUR",  # Default to EUR for Europe
    "asia": "USD",  # Default to USD for cross-region
    "emerging": "USD",
    # Western Europe
    "uk": "GBP",
    "germany": "EUR",
    "france": "EUR",
    "switzerland": "CHF",
    "netherlands": "EUR",
    "spain": "EUR",
    "italy": "EUR",
    "belgium": "EUR",
    "austria": "EUR",
    "portugal": "EUR",
    # Nordics
    "sweden": "SEK",
    "norway": "NOK",
    "denmark": "DKK",
    "finland": "EUR",
    # Asia-Pacific Developed
    "japan": "JPY",
    "hongkong": "HKD",
    "australia": "AUD",
    "singapore": "SGD",
    "newzealand": "NZD",
    # Asia-Pacific Emerging
    "china": "CNY",
    "korea": "KRW",
    "taiwan": "TWD",
    "india": "INR",
    "indonesia": "IDR",
    "malaysia": "MYR",
    "thailand": "THB",
    # Americas
    "canada": "CAD",
    "brazil": "BRL",
    "mexico": "MXN",
    # Middle East & Africa
    "southafrica": "ZAR",
    "israel": "ILS",
    "turkey": "TRY",
}


def get_market_currency(universe: str) -> str:
    """Get the primary currency for a market/universe.

    Args:
        universe: Name of the universe

    Returns:
        Currency code (e.g., "USD", "GBP", "EUR")
    """
    return MARKET_CURRENCIES.get(universe, "USD")


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
        universe: Name of the universe (sp500, dow30, nasdaq100, russell2000, etf)

    Returns:
        List of ticker symbols

    Raises:
        FileNotFoundError: If the universe file doesn't exist
    """
    data_dir = get_data_dir()
    ticker_file = data_dir / f"{universe}.txt"

    if not ticker_file.exists():
        available = ", ".join(AVAILABLE_UNIVERSES.keys())
        raise FileNotFoundError(f"Universe '{universe}' not found. Available: {available}")

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
        raise FileNotFoundError(f"Universe '{universe}' not found. Available: {available}")

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
        name: Screen name (graham, buffett, dividend, fallen-angels,
            hidden-gems, oversold, turnaround)

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


# Preset descriptions for TUI display
PRESET_DESCRIPTIONS: dict[str, str] = {
    "graham": "Classic Ben Graham value criteria",
    "buffett": "Quality companies at fair prices",
    "dividend": "Income-focused high yielders",
    "fallen-angels": "Quality stocks down 30%+",
    "hidden-gems": "Quality small/mid caps beaten down",
    "oversold": "Technical oversold signals",
    "turnaround": "Beaten down, recovery potential",
}


def calculate_similarity_score(target: Stock, candidate: Stock) -> tuple[float, list[str]]:
    """
    Calculate how similar a candidate stock is to a target stock.

    Returns a score from 0-100 and a list of matching reasons.
    Higher score = more similar.

    Factors considered:
    - Same industry (30 points)
    - Same sector (10 points)
    - Similar market cap range (15 points)
    - Similar P/E range (15 points)
    - Similar ROE (10 points)
    - Similar dividend yield (10 points)
    - Similar RSI/technical setup (10 points)

    Args:
        target: The stock to find similar stocks to
        candidate: A potential similar stock

    Returns:
        Tuple of (similarity_score, list of matching reasons)
    """
    if target.ticker == candidate.ticker:
        return 0, []  # Don't match self

    score = 0.0
    reasons = []

    # Industry match (30 points) - highest weight
    if target.industry and candidate.industry:
        if target.industry == candidate.industry:
            score += 30
            reasons.append("Same industry")
        elif target.sector and candidate.sector and target.sector == candidate.sector:
            score += 10
            reasons.append("Same sector")

    # Market cap similarity (15 points)
    target_mc = target.valuation.market_cap
    candidate_mc = candidate.valuation.market_cap
    if target_mc and candidate_mc and target_mc > 0:
        ratio = candidate_mc / target_mc
        if 0.5 <= ratio <= 2.0:  # Within 50-200% of target
            score += 15
            reasons.append("Similar size")
        elif 0.25 <= ratio <= 4.0:  # Within 25-400%
            score += 8

    # P/E similarity (15 points)
    target_pe = target.valuation.pe_trailing
    candidate_pe = candidate.valuation.pe_trailing
    if (
        target_pe
        and candidate_pe
        and isinstance(target_pe, (int, float))
        and isinstance(candidate_pe, (int, float))
        and target_pe > 0
        and candidate_pe > 0
    ):
        pe_diff = abs(target_pe - candidate_pe)
        if pe_diff <= 3:  # Very similar P/E
            score += 15
            reasons.append("Similar P/E")
        elif pe_diff <= 7:
            score += 10
        elif pe_diff <= 12:
            score += 5

    # ROE similarity (10 points)
    target_roe = target.profitability.roe
    candidate_roe = candidate.profitability.roe
    if target_roe is not None and candidate_roe is not None:
        roe_diff = abs(target_roe - candidate_roe)
        if roe_diff <= 3:  # Very similar ROE
            score += 10
            reasons.append("Similar ROE")
        elif roe_diff <= 7:
            score += 6
        elif roe_diff <= 12:
            score += 3

    # Dividend yield similarity (10 points)
    target_div = target.dividends.dividend_yield
    candidate_div = candidate.dividends.dividend_yield
    if target_div is not None and candidate_div is not None:
        # Both pay dividends
        div_diff = abs(target_div - candidate_div)
        if div_diff <= 0.5:  # Very similar yield
            score += 10
            reasons.append("Similar dividend")
        elif div_diff <= 1.5:
            score += 6
        elif div_diff <= 3:
            score += 3
    elif target_div is None and candidate_div is None:
        # Both non-dividend payers
        score += 5

    # Technical/RSI similarity (10 points)
    target_rsi = target.technical.rsi_14
    candidate_rsi = candidate.technical.rsi_14
    if target_rsi and candidate_rsi:
        rsi_diff = abs(target_rsi - candidate_rsi)
        if rsi_diff <= 5:  # Very similar momentum
            score += 10
            reasons.append("Similar momentum")
        elif rsi_diff <= 12:
            score += 6
        elif rsi_diff <= 20:
            score += 3

    return score, reasons


def find_similar_stocks(
    target: Stock,
    candidates: list[Stock],
    limit: int = 10,
    min_score: float = 25,
) -> list[tuple[Stock, float, list[str]]]:
    """
    Find stocks similar to the target stock.

    Args:
        target: The stock to find similar stocks to
        candidates: List of stocks to search through
        limit: Maximum number of results to return
        min_score: Minimum similarity score to include (0-100)

    Returns:
        List of (stock, score, reasons) tuples, sorted by score descending
    """
    scored = []

    for candidate in candidates:
        score, reasons = calculate_similarity_score(target, candidate)
        if score >= min_score:
            scored.append((candidate, score, reasons))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[:limit]
