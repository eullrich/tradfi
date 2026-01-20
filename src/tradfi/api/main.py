"""FastAPI application for TradFi."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradfi.api.routers import cache, lists, refresh, screening, stocks, watchlist
from tradfi.api.scheduler import setup_scheduler, shutdown_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop scheduler."""
    logger.info("Starting TradFi API...")
    setup_scheduler()
    yield
    logger.info("Shutting down TradFi API...")
    shutdown_scheduler()


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
- **Scheduled Refresh**: Automatic daily refresh of stock data

## Data Source

Data is fetched from yfinance (Yahoo Finance) and cached locally.
No API key required.

## Scheduled Refresh

The API automatically refreshes stock data daily at 5 AM UTC.
Configure via environment variables:
- `TRADFI_REFRESH_HOUR`: Hour to run (default: 5)
- `TRADFI_REFRESH_UNIVERSES`: Comma-separated universes (default: dow30,nasdaq100,sp500)
- `TRADFI_REFRESH_ENABLED`: Set to "false" to disable
""",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
app.include_router(refresh.router, prefix="/api/v1")


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
            "refresh": "/api/v1/refresh/status",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint with cache and scheduler status."""
    from tradfi.api.scheduler import get_refresh_state
    from tradfi.utils.cache import get_cache_stats

    state = get_refresh_state()
    cache_stats = get_cache_stats()

    return {
        "status": "healthy",
        "cache": {
            "total_stocks": cache_stats["total_cached"],
            "fresh": cache_stats["fresh"],
            "stale": cache_stats["stale"],
        },
        "refresh": {
            "last_refresh": state["last_refresh"],
            "is_running": state["is_running"],
        },
    }
