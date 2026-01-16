"""Stock analysis endpoints."""

from fastapi import APIRouter, HTTPException, Query

from tradfi.api.converters import quarterly_trends_to_schema, stock_to_schema
from tradfi.api.schemas import (
    AnalyzeRequestSchema,
    QuarterlyTrendsSchema,
    StockSchema,
)
from tradfi.core.data import fetch_stock
from tradfi.core.quarterly import fetch_quarterly_financials

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}", response_model=StockSchema)
async def get_stock(
    ticker: str,
    use_cache: bool = Query(default=True, description="Use cached data if available"),
):
    """
    Get complete analysis for a single stock.

    Returns all valuation, profitability, technical, and fair value metrics.
    """
    stock = fetch_stock(ticker.upper(), use_cache=use_cache)
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
        raise HTTPException(
            status_code=404, detail=f"Quarterly data for {ticker} not found"
        )
    return quarterly_trends_to_schema(trends)
