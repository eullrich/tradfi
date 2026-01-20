# CLAUDE.md - TradFi Project Guide

## Project Overview

TradFi is a Python CLI tool for value investors to screen stocks and analyze companies using fundamental metrics combined with technical oversold indicators. It uses yfinance for free market data access.

## Tech Stack

- **Python 3.11+** - Primary language
- **Typer** - CLI framework with type hints
- **yfinance** - Free market data (no API key required)
- **pandas** - Data processing
- **Rich** - Terminal formatting with tables/colors
- **Textual** - TUI (Terminal User Interface)
- **FastAPI** - REST API server
- **SQLite** - Caching and data persistence

## Project Structure

```
tradfi/
├── pyproject.toml           # Project config, dependencies, scripts
├── PLAN.md                  # Detailed implementation plan
├── src/tradfi/
│   ├── cli.py               # Main CLI entry point (Typer app)
│   ├── api.py               # FastAPI server for remote cache access
│   ├── commands/
│   │   ├── analyze.py       # Single stock analysis
│   │   ├── screen.py        # Stock screener with filters
│   │   ├── quarterly.py     # Quarterly financial trends
│   │   ├── compare.py       # List comparison command
│   │   ├── watchlist.py     # Watchlist management
│   │   ├── cache.py         # Cache management commands
│   │   └── lists.py         # Stock list management (with categories & notes)
│   ├── core/
│   │   ├── data.py          # Stock data (cache-only mode, no live API calls)
│   │   ├── technical.py     # RSI, moving averages, 52W metrics
│   │   ├── valuation.py     # Graham number, DCF, P/E fair value
│   │   ├── screener.py      # Screening logic and presets
│   │   ├── research.py      # Research functionality
│   │   └── quarterly.py     # Quarterly data fetching from yfinance
│   ├── models/
│   │   └── stock.py         # Stock dataclass with all metrics + QuarterlyData/Trends
│   ├── tui/
│   │   └── app.py           # Textual TUI application (with action menu)
│   └── utils/
│       ├── cache.py         # SQLite caching utilities (lists, categories, notes)
│       ├── display.py       # Rich formatting helpers
│       └── sparkline.py     # ASCII sparkline generation
└── data/
    ├── sp500.txt            # S&P 500 tickers
    ├── dow30.txt            # Dow 30 tickers
    ├── nasdaq100.txt        # NASDAQ 100 tickers
    ├── russell2000.txt      # Russell 2000 tickers
    ├── sweetspot.txt        # $2-12B market cap stocks
    ├── etf.txt              # ETFs with category headers (REITs, Commodities, Sectors, International)
    ├── dividends.txt        # Dividend stocks
    └── value.txt            # Value-focused stocks
```

## Available Universes

The following universes are available for screening:
- **sp500** - S&P 500 (~500 large-cap US stocks)
- **dow30** - Dow Jones Industrial Average (30 stocks)
- **nasdaq100** - NASDAQ-100 (100 largest NASDAQ stocks)
- **russell2000** - Russell 2000 sample (~200 small-cap stocks)
- **sweetspot** - $2-12B market cap sweet spot (under-followed + fallen angels)
- **etf** - ETFs with categories: REITs, Commodities, Sectors, International
- **dividends** - Dividend Aristocrats & high-yield stocks
- **value** - Value-focused stocks and ETFs

### ETF Categories

The `etf` universe supports category filtering. Categories are defined in `data/etf.txt` using `## Category` headers:
- **REITs** - Real Estate Investment Trusts
- **Commodities** - Gold, silver, oil, agriculture ETFs
- **Sectors** - Technology, healthcare, financials sector ETFs
- **International** - Country ETFs and ADRs

In the TUI, when you select the `etf` universe, a category filter appears allowing you to filter by specific ETF types.

## Key Commands

```bash
# Install in development mode
pip install -e .

# Core commands
tradfi                       # Launch TUI (default)
tradfi ui                    # Launch TUI explicitly
tradfi analyze AAPL          # Analyze single stock
tradfi screen                # Screen with default criteria
tradfi screen --preset graham    # Use Graham preset
tradfi screen --rsi-max 30       # Filter by oversold RSI

# Quarterly analysis
tradfi quarterly AAPL            # Show 8 quarters of financial trends
tradfi quarterly AAPL --periods 12   # Show more quarters
tradfi quarterly AAPL MSFT --compare # Compare two stocks

# List comparison
tradfi compare my-longs my-shorts    # Compare two lists
tradfi compare my-picks --metrics pe,roe,mos  # Single list with custom metrics

# List management
tradfi list ls                   # Show all saved lists
tradfi list create my-picks AAPL,MSFT,GOOGL  # Create a list
tradfi list show my-picks        # View list contents
tradfi list add my-picks NVDA    # Add ticker to list
tradfi list remove my-picks MSFT # Remove ticker from list
tradfi list long AAPL            # Add to long list
tradfi list short TSLA           # Add to short list

# List categories
tradfi list category create "Value Picks" --icon "💎"
tradfi list category ls          # List all categories
tradfi list move my-picks "Value Picks"  # Move list to category

# List notes
tradfi list note my-picks AAPL "Strong moat, waiting for pullback"
tradfi list note my-picks AAPL --thesis "Services growth" --target 200 --entry 165
tradfi list notes my-picks       # Show all notes in list

# Cache management
tradfi cache status          # Show cache stats and last updated time
tradfi cache prefetch sp500  # Prefetch stocks from yfinance to cache
tradfi cache prefetch dow30 --delay 5  # Prefetch with custom rate limit
tradfi cache clear           # Clear cached data

# API server (for remote cache access)
tradfi serve                 # Start API server on port 8000
tradfi serve --port 3000     # Start on custom port

# Utilities
tradfi watchlist add AAPL    # Add to watchlist
```

