# CLAUDE.md - TradFi Project Guide

## Project Overview

TradFi is a Python CLI tool for value investors to screen stocks and analyze companies using fundamental metrics combined with technical oversold indicators. Uses yfinance for market data with a remote-first architecture where the CLI communicates with a FastAPI backend. Supports international markets (40+ exchanges), currency conversion, user authentication, and portfolio P&L tracking.

## Tech Stack

- **Python 3.11+** - Primary language (runtime.txt pins 3.11.7)
- **Typer** - CLI framework with type hints
- **yfinance** - Market data (no API key required)
- **pandas** - Data processing
- **Rich** - Terminal formatting
- **Textual** - TUI (Terminal User Interface)
- **FastAPI** - REST API server
- **SQLite** - Caching and persistence
- **APScheduler** - Background refresh tasks
- **httpx** - HTTP client for remote API calls
- **email-validator** - Email validation for passwordless auth

## Project Structure

```
tradfi/
├── pyproject.toml
├── railway.json               # Railway deployment config
├── nixpacks.toml              # Nixpacks build config
├── Procfile                   # Heroku/Railway process file
├── runtime.txt                # Python version (3.11.7)
├── server.py                  # Railway entry point
├── src/tradfi/
│   ├── cli.py                 # Main CLI entry point
│   ├── api.py                 # User-authenticated API (auth, portfolio, user-scoped data)
│   ├── api/
│   │   ├── main.py            # Primary FastAPI app (/api/v1 endpoints)
│   │   ├── auth.py            # Admin API key authentication
│   │   ├── converters.py      # Dataclass-to-schema converters
│   │   ├── scheduler.py       # APScheduler background refresh
│   │   ├── schemas.py         # Pydantic request/response models
│   │   └── routers/
│   │       ├── stocks.py      # Stock analysis endpoints
│   │       ├── screening.py   # Screening endpoints
│   │       ├── lists.py       # List management endpoints
│   │       ├── cache.py       # Cache management endpoints
│   │       ├── refresh.py     # Background refresh endpoints
│   │       ├── currency.py    # Currency conversion endpoints
│   │       └── watchlist.py   # Watchlist endpoints
│   ├── commands/
│   │   ├── analyze.py         # Stock analysis
│   │   ├── screen.py          # Stock screener
│   │   ├── quarterly.py       # Quarterly trends
│   │   ├── compare.py         # List comparison
│   │   ├── watchlist.py       # Watchlist management
│   │   ├── cache.py           # Cache management
│   │   └── lists.py           # List management
│   ├── core/
│   │   ├── data.py            # Stock data provider
│   │   ├── remote_provider.py # API client for CLI
│   │   ├── portfolio.py       # Portfolio P&L tracking
│   │   ├── technical.py       # RSI, moving averages
│   │   ├── valuation.py       # Graham number, DCF
│   │   ├── screener.py        # Screening logic
│   │   ├── research.py        # SEC filing analysis
│   │   ├── quarterly.py       # Quarterly data
│   │   └── currency.py        # Currency conversion service
│   ├── models/
│   │   └── stock.py           # Stock dataclass
│   ├── tui/
│   │   └── app.py             # Textual TUI
│   └── utils/
│       ├── cache.py           # SQLite utilities
│       ├── display.py         # Rich formatting
│       └── sparkline.py       # ASCII sparklines
├── tests/
│   ├── test_cache_refresh.py
│   ├── test_display.py
│   ├── test_models.py
│   ├── test_screener.py
│   ├── test_sparkline.py
│   ├── test_technical.py
│   └── test_valuation.py
└── data/                      # Universe/list files (43 total)
    ├── sp500.txt              # S&P 500 (~500 stocks)
    ├── dow30.txt              # Dow 30
    ├── nasdaq100.txt          # NASDAQ 100
    ├── nasdaq.txt             # NASDAQ Composite (~3,100 stocks)
    ├── russell2000.txt        # Russell 2000 (~1,900 stocks)
    ├── sweetspot.txt          # $2-12B market cap (250 stocks)
    ├── etf.txt                # ETFs with category headers
    ├── dividends.txt          # Dividend stocks
    ├── value.txt              # Value stocks
    ├── # International markets (see below)
    └── ...
```

### International Market Universes

**Europe:** uk.txt, germany.txt, france.txt, switzerland.txt, netherlands.txt, spain.txt, italy.txt, belgium.txt, austria.txt, portugal.txt, europe.txt (aggregate)

**Nordics:** sweden.txt, norway.txt, denmark.txt, finland.txt

**Asia-Pacific:** japan.txt, hongkong.txt, china.txt, korea.txt, taiwan.txt, india.txt, singapore.txt, australia.txt, newzealand.txt, asia.txt (aggregate)

**Emerging Markets:** brazil.txt, mexico.txt, southafrica.txt, indonesia.txt, thailand.txt, malaysia.txt, israel.txt, turkey.txt, emerging.txt (aggregate)

## Environment Variables

