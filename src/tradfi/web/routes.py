"""Page routes for the web frontend.

Serves full HTML pages using Jinja2 templates. All routes except the
entrance page require authentication via the session cookie.
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from tradfi.core.data import fetch_stock, fetch_stocks_batch
from tradfi.core.screener import (
    AVAILABLE_UNIVERSES,
    PRESET_INFO,
    PRESET_SCREENS,
    get_preset_screen,
    load_tickers,
    screen_stock,
)
from tradfi.models.stock import Stock
from tradfi.utils.cache import (
    user_get_list,
    user_get_list_items,
    user_get_lists,
    user_get_watchlist,
)
from tradfi.utils.cache import validate_session_token
from tradfi.web.dependencies import get_current_user

router = APIRouter(tags=["pages"])

# Template directory lives alongside the web module's parent package
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


# ============================================================================
# Sort Options
# ============================================================================
# Maps sort key strings to (extractor_fn, default_reverse, display_name).
# Reuses the same logic as the TUI's SORT_OPTIONS.

SORT_KEYS: dict[str, tuple[Callable, bool, str]] = {
    "ticker": (lambda s: s.ticker, False, "Ticker"),
    "sector": (lambda s: s.sector or "ZZZ", False, "Sector"),
    "price": (lambda s: s.current_price or 0, True, "Price"),
    "pe": (
        lambda s: (
            s.valuation.pe_trailing
            if s.valuation.pe_trailing and s.valuation.pe_trailing > 0
            else float("inf")
        ),
        False,
        "P/E",
    ),
    "pb": (
        lambda s: (
            s.valuation.pb_ratio
            if s.valuation.pb_ratio and s.valuation.pb_ratio > 0
            else float("inf")
        ),
        False,
        "P/B",
    ),
    "ev": (
        lambda s: (
            s.valuation.ev_ebitda
            if s.valuation.ev_ebitda and s.valuation.ev_ebitda > 0
            else float("inf")
        ),
        False,
        "EV/EBITDA",
    ),
    "roe": (
        lambda s: s.profitability.roe if s.profitability.roe is not None else float("-inf"),
        True,
        "ROE",
    ),
    "de": (
        lambda s: (
            s.financial_health.debt_to_equity / 100
            if s.financial_health.debt_to_equity is not None
            else float("inf")
        ),
        False,
        "D/E",
    ),
    "rsi": (
        lambda s: s.technical.rsi_14 if s.technical.rsi_14 is not None else float("inf"),
        False,
        "RSI",
    ),
    "mos": (
        lambda s: (
            s.fair_value.margin_of_safety_pct
            if s.fair_value.margin_of_safety_pct is not None
            else float("-inf")
        ),
        True,
        "MoS%",
    ),
    "div": (
        lambda s: s.dividends.dividend_yield if s.dividends.dividend_yield else 0,
        True,
        "Div Yield",
    ),
    "fcfy": (
        lambda s: s.buyback.fcf_yield_pct if s.buyback.fcf_yield_pct is not None else float("-inf"),
        True,
        "FCF Yield",
    ),
    "signal": (
        lambda s: {"STRONG_BUY": 0, "BUY": 1, "WATCH": 2, "NEUTRAL": 3}.get(s.signal, 4),
        False,
        "Signal",
    ),
}

# Available column profiles (matching TUI profiles)
PROFILE_ORDER: list[str] = ["overview", "value", "quality", "cashflow", "technical", "ownership"]

PROFILE_DISPLAY_NAMES: dict[str, str] = {
    "overview": "Overview",
    "value": "Value",
    "quality": "Quality",
    "cashflow": "Cash Flow",
    "technical": "Technical",
    "ownership": "Ownership",
}


# ============================================================================
# Shared Screening Logic
# ============================================================================


def _run_screener(
    universe: str = "sp500",
    preset: str | None = None,
    sort: str = "ticker",
    sort_dir: str = "asc",
    search: str | None = None,
) -> list[Stock]:
    """Run the stock screener and return filtered, sorted results.

    This is the shared logic used by both full page routes and HTMX partials.

    Args:
        universe: Universe to screen (e.g., 'sp500', 'dow30').
        preset: Optional screening preset name (e.g., 'graham', 'buffett').
        sort: Sort key (must be a key in SORT_KEYS).
        sort_dir: Sort direction, 'asc' or 'desc'.
        search: Optional search string to filter by ticker or company name.

    Returns:
        Sorted list of Stock objects passing all filters.
    """
    # Load tickers for the universe
    try:
        tickers = load_tickers(universe)
    except (FileNotFoundError, ValueError):
        tickers = load_tickers("sp500")

    # Fetch all cached stock data
    stocks_dict = fetch_stocks_batch(tickers)
    stocks: list[Stock] = list(stocks_dict.values())

    # Apply preset screening criteria
    if preset and preset in PRESET_SCREENS:
        criteria = get_preset_screen(preset)
        stocks = [s for s in stocks if screen_stock(s, criteria)]

    # Apply search filter
    if search:
        search_lower = search.lower()
        stocks = [
            s
            for s in stocks
            if search_lower in s.ticker.lower()
            or (s.name and search_lower in s.name.lower())
        ]

    # Sort
    sort_key_info = SORT_KEYS.get(sort, SORT_KEYS["ticker"])
    extractor, default_reverse, _name = sort_key_info

    if sort_dir == "desc":
        reverse = True
    elif sort_dir == "asc":
        reverse = False
    else:
        reverse = default_reverse

    stocks.sort(key=extractor, reverse=reverse)

    return stocks


# ============================================================================
# Page Routes
# ============================================================================


@router.get("/", response_class=HTMLResponse)
async def entrance(request: Request) -> HTMLResponse | RedirectResponse:
    """Render the entrance / login page.

    No authentication required. Redirects to /screener if already logged in.
    """
    token = request.cookies.get("session")
    if token and validate_session_token(token):
        return RedirectResponse(url="/screener", status_code=303)

    return templates.TemplateResponse(
        "entrance.html",
        {"request": request},
    )


@router.get("/screener", response_class=HTMLResponse)
async def screener(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    universe: str = Query("sp500"),
    preset: str | None = Query(None),
    sort: str = Query("ticker"),
    dir: str = Query("asc"),
    profile: str = Query("overview"),
    search: str | None = Query(None),
) -> HTMLResponse:
    """Render the stock screener page.

    When the HX-Request header is present (HTMX request), returns only
    the partial table body. Otherwise returns the full page.

    Args:
        request: The incoming request.
        user: Authenticated user from session cookie.
        universe: Stock universe to screen.
        preset: Optional screening preset.
        sort: Sort column key.
        dir: Sort direction ('asc' or 'desc').
        profile: Column profile to display.
        search: Optional ticker/name search filter.
    """
    stocks = _run_screener(
        universe=universe,
        preset=preset,
        sort=sort,
        sort_dir=dir,
        search=search,
    )

    # Ensure profile is valid
    if profile not in PROFILE_ORDER:
        profile = "overview"

    context = {
        "request": request,
        "user": user,
        "stocks": stocks,
        "universe": universe,
        "preset": preset,
        "sort": sort,
        "dir": dir,
        "profile": profile,
        "search": search or "",
        "universes": AVAILABLE_UNIVERSES,
        "presets": PRESET_INFO,
        "profiles": PROFILE_DISPLAY_NAMES,
        "profile_order": PROFILE_ORDER,
        "total_count": len(stocks),
    }

    return templates.TemplateResponse("screener.html", context)


@router.get("/stock/{ticker}", response_class=HTMLResponse)
async def stock_detail(
    request: Request,
    ticker: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> HTMLResponse:
    """Render the stock detail page.

    Fetches full stock data from cache and renders the detail view.

    Args:
        request: The incoming request.
        ticker: Stock ticker symbol (e.g., 'AAPL').
        user: Authenticated user from session cookie.
    """
    stock = fetch_stock(ticker.upper())

    return templates.TemplateResponse(
        "stock_detail.html",
        {
            "request": request,
            "user": user,
            "stock": stock,
            "ticker": ticker.upper(),
        },
    )


@router.get("/lists", response_class=HTMLResponse)
async def lists_page(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
) -> HTMLResponse:
    """Render the saved lists overview page.

    Shows all lists owned by the current user.

    Args:
        request: The incoming request.
        user: Authenticated user from session cookie.
    """
    user_lists = user_get_lists(user["id"])

    return templates.TemplateResponse(
        "lists.html",
        {
            "request": request,
            "user": user,
            "lists": user_lists or [],
        },
    )


@router.get("/lists/{name}", response_class=HTMLResponse)
async def list_detail(
    request: Request,
    name: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> HTMLResponse:
    """Render a specific saved list's detail page.

    Shows the list metadata and all items with their stock data.

    Args:
        request: The incoming request.
        name: List name.
        user: Authenticated user from session cookie.
    """
    list_info = user_get_list(user["id"], name)
    items = user_get_list_items(user["id"], name) if list_info else None

    # Fetch stock data for all tickers in the list
    stocks: dict[str, Stock] = {}
    if items:
        tickers = [item["ticker"] for item in items]
        stocks = fetch_stocks_batch(tickers)

    return templates.TemplateResponse(
        "list_detail.html",
        {
            "request": request,
            "user": user,
            "list_info": list_info,
            "list_name": name,
            "items": items or [],
            "stocks": stocks,
        },
    )


@router.get("/watchlist", response_class=HTMLResponse)
async def watchlist_page(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
) -> HTMLResponse:
    """Render the user's watchlist page.

    Shows all tickers on the watchlist with their current stock data.

    Args:
        request: The incoming request.
        user: Authenticated user from session cookie.
    """
    items = user_get_watchlist(user["id"])

    # Fetch stock data for all watched tickers
    stocks: dict[str, Stock] = {}
    if items:
        tickers = [item["ticker"] for item in items]
        stocks = fetch_stocks_batch(tickers)

    return templates.TemplateResponse(
        "watchlist.html",
        {
            "request": request,
            "user": user,
            "items": items or [],
            "stocks": stocks,
        },
    )