## Core Data Models

The `Stock` dataclass in `models/stock.py` contains:
- **ValuationMetrics**: P/E, P/B, P/S, PEG, EV/EBITDA, market cap
- **ProfitabilityMetrics**: margins, ROE, ROA
- **FinancialHealth**: current ratio, debt/equity, FCF
- **GrowthMetrics**: revenue/earnings growth
- **DividendInfo**: yield, payout ratio
- **TechnicalIndicators**: RSI, MAs, 52W metrics, returns
- **FairValueEstimates**: Graham number, DCF, margin of safety
- **BuybackInfo**: ownership, FCF yield

### Quarterly Data Models
- **QuarterlyData**: Single quarter snapshot (revenue, net income, margins, EPS, FCF)
- **QuarterlyTrends**: Container with trend analysis properties (revenue_trend, margin_trend, qoq_growth)

## Screening Presets

Defined in `core/screener.py`:
- **graham**: Benjamin Graham criteria (P/E < 15, P/B < 1.5, etc.)
- **buffett**: Quality + value (ROE > 15%, D/E < 0.5)
- **deep-value**: Low P/B < 1.0, P/E < 10
- **oversold-value**: Value + RSI < 35

## Development Guidelines

1. **Testing**: Run `pytest` from project root
2. **Linting**: Use `ruff check .` and `ruff format .`
3. **Type hints**: All functions should have type annotations
4. **Error handling**: Handle missing yfinance data gracefully (many fields return None)
5. **Caching**: Data is cached in SQLite; use `tradfi cache clear` to reset

## Deep Research (SEC Filing Analysis)

The deep research feature analyzes SEC filings (10-K, 10-Q) using an LLM. Supports two providers:

### OpenRouter (Recommended - Free Models Available)
```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```
Uses `deepseek/deepseek-r1:free` by default (free, no cost).

### Anthropic Claude
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```
Uses `claude-sonnet-4-20250514` (paid).

The system auto-detects which provider to use based on available environment variables. OpenRouter is checked first, then Anthropic.

## Cache-Only Mode (Railway Deployment)

The app runs in **cache-only mode** - it never hits the yfinance API during normal operation. All stock data is served from the SQLite cache for fast, consistent performance.

To populate the cache, use the prefetch command:
```bash
tradfi cache prefetch sp500 --delay 5   # Prefetch S&P 500
tradfi cache prefetch all --delay 10    # Prefetch all universes
```

Rate limiting (2s delay by default) only applies during prefetch operations.

## API Server

Start the API server for remote cache access:
```bash
tradfi serve --port 8000
```

### Endpoints

- `GET /api/cache/status` - Cache stats and last updated time
- `GET /health` - Health check

Example response from `/api/cache/status`:
```json
{
  "total_cached": 500,
  "fresh": 450,
  "stale": 50,
  "cache_ttl_minutes": 30,
  "last_updated": "2024-01-15T10:30:00",
  "last_updated_ago": "2h ago"
}
```

## Signal Logic

Stock signals are generated in `models/stock.py`:
- **STRONG_BUY**: Value criteria met + RSI < 20
- **BUY**: Value criteria met + RSI < 30 OR within 10% of 52W low
- **WATCH**: Value criteria met + RSI 30-40 OR within 20% of 52W low
- **NEUTRAL**: Value criteria met, not oversold

## TUI Usage

The TUI has been simplified for easier navigation:

### Essential Keybindings
- **Space** - Open action menu (all commands organized by category)
- **/** - Search for ticker
- **r** - Refresh / Run screen
- **Enter** - Select item
- **Escape** - Go back
- **q** - Quit

### Action Menu Categories
- **Navigate**: Search, Filter by Universe/Industry, Clear filters
- **Sort By**: P/E, Price, RSI, Margin of Safety, etc.
- **Actions**: Refresh, Save list
- **View**: Help, Stock detail, Quarterly trends

### Category Filtering
When selecting a single universe that has categories (like `etf`), a category filter appears in the sidebar. Select one or more categories to filter the results.

### Simplified Data Table
Default columns: `Ticker | Price | P/E | ROE | RSI | MoS% | Div | Signal`

## Database Schema

SQLite database at `~/.tradfi/cache.db` contains:
- **stock_cache**: Cached stock data with TTL
- **saved_lists**: User-created stock lists
- **list_categories**: Categories for organizing lists
- **list_category_membership**: List-to-category assignments
- **list_item_notes**: Enhanced notes with thesis, entry/target prices
