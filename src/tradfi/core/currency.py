"""Currency conversion service using yfinance forex data."""

from __future__ import annotations

import time

import yfinance as yf

# Currency symbols for display
CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "AUD": "A$",
    "CAD": "C$",
    "CHF": "CHF",
    "CNY": "¥",
    "HKD": "HK$",
    "SGD": "S$",
    "INR": "₹",
    "KRW": "₩",
    "TWD": "NT$",
    "BRL": "R$",
    "MXN": "MX$",
    "ZAR": "R",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "NZD": "NZ$",
    "THB": "฿",
    "IDR": "Rp",
    "MYR": "RM",
    "PHP": "₱",
    "PLN": "zł",
    "TRY": "₺",
    "ILS": "₪",
    "SAR": "SR",
    "AED": "AED",
    "CLP": "CLP",
    "COP": "COP",
    "XAU": "XAU",  # Gold - troy ounces
}

# yfinance forex tickers (all vs USD)
# For XXX/USD pairs, the rate is how many USD per 1 XXX
# For USD/XXX pairs (like USDJPY), the rate is how many XXX per 1 USD
FOREX_TICKERS: dict[str, str] = {
    # Major currencies (XXX/USD format - rate = USD per 1 unit)
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
    "AUD": "AUDUSD=X",
    "NZD": "NZDUSD=X",
    # USD/XXX format - need to invert
    "JPY": "USDJPY=X",
    "CAD": "USDCAD=X",
    "CHF": "USDCHF=X",
    "CNY": "USDCNY=X",
    "HKD": "USDHKD=X",
    "SGD": "USDSGD=X",
    "INR": "USDINR=X",
    "KRW": "USDKRW=X",
    "TWD": "USDTWD=X",
    "BRL": "USDBRL=X",
    "MXN": "USDMXN=X",
    "ZAR": "USDZAR=X",
    "SEK": "USDSEK=X",
    "NOK": "USDNOK=X",
    "DKK": "USDDKK=X",
    "THB": "USDTHB=X",
    "IDR": "USDIDR=X",
    "MYR": "USDMYR=X",
    "PHP": "USDPHP=X",
    "PLN": "USDPLN=X",
    "TRY": "USDTRY=X",
    "ILS": "USDILS=X",
    "SAR": "USDSAR=X",
    "AED": "USDAED=X",
    "CLP": "USDCLP=X",
    "COP": "USDCOP=X",
    # Gold
    "XAU": "XAUUSD=X",  # USD per troy ounce
}

# Currencies where yfinance gives USD/XXX (need to invert for XXX/USD)
INVERTED_PAIRS = {
    "JPY",
    "CAD",
    "CHF",
    "CNY",
    "HKD",
    "SGD",
    "INR",
    "KRW",
    "TWD",
    "BRL",
    "MXN",
    "ZAR",
    "SEK",
    "NOK",
    "DKK",
    "THB",
    "IDR",
    "MYR",
    "PHP",
    "PLN",
    "TRY",
    "ILS",
    "SAR",
    "AED",
    "CLP",
    "COP",
}


def get_currency_symbol(currency: str) -> str:
    """Get the display symbol for a currency code."""
    return CURRENCY_SYMBOLS.get(currency.upper(), currency.upper())


def fetch_exchange_rate(currency: str) -> float | None:
    """
    Fetch a single exchange rate from yfinance.

    Returns the rate as: how many USD per 1 unit of currency.
    For gold (XAU), returns USD per troy ounce.

    Returns None if fetch fails.
    """
    currency = currency.upper()

    if currency == "USD":
        return 1.0

    ticker_symbol = FOREX_TICKERS.get(currency)
    if not ticker_symbol:
        return None

    try:
        ticker = yf.Ticker(ticker_symbol)
        # Try to get the current price
        hist = ticker.history(period="1d")
        if hist.empty:
            # Fallback to info
            info = ticker.info
            rate = info.get("regularMarketPrice") or info.get("previousClose")
        else:
            rate = hist["Close"].iloc[-1]

        if rate is None:
            return None

        # For USD/XXX pairs, we need to invert to get XXX/USD
        if currency in INVERTED_PAIRS:
            return 1.0 / rate

        # For XXX/USD pairs (EUR, GBP, AUD, NZD) and XAU, rate is already correct
        return float(rate)
    except Exception:
        return None


