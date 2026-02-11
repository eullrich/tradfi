"""HTMX partial routes for the web frontend.

These routes return HTML fragments (not full pages) for HTMX to swap
into the DOM. All routes require authentication.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from tradfi.web.dependencies import get_current_user
from tradfi.web.routes import PROFILE_DISPLAY_NAMES, PROFILE_ORDER, _run_screener, templates

router = APIRouter(tags=["partials"])


@router.get("/screener/results", response_class=HTMLResponse)
async def screener_results(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    universe: str = Query("sp500"),
    preset: str | None = Query(None),
    sort: str = Query("ticker"),
    dir: str = Query("asc"),
    profile: str = Query("overview"),
    search: str | None = Query(None),
) -> HTMLResponse:
    """Return the screener table body as an HTMX partial.

    This endpoint is called by HTMX when the user changes filters, sort
    order, or search terms. It returns just the ``<tbody>`` content for
    the screener table.

    Args:
        request: The incoming request.
        user: Authenticated user from session cookie.
        universe: Stock universe to screen.
        preset: Optional screening preset name.
        sort: Sort column key.
        dir: Sort direction ('asc' or 'desc').
        profile: Column profile to display.
        search: Optional ticker/name search filter.

    Returns:
        HTML partial with table body rows.
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
        "profiles": PROFILE_DISPLAY_NAMES,
        "profile_order": PROFILE_ORDER,
        "total_count": len(stocks),
    }

    return templates.TemplateResponse("partials/screener_tbody.html", context)
