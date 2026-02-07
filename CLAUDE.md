# CLAUDE.md - TradFi Project Guide

## Project Overview

TradFi is a Python CLI tool for value investors to screen stocks and analyze companies using fundamental metrics combined with technical oversold indicators. Uses yfinance for market data with a remote-first architecture where the CLI communicates with a FastAPI backend.

## Tech Stack

- **Python 3.11+** - Primary language
- **Typer** - CLI framework with type hints
- **yfinance** - Market data (no API key required)
- **pandas** - Data processing
- **Rich** - Terminal formatting
- **Textual** - TUI (Terminal User Interface)
- **FastAPI** - REST API server
- **SQLite** - Caching and persistence
- **APScheduler** - Background refresh tasks
- **httpx** - HTTP client for remote API calls

## Project Structure

```
tradfi/
├── pyproject.toml
├── src/tradfi/
│   ├── cli.py                   # Main CLI entry point
│   ├── api.py                   # FastAPI server setup
│   ├── commands/
│   │   ├── analyze.py           # Stock analysis
│   │   ├── screen.py            # Stock screener
│   │   ├── quarterly.py         # Quarterly trends
│   │   ├── compare.py           # List comparison
│   │   ├── watchlist.py         # Watchlist management
│   │   ├── cache.py             # Cache management
│   │   └── lists.py             # List management
│   ├── core/
│   │   ├── data.py              # Stock data provider
│   │   ├── remote_provider.py   # API client for CLI
│   │   ├── portfolio.py         # Portfolio P&L tracking
│   │   ├── technical.py         # RSI, moving averages
│   │   ├── valuation.py         # Graham number, DCF
│   │   ├── screener.py          # Screening logic
│   │   ├── research.py          # SEC filing analysis
│   │   └── quarterly.py         # Quarterly data
│   ├── models/
│   │   └── stock.py             # Stock dataclass
│   ├── routers/                 # API route modules
│   │   ├── stocks.py
│   │   ├── screening.py
│   │   ├── lists.py
│   │   ├── cache.py
│   │   └── refresh.py
│   ├── tui/
│   │   └── app.py               # Textual TUI
│   └── utils/
│       ├── cache.py             # SQLite utilities
│       ├── display.py           # Rich formatting
│       └── sparkline.py         # ASCII sparklines
└── data/
    ├── sp500.txt                # S&P 500 (~500 stocks)
    ├── dow30.txt                # Dow 30
    ├── nasdaq100.txt            # NASDAQ 100
    ├── russell2000.txt          # Russell 2000 (~1,900 stocks)
    ├── sweetspot.txt            # $2-12B market cap (250 stocks)
    ├── etf.txt                  # ETFs with category headers
    ├── dividends.txt            # Dividend stocks
    └── value.txt                # Value stocks
```

## Key Commands

```bash
# Install
pip install -e .

# Core commands
tradfi                           # Launch TUI (default)
tradfi analyze AAPL              # Analyze single stock
tradfi screen                    # Screen with default criteria
tradfi screen --preset graham    # Use preset
tradfi quarterly AAPL            # 8 quarters of trends

# List management
tradfi list ls                   # Show all lists
tradfi list create picks AAPL,MSFT
tradfi list show picks
tradfi list add picks NVDA
tradfi list long AAPL            # Add to long list
tradfi list short TSLA           # Add to short list

# Portfolio tracking
tradfi list note picks AAPL --shares 100 --entry 150 --target 200

# Cache management
tradfi cache status
tradfi cache prefetch sp500 --delay 5

# API server
tradfi api                       # Start API on port 8000
tradfi serve --port 3000         # Legacy server command
```

## Screening Presets

Defined in `core/screener.py`:

**Value Presets:**
- **graham** - Benjamin Graham criteria (P/E < 15, P/B < 1.5)
- **buffett** - Quality + value (ROE > 15%, D/E < 0.5)
- **deep-value** - Low P/B < 1.0, P/E < 10
- **oversold-value** - Value + RSI < 35

**Income Presets:**
- **dividend** - High yield dividend stocks
- **dividend-growers** - Sustainable dividend payers

**Quality Presets:**
- **quality** - High ROE, strong margins
- **buyback** - Companies buying back shares

**Discovery Presets:**
- **fallen-angels** - Quality stocks down 30%+
- **turnaround** - Beaten down recovery plays
- **hidden-gems** - Small/mid cap quality
- **momentum-value** - Value with positive momentum
- **short-candidates** - Overvalued/weak fundamentals

