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
- **SQLite** - Caching and data persistence

## Project Structure

```
tradfi/
├── pyproject.toml           # Project config, dependencies, scripts
├── PLAN.md                  # Detailed implementation plan
├── src/tradfi/
│   ├── cli.py               # Main CLI entry point (Typer app)
│   ├── commands/
│   │   ├── analyze.py       # Single stock analysis
│   │   ├── screen.py        # Stock screener with filters
│   │   ├── quarterly.py     # Quarterly financial trends
│   │   ├── compare.py       # List comparison command
│   │   ├── watchlist.py     # Watchlist management
│   │   ├── cache.py         # Cache management commands
│   │   └── lists.py         # Stock list management (with categories & notes)
│   ├── core/
│   │   ├── data.py          # yfinance data fetching with caching
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
    └── [other lists].txt    # Sector/thematic lists
```

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

# Utilities
tradfi watchlist add AAPL    # Add to watchlist
tradfi cache clear           # Clear cached data
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

## API Rate Limiting

yfinance has no official rate limits, but the code implements a configurable delay between requests (see `utils/cache.py` for config). Cached data has a configurable TTL.

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

### Simplified Data Table
Default columns: `Ticker | Price | P/E | ROE | RSI | MoS% | Div | Signal`

## Database Schema

SQLite database at `~/.tradfi/cache.db` contains:
- **stock_cache**: Cached stock data with TTL
- **saved_lists**: User-created stock lists
- **list_categories**: Categories for organizing lists
- **list_category_membership**: List-to-category assignments
- **list_item_notes**: Enhanced notes with thesis, entry/target prices
