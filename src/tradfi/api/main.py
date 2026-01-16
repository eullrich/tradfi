"""FastAPI application for TradFi."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradfi.api.routers import cache, lists, screening, stocks, watchlist

app = FastAPI(
    title="TradFi API",
    description="""
Value investing API for screening stocks and analyzing companies
using fundamental metrics combined with technical oversold indicators.

## Features

- **Stock Analysis**: Get complete fundamental and technical analysis for any stock
- **Screening**: Filter stocks using preset strategies (Graham, Buffett, etc.) or custom criteria
- **Quarterly Trends**: View quarterly financial data with trend analysis
- **Lists**: Create and manage stock lists with notes and categories
- **Watchlist**: Track stocks you're monitoring

## Data Source

Data is fetched from yfinance (Yahoo Finance) and cached locally.
No API key required.
""",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow all origins by default for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stocks.router, prefix="/api/v1")
app.include_router(screening.router, prefix="/api/v1")
app.include_router(lists.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(cache.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "TradFi API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "stocks": "/api/v1/stocks/{ticker}",
            "screening": "/api/v1/screening/run",
            "lists": "/api/v1/lists",
            "watchlist": "/api/v1/watchlist",
            "cache": "/api/v1/cache/stats",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