## API Endpoints

The API uses modular routers with 25+ endpoints:

**Stocks** (`/api/v1/stocks`):
- `GET /{ticker}` - Single stock analysis
- `POST /analyze` - Batch analysis
- `GET /batch/all` - All cached stocks
- `GET /{ticker}/quarterly` - Quarterly data

**Screening** (`/api/v1/screening`):
- `GET /universes` - List universes
- `GET /presets` - List presets
- `POST /run` - Execute screen

**Lists** (`/api/v1/lists`):
- `GET/POST /` - List management
- `GET/DELETE /{name}` - Specific list
- `POST/DELETE /{name}/items` - Add/remove items
- `PUT /{name}/items/{ticker}/notes` - Update notes
- `GET/POST /categories` - Category management

**Cache** (`/api/v1/cache`):
- `GET /stats` - Cache statistics
- `POST /clear` - Clear cache
- `GET /sectors` - Sector list

**Refresh** (`/api/v1/refresh`):
- `GET /status` - Refresh status
- `POST /{universe}` - Trigger background refresh
- `GET /health` - Health check

## TUI Keybindings

**Navigation:**
- **Space** - Open action menu
- **/** - Search ticker
- **u** - Filter by universe
- **f** - Filter by sector
- **c** - Clear filters
- **Enter** - Select item
- **Escape** - Go back
- **q** - Quit

**Actions:**
- **r** - Refresh/run screen
- **s** - Save list
- **C** - Clear cache
- **R** - Resync universes
- **?** - Show shortcuts

**Discovery Presets:**
- **F** - Fallen Angels
- **H** - Hidden Gems
- **T** - Turnaround Candidates
- **M** - Momentum + Value
- **D** - Dividend Growers

**Sort (number keys):**
- 0-9, i - Various sort options (P/E, P/B, ROE, RSI, etc.)

## Database Schema

SQLite at `~/.tradfi/cache.db`:

**Core Tables:**
- `stock_cache` - Cached stock data with TTL
- `watchlist` - User watchlist
- `alerts` - Price alerts

**List Tables:**
- `saved_lists` - User-created lists
- `saved_list_items` - List contents
- `list_categories` - List organization
- `list_category_membership` - List-to-category links
- `list_item_notes` - Notes with position tracking (shares, entry, target, thesis)
- `smart_lists` - Auto-updating lists with saved criteria

**User Tables:**
- `users` - Passwordless email auth
- `auth_tokens` - Magic link and session tokens
- `user_watchlist` - User-scoped watchlists
- `user_saved_lists` - User-scoped lists
- `user_saved_list_items` - User-scoped list items

## Development

```bash
# Testing
pytest

# Linting
ruff check .
ruff format .
```

**Guidelines:**
- All functions need type annotations
- Handle missing yfinance data gracefully (fields can return None)
- Use `tradfi cache clear` to reset cache during development

## Deep Research

Analyzes SEC filings (10-K, 10-Q) using LLMs:

```bash
# OpenRouter (free models available)
export OPENROUTER_API_KEY=sk-or-v1-...

# Or Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...
```

Auto-detects provider based on available environment variables.

## Self-Improvement Rules

Claude must follow these rules to maintain and improve project knowledge automatically:

- **On correction**: When you make a mistake and are corrected, immediately update this CLAUDE.md with a concise rule under a `## Learned Rules` section to prevent that class of mistake in the future.
- **On pattern discovery**: When you discover a codebase pattern not documented here (e.g., naming conventions, error handling idioms, data flow patterns), add it to the relevant section of this file.
- **On failure recovery**: When a command, test, or workflow fails and you find the fix, document it under `## Development` or a `## Gotchas` section.
- **On reconnaissance**: Before implementing any non-trivial feature, find 2 similar examples in the repo and explain the pattern. Then follow that pattern.
- **Keep it lean**: Rules should be concise and actionable. Delete rules that become outdated or redundant. This file should never exceed ~300 lines.

## Memory

- Maintain cross-session learnings in auto-memory at `/root/.claude/projects/-home-user-tradfi/memory/MEMORY.md`
- After completing any non-trivial task, record what worked, what didn't, and codebase-specific insights in memory.
- Create topic-specific files (e.g., `yfinance-gotchas.md`, `tui-patterns.md`) for detailed notes and link them from MEMORY.md.

## Learned Rules

_This section is auto-maintained by Claude. Rules are added when mistakes are corrected._
