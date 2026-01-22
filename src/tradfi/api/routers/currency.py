"""Currency conversion and exchange rate endpoints."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from tradfi.core.currency import (
    CURRENCY_SYMBOLS,
    SUPPORTED_CURRENCIES,
    DEFAULT_CURRENCY_CYCLE,
    fetch_exchange_rate,
    fetch_exchange_rates,
    get_currency_symbol,
    clear_rate_cache,
    get_all_cached_rates,
)
from tradfi.utils.cache import (
    get_display_currency,
    set_display_currency,
    get_currency_rate_ttl,
    cache_currency_rate,
    get_all_cached_currency_rates,
    clear_currency_rates,
)

router = APIRouter(prefix="/currency", tags=["currency"])


class ExchangeRateSchema(BaseModel):
    """Exchange rate information."""
    currency: str
    rate_to_usd: float
    symbol: str


class CurrencyConfigSchema(BaseModel):
    """Currency configuration."""
    display_currency: str
    display_symbol: str
    available_currencies: list[str]
    currency_cycle: list[str]
    rate_ttl_seconds: int


class MessageSchema(BaseModel):
    """Simple message response."""
    message: str


@router.get("/rates", response_model=list[ExchangeRateSchema])
async def get_rates(
    currencies: str = Query(
        default=None,
        description="Comma-separated currency codes (e.g., EUR,GBP,JPY). If omitted, returns all cached rates.",
    )
):
    """
    Get exchange rates for specified currencies.

    Rates are returned as USD per 1 unit of the foreign currency.
    For example, EUR rate of 1.10 means 1 EUR = 1.10 USD.

    For gold (XAU), the rate is USD per troy ounce.
    """
    if currencies:
        currency_list = [c.strip().upper() for c in currencies.split(",")]
        rates = fetch_exchange_rates(currency_list)
    else:
        # Return all cached rates
        rates = get_all_cached_currency_rates()
        if not rates:
            # Fetch common currencies if cache is empty
            rates = fetch_exchange_rates(DEFAULT_CURRENCY_CYCLE)

    # Cache the rates in the database
    for currency, rate in rates.items():
        if currency != "USD":
            cache_currency_rate(currency, rate)

    return [
        ExchangeRateSchema(
            currency=currency,
            rate_to_usd=rate,
            symbol=get_currency_symbol(currency),
        )
        for currency, rate in rates.items()
    ]


@router.get("/rate/{currency}", response_model=ExchangeRateSchema)
async def get_rate(currency: str):
    """
    Get exchange rate for a single currency.

    Rate is returned as USD per 1 unit of the foreign currency.
    """
    currency = currency.upper()

    if currency == "USD":
        return ExchangeRateSchema(
            currency="USD",
            rate_to_usd=1.0,
            symbol="$",
        )

    rate = fetch_exchange_rate(currency)
    if rate is None:
        return ExchangeRateSchema(
            currency=currency,
            rate_to_usd=0.0,
            symbol=get_currency_symbol(currency),
        )

    # Cache the rate
    cache_currency_rate(currency, rate)

    return ExchangeRateSchema(
        currency=currency,
        rate_to_usd=rate,
        symbol=get_currency_symbol(currency),
    )


@router.post("/rates/refresh", response_model=list[ExchangeRateSchema])
async def refresh_rates():
    """
    Force refresh exchange rates for all currencies in the default cycle.

    Clears the in-memory cache and fetches fresh rates from yfinance.
    """
    # Clear caches
    clear_rate_cache()
    clear_currency_rates()

    # Fetch fresh rates for default currencies
    rates = fetch_exchange_rates(DEFAULT_CURRENCY_CYCLE)

    # Cache in database
    for currency, rate in rates.items():
        if currency != "USD":
            cache_currency_rate(currency, rate)

    return [
        ExchangeRateSchema(
            currency=currency,
            rate_to_usd=rate,
            symbol=get_currency_symbol(currency),
        )
        for currency, rate in rates.items()
    ]


@router.get("/config", response_model=CurrencyConfigSchema)
async def get_currency_config():
    """Get current currency configuration."""
    display_currency = get_display_currency()
    return CurrencyConfigSchema(
        display_currency=display_currency,
        display_symbol=get_currency_symbol(display_currency),
        available_currencies=SUPPORTED_CURRENCIES,
        currency_cycle=DEFAULT_CURRENCY_CYCLE,
        rate_ttl_seconds=get_currency_rate_ttl(),
    )


@router.put("/config", response_model=CurrencyConfigSchema)
async def update_currency_config(currency: str = Query(..., description="Currency code to set as default")):
    """Set the default display currency."""
    currency = currency.upper()

    if currency not in CURRENCY_SYMBOLS:
        # Allow it anyway, just use the code as the symbol
        pass

    set_display_currency(currency)

    return CurrencyConfigSchema(
        display_currency=currency,
        display_symbol=get_currency_symbol(currency),
        available_currencies=SUPPORTED_CURRENCIES,
        currency_cycle=DEFAULT_CURRENCY_CYCLE,
        rate_ttl_seconds=get_currency_rate_ttl(),
    )


@router.get("/symbols")
async def get_symbols():
    """Get all supported currency symbols."""
    return {
        currency: symbol
        for currency, symbol in CURRENCY_SYMBOLS.items()
    }