```bash
# Security
TRADFI_ADMIN_KEY              # API key for protected admin endpoints (X-Admin-Key header)
TRADFI_CORS_ORIGINS           # CORS allowed origins (disabled by default; use * for dev)

# Connection
TRADFI_API_URL                # Remote API URL for CLI/TUI to connect to

# Paths
TRADFI_DATA_DIR               # Custom data directory path
TRADFI_DB_PATH                # Custom database path
TRADFI_CONFIG_PATH            # Custom config path

# Cache
TRADFI_CACHE_TTL              # Cache TTL in seconds

# Scheduler
TRADFI_REFRESH_ENABLED        # Enable/disable background refresh (default: true)
TRADFI_REFRESH_HOUR           # Hour for scheduled refresh (default: 5)
TRADFI_REFRESH_MINUTE         # Minute for scheduled refresh (default: 0)
TRADFI_REFRESH_UNIVERSES      # Comma-separated universes to refresh
TRADFI_REFRESH_DELAY          # Delay between API calls (default: 2.0 seconds)

# Mode
TRADFI_PRODUCTION             # Production mode (hides magic link tokens in logs)

# Deep Research (LLM providers)
OPENROUTER_API_KEY            # OpenRouter API key (free models available)
ANTHROPIC_API_KEY             # Anthropic Claude API key
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

## API Architecture

The project has two API layers:

### Primary API (`api/main.py` - `/api/v1`)

The main API uses modular routers with admin key protection on write operations.

**Stocks** (`/api/v1/stocks`):
- `GET /{ticker}` - Single stock analysis
- `POST /analyze` - Batch analysis
- `POST /batch` - Batch fetch by ticker list
- `GET /batch/all` - All cached stocks
- `GET /{ticker}/quarterly` - Quarterly data

**Screening** (`/api/v1/screening`):
- `GET /universes` - List universes
- `GET /presets` - List presets
- `GET /presets/{name}` - Get specific preset
- `POST /run` - Execute screen

**Lists** (`/api/v1/lists`):
- `GET/POST /` - List management
- `GET/DELETE /{name}` - Specific list
- `POST/DELETE /{name}/items` - Add/remove items
- `PUT /{name}/items/{ticker}/notes` - Update notes
- `GET/POST /categories` - Category management

**Watchlist** (`/api/v1/watchlist`):
- `GET /` - Get all watchlist items
- `POST /` - Add to watchlist
- `DELETE /{ticker}` - Remove from watchlist
- `PUT /{ticker}/notes` - Update notes

**Currency** (`/api/v1/currency`):
- `GET /rates` - Get exchange rates
- `GET /rate/{currency}` - Single currency rate
- `POST /rates/refresh` - Force refresh rates
- `GET /config` - Get currency configuration
- `PUT /config` - Set default display currency
- `GET /symbols` - All supported currency symbols

**Cache** (`/api/v1/cache`):
- `GET /stats` - Cache statistics
- `POST /clear` - Clear cache (admin key required)
- `GET /sectors` - Sector list

**Refresh** (`/api/v1/refresh`):
- `GET /status` - Refresh status
- `GET /universes` - Statistics for all universes
- `POST /{universe}` - Trigger background refresh (admin key required)
- `GET /health` - Health check

### User-Authenticated API (`api.py` - `/api`)

Separate API with passwordless email auth and user-scoped data.

**Auth** (`/api/auth`):
- `POST /register` - Register with email
- `POST /verify` - Verify magic link token
- `POST /logout` - Revoke session
- `GET /me` - Current user info

**User Watchlist** (`/api/watchlist`):
- `GET/POST /` - User-scoped watchlist
- `DELETE /{ticker}` - Remove
- `PATCH /{ticker}` - Update notes

**User Lists** (`/api/lists`):
- `GET/POST /` - User-scoped lists
- `GET/DELETE /{list_name}` - Specific list
- `GET/POST /{list_name}/items` - List items
- `DELETE /{list_name}/items/{ticker}` - Remove item
- `PATCH /{list_name}/items/{ticker}` - Update notes

**Portfolio** (`/api/lists/{list_name}`):
- `PUT /items/{ticker}/position` - Set position (shares, entry, target)
- `GET /items/{ticker}/position` - Get position
- `DELETE /items/{ticker}/position` - Clear position
- `GET /portfolio` - Full portfolio with P&L calculations
- `GET /has-positions` - Check if list has positions

## Security

- **Admin endpoints** require `X-Admin-Key` header matching `TRADFI_ADMIN_KEY` env var
- **CORS** is disabled by default; set `TRADFI_CORS_ORIGINS` to enable (use specific origins in production)
- **User auth** uses passwordless magic links with session tokens
- **Production mode** (`TRADFI_PRODUCTION=true`) hides magic link tokens from API responses

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
- `currency_rates` - Cached exchange rates with TTL

**List Tables:**
- `saved_lists` - User-created lists
- `saved_list_items` - List contents with position tracking (shares, entry, target)
- `list_categories` - List organization
- `list_category_membership` - List-to-category links
- `list_item_notes` - Notes with thesis
- `smart_lists` - Auto-updating lists with saved screening criteria

**User Tables:**
- `users` - Passwordless email auth
- `auth_tokens` - Magic link and session tokens with expiry
- `user_watchlist` - User-scoped watchlists
- `user_saved_lists` - User-scoped lists
- `user_saved_list_items` - User-scoped list items with position tracking

## Deployment

Supports multiple deployment targets:
- **Railway** (primary) - `railway.json` + `server.py` entry point
- **Nixpacks** - `nixpacks.toml` build config
- **Heroku** - `Procfile`
- **Local** - `tradfi api` or `tradfi serve`

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
- Admin endpoints need `TRADFI_ADMIN_KEY` set for local testing

## Deep Research

Analyzes SEC filings (10-K, 10-Q) using LLMs:

```bash
# OpenRouter (free models available)
export OPENROUTER_API_KEY=sk-or-v1-...

# Or Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...
```

Auto-detects provider based on available environment variables.

## Currency Conversion

Supports 30+ currencies via yfinance forex data:
- USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD, and more
- Gold pricing (XAU)
- Configurable default display currency
- Rates cached in SQLite with TTL
