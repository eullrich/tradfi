"""Stock analysis endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, Query

from tradfi.api.converters import quarterly_trends_to_schema, stock_to_schema
from tradfi.api.schemas import (
    AnalyzeRequestSchema,
    QuarterlyTrendsSchema,
    StockSchema,
)
from tradfi.core.data import fetch_stock, fetch_stocks_batch
from tradfi.core.quarterly import fetch_quarterly_financials

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}", response_model=StockSchema)
async def get_stock(
    ticker: str,
    use_cache: bool = Query(default=True, description="Use cached data if available"),
    cache_only: bool = Query(
        default=False, description="Only return cached data, never hit yfinance"
    ),
):
    """
    Get complete analysis for a single stock.

    Returns all valuation, profitability, technical, and fair value metrics.

    Use cache_only=true for fast responses from pre-cached data (e.g., TUI access).
    """
    stock = fetch_stock(ticker.upper(), use_cache=use_cache, cache_only=cache_only)
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    return stock_to_schema(stock)


@router.post("/analyze", response_model=list[StockSchema])
async def analyze_stocks(request: AnalyzeRequestSchema):
    """
    Analyze multiple stocks at once.

    Returns analysis for all valid tickers. Invalid tickers are skipped.
    """
    results = []
    for ticker in request.tickers:
        stock = fetch_stock(ticker.upper(), use_cache=True)
        if stock is not None:
            results.append(stock_to_schema(stock))
    return results


@router.get("/batch/all")
async def get_all_stocks():
    """
    Get all cached stocks in a single request.

    This is optimized for the TUI screener to fetch all stocks at once
    instead of making individual requests per ticker.

    Returns dict mapping ticker to stock data.
    """
    stocks = fetch_stocks_batch()
    result = {}
    for ticker, stock in stocks.items():
        try:
            result[ticker] = stock_to_schema(stock)
        except Exception:
            pass  # Skip stocks that fail schema conversion
    return result


@router.post("/batch")
async def get_stocks_batch(
    tickers: list[str],
    fetch_missing: bool = Query(
        default=False, description="Fetch missing tickers from yfinance if not in cache"
    ),
):
    """
    Get multiple stocks by ticker in a single request.

    Returns dict mapping ticker to stock data. Missing tickers are omitted.
    When fetch_missing=true, uncached tickers are fetched from yfinance.
    """
    if fetch_missing:
        # fetch_stock_from_api uses time.sleep for rate limiting - run in thread
        # to avoid blocking the async event loop
        stocks = await asyncio.to_thread(fetch_stocks_batch, tickers, fetch_missing=True)
    else:
        stocks = fetch_stocks_batch(tickers)
    result = {}
    for ticker, stock in stocks.items():
        try:
            result[ticker] = stock_to_schema(stock)
        except Exception:
            pass  # Skip stocks that fail schema conversion
    return result


@router.get("/{ticker}/quarterly", response_model=QuarterlyTrendsSchema)
async def get_quarterly_data(
    ticker: str,
    periods: int = Query(default=8, ge=1, le=20, description="Number of quarters"),
):
    """
    Get quarterly financial trends for a stock.

    Returns revenue, margins, EPS, and FCF data with trend analysis.
    """
    trends = fetch_quarterly_financials(ticker.upper(), periods=periods)
    if trends is None:
        raise HTTPException(status_code=404, detail=f"Quarterly data for {ticker} not found")
    return quarterly_trends_to_schema(trends)