def fetch_exchange_rates(currencies: list[str]) -> dict[str, float]:
    """
    Fetch multiple exchange rates from yfinance.

    Returns dict mapping currency code to rate (USD per 1 unit).
    Only includes currencies that were successfully fetched.
    """
    rates = {"USD": 1.0}

    for currency in currencies:
        currency = currency.upper()
        if currency == "USD":
            continue

        rate = fetch_exchange_rate(currency)
        if rate is not None:
            rates[currency] = rate

    return rates


def convert_currency(
    value: float,
    from_currency: str,
    to_currency: str,
    rates: dict[str, float] | None = None,
) -> float | None:
    """
    Convert a value from one currency to another.

    Args:
        value: The amount to convert
        from_currency: Source currency code
        to_currency: Target currency code
        rates: Optional pre-fetched rates dict. If None, will fetch.

    Returns:
        Converted value, or None if conversion not possible.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return value

    # Fetch rates if not provided
    if rates is None:
        rates = fetch_exchange_rates([from_currency, to_currency])

    from_rate = rates.get(from_currency)
    to_rate = rates.get(to_currency)

    if from_rate is None or to_rate is None:
        return None

    # Convert: from_currency -> USD -> to_currency
    # value in from_currency * (USD per from_currency) = value in USD
    # value in USD / (USD per to_currency) = value in to_currency
    usd_value = value * from_rate
    return usd_value / to_rate


def format_with_currency(
    value: float | None,
    currency: str = "USD",
    abbreviate: bool = True,
    decimals: int = 2,
) -> str:
    """
    Format a value with the appropriate currency symbol.

    Args:
        value: The value to format
        currency: Currency code
        abbreviate: Use K/M/B/T suffixes for large numbers
        decimals: Number of decimal places

    Returns:
        Formatted string like "$1.23B" or "£45.67"
    """
    if value is None:
        return "N/A"

    currency = currency.upper()
    symbol = get_currency_symbol(currency)

    # Special handling for gold (XAU) - show as "XAU 0.52"
    if currency == "XAU":
        if abbreviate and abs(value) >= 1000:
            return f"XAU {value:,.0f}"
        return f"XAU {value:.{decimals}f}"

    # Handle large number abbreviation
    if abbreviate:
        abs_value = abs(value)
        if abs_value >= 1e12:
            return f"{symbol}{value / 1e12:.2f}T"
        if abs_value >= 1e9:
            return f"{symbol}{value / 1e9:.2f}B"
        if abs_value >= 1e6:
            return f"{symbol}{value / 1e6:.2f}M"
        if abs_value >= 1e3:
            return f"{symbol}{value / 1e3:.2f}K"

    # Standard formatting
    if abs(value) >= 100:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.{decimals}f}"


# Cache for exchange rates with TTL
_rate_cache: dict[str, tuple[float, float]] = {}  # currency -> (rate, timestamp)
_cache_ttl = 3600  # 1 hour default


def get_cached_rate(currency: str, ttl: int | None = None) -> float | None:
    """
    Get an exchange rate, using cache if available and fresh.

    Args:
        currency: Currency code
        ttl: Cache TTL in seconds (default 1 hour)

    Returns:
        Exchange rate or None if not available
    """
    currency = currency.upper()

    if currency == "USD":
        return 1.0

    if ttl is None:
        ttl = _cache_ttl

    # Check cache
    if currency in _rate_cache:
        rate, timestamp = _rate_cache[currency]
        if time.time() - timestamp < ttl:
            return rate

    # Fetch fresh rate
    rate = fetch_exchange_rate(currency)
    if rate is not None:
        _rate_cache[currency] = (rate, time.time())

    return rate


def clear_rate_cache() -> None:
    """Clear the in-memory rate cache."""
    _rate_cache.clear()


def get_all_cached_rates() -> dict[str, float]:
    """Get all currently cached rates."""
    now = time.time()
    return {currency: rate for currency, (rate, ts) in _rate_cache.items() if now - ts < _cache_ttl}


# List of all supported currencies for display
SUPPORTED_CURRENCIES = list(CURRENCY_SYMBOLS.keys())

# Default currency cycle for TUI toggle
DEFAULT_CURRENCY_CYCLE = ["USD", "EUR", "GBP", "JPY", "AUD", "ZAR", "XAU"]
