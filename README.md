# TradFi

A Python CLI tool for value investors to screen stocks and analyze companies using fundamental metrics combined with technical oversold indicators.

## Features

- **Stock Screening** - Filter stocks by value metrics (P/E, P/B, ROE) and technical indicators (RSI, 52W highs/lows)
- **Single Stock Analysis** - Deep dive into individual companies with valuation and profitability metrics
- **Quarterly Trends** - View 8+ quarters of financial data with trend analysis
- **List Management** - Create and organize watchlists with categories and notes
- **Portfolio Tracking** - Track positions with P&L, cost basis, target prices, and allocation
- **International Markets** - Screen stocks across 40+ universes covering 30+ countries with currency conversion
- **Interactive TUI** - Terminal UI with sector heatmaps, scatter plots, and discovery presets
- **REST API** - FastAPI server with 30+ endpoints, scheduled refresh, and admin auth
- **Free Data** - Uses yfinance for market data (no API key required)

## Installation

Requires Python 3.11+

```bash
# Clone the repository
git clone https://github.com/eullrich/tradfi.git
cd tradfi

# Install in development mode
pip install -e .
```

## Quick Start

```bash
# Launch the interactive TUI
tradfi

# Analyze a single stock
tradfi analyze AAPL

# Screen stocks with default criteria
tradfi screen

# Screen with a preset (graham, buffett, dividend, fallen-angels, hidden-gems, oversold, turnaround)
tradfi screen --preset graham

# View quarterly financial trends
tradfi quarterly AAPL
```

## Available Universes

### US Markets

| Universe | Description |
|----------|-------------|
| `sp500` | S&P 500 (~500 large-cap US stocks) |
| `dow30` | Dow Jones Industrial Average (30 stocks) |
| `nasdaq100` | NASDAQ-100 (100 largest NASDAQ stocks) |
| `nasdaq` | NASDAQ Composite (~3,100 NASDAQ-listed stocks) |
| `russell2000` | Russell 2000 sample (~200 small-cap stocks) |
| `etf` | ETFs (REITs, Commodities, Sectors, International) |

### International Markets

Screen stocks globally across 35 country and regional universes:

| Universe | Description |
|----------|-------------|
| `europe` | Major European markets (UK, DE, FR, CH, NL, ES, IT) |
| `asia` | Major Asian markets (JP, HK, CN, KR, TW, IN, SG, AU) |
| `emerging` | Emerging markets (BR, MX, ZA, IN, ID, TH, MY) |

<details>
<summary>Western Europe (10 markets)</summary>

| Universe | Exchange | Currency |
|----------|----------|----------|
| `uk` | London Stock Exchange - FTSE | GBP |
| `germany` | Frankfurt/XETRA - DAX | EUR |
| `france` | Euronext Paris - CAC 40 | EUR |
| `switzerland` | SIX Swiss Exchange - SMI | CHF |
| `netherlands` | Euronext Amsterdam - AEX | EUR |
| `spain` | Bolsa de Madrid - IBEX 35 | EUR |
| `italy` | Borsa Italiana - FTSE MIB | EUR |
| `belgium` | Euronext Brussels - BEL 20 | EUR |
| `austria` | Vienna Stock Exchange - ATX | EUR |
| `portugal` | Euronext Lisbon - PSI 20 | EUR |

</details>

<details>
<summary>Nordics (4 markets)</summary>

| Universe | Exchange | Currency |
|----------|----------|----------|
| `sweden` | Nasdaq Stockholm - OMX 30 | SEK |
| `norway` | Oslo Bors - OBX | NOK |
| `denmark` | Nasdaq Copenhagen - OMXC25 | DKK |
| `finland` | Nasdaq Helsinki - OMXH25 | EUR |

</details>

<details>
<summary>Asia-Pacific (12 markets)</summary>

| Universe | Exchange | Currency |
|----------|----------|----------|
| `japan` | Tokyo Stock Exchange - Nikkei/TOPIX | JPY |
| `hongkong` | Hong Kong Exchange - Hang Seng | HKD |
| `australia` | ASX - ASX 200 | AUD |
| `singapore` | Singapore Exchange - STI | SGD |
| `newzealand` | NZX - NZX 50 | NZD |
| `china` | Shanghai & Shenzhen - CSI 300 | CNY |
| `korea` | Korea Exchange - KOSPI | KRW |
| `taiwan` | Taiwan Stock Exchange - TWSE | TWD |
| `india` | National Stock Exchange - NIFTY 50 | INR |
| `indonesia` | Indonesia Stock Exchange - LQ45 | IDR |
| `malaysia` | Bursa Malaysia - KLCI | MYR |
| `thailand` | Stock Exchange of Thailand - SET50 | THB |

</details>

<details>
<summary>Americas & Other (6 markets)</summary>

| Universe | Exchange | Currency |
|----------|----------|----------|
| `canada` | Toronto Stock Exchange - TSX 60 | CAD |
| `brazil` | B3 Sao Paulo - Ibovespa | BRL |
| `mexico` | Bolsa Mexicana - IPC | MXN |
| `southafrica` | Johannesburg Stock Exchange - JSE Top 40 | ZAR |
| `israel` | Tel Aviv Stock Exchange - TA-35 | ILS |
| `turkey` | Borsa Istanbul - BIST 30 | TRY |

</details>

## Commands

### Core Commands

```bash
tradfi                           # Launch TUI (default)
tradfi analyze AAPL              # Analyze single stock
tradfi screen                    # Screen with default criteria
tradfi screen --preset graham    # Use Graham preset
tradfi screen --rsi-max 30       # Filter by oversold RSI
```

### Quarterly Analysis

```bash
tradfi quarterly AAPL                # Show 8 quarters of financial trends
tradfi quarterly AAPL --periods 12   # Show more quarters
tradfi quarterly AAPL MSFT --compare # Compare two stocks
```

### List Management

```bash
tradfi list ls                       # Show all saved lists
tradfi list create my-picks AAPL,MSFT,GOOGL  # Create a list
tradfi list show my-picks            # View list contents
tradfi list add my-picks NVDA        # Add ticker to list
tradfi list remove my-picks MSFT     # Remove ticker from list

# Quick long/short lists
tradfi list long AAPL                # Add to long list
tradfi list short TSLA               # Add to short list

# Categories
tradfi list category create "Value Picks" --icon "💎"
tradfi list move my-picks "Value Picks"

# Notes with thesis and price targets
tradfi list note my-picks AAPL "Strong moat, waiting for pullback"
tradfi list note my-picks AAPL --thesis "Services growth" --target 200 --entry 165

# Portfolio P&L tracking
tradfi list note my-picks AAPL --shares 100 --entry 150 --target 200
tradfi list note my-picks MSFT --shares 50 --entry 380 --target 450
```

### List Comparison

```bash
tradfi compare my-longs my-shorts        # Compare two lists
tradfi compare my-picks --metrics pe,roe,mos  # Single list with custom metrics
```

### Cache Management

```bash
tradfi cache status              # Show cache stats
tradfi cache prefetch sp500      # Prefetch S&P 500 to cache
tradfi cache prefetch all        # Prefetch all universes
tradfi cache clear               # Clear cached data
```

### API Server

```bash
tradfi api                       # Start API on port 8000
tradfi serve --port 3000         # Start on custom port
```

The API serves 30+ endpoints across 7 modules. Interactive docs at `/docs` (Swagger) and `/redoc`.

| Module | Prefix | Endpoints | Description |
|--------|--------|-----------|-------------|
| Stocks | `/api/v1/stocks` | 5 | Single and batch stock analysis, quarterly data |
| Screening | `/api/v1/screening` | 4 | Universe listing, presets, run screens |
| Lists | `/api/v1/lists` | 11 | List CRUD, items, notes, categories |
| Watchlist | `/api/v1/watchlist` | 4 | Watchlist CRUD with notes |
| Cache | `/api/v1/cache` | 3 | Stats, clear, sector listing |
| Refresh | `/api/v1/refresh` | 4 | Status, trigger refresh, health check |
| Currency | `/api/v1/currency` | 6 | Exchange rates, config, symbols |

<details>
<summary>Environment Variables</summary>

| Variable | Description | Default |
|----------|-------------|---------|
| `TRADFI_ADMIN_KEY` | Admin API key for destructive operations | _(open access)_ |
| `TRADFI_REFRESH_HOUR` | Hour (UTC) for daily auto-refresh | `5` |
| `TRADFI_REFRESH_UNIVERSES` | Comma-separated universes to refresh | `dow30,nasdaq100,sp500` |
| `TRADFI_REFRESH_ENABLED` | Set to `false` to disable auto-refresh | `true` |
| `TRADFI_CORS_ORIGINS` | CORS origins (`*` for dev, comma-separated for prod) | _(disabled)_ |

</details>

## Screening Presets

| Category | Preset | Description | Key Criteria |
|----------|--------|-------------|--------------|
| Value | `graham` | Benjamin Graham's value criteria | P/E<15, P/B<1.5, CR>2 |
| Value | `buffett` | Quality companies at fair prices | ROE>15%, Margin>10%, P/E<25 |
| Income | `dividend` | High-yield income stocks | Yield>3%, ROE>10% |
| Discovery | `fallen-angels` | Quality stocks down 30%+ | ROE>15%, Margin>10%, down 30%+ |
| Discovery | `hidden-gems` | Quality small/mid caps beaten down | $2-10B, P/E<18, ROE>12%, RSI<40 |
| Contrarian | `oversold` | Technical oversold signals | RSI<30, near 52W low, below 200MA |
| Contrarian | `turnaround` | Beaten down, recovery potential | P/E<12, down 25%+, RSI<40 |

## TUI Keybindings

### Main View

| Key | Action |
|-----|--------|
| `Space` | Open action menu (all commands) |
| `/` | Search for ticker |
| `r` | Refresh / Run screen |
| `Enter` | Select / View details |
| `Escape` | Go back |
| `q` | Quit |
| `?` | Show help |
| `u` | Filter by universe |
| `f` | Filter by sector |
| `c` | Clear all filters |
| `s` | Save current results as list |
| `$` | Toggle display currency |
| `h` | Sector heatmap |
| `p` | Scatter plot |
| `K` | Cache manager |

### Discovery Presets (via action menu)

| Key | Preset |
|-----|--------|
| `F` | Fallen Angels (quality down 30%+) |
| `H` | Hidden Gems (small/mid quality) |
| `T` | Turnaround Candidates |
| `O` | Oversold (RSI<30, near lows) |
| `D` | Dividend (yield>3%) |

### Sort Keys

| Key | Sort By |
|-----|---------|
| `1` | Ticker |
| `2` | Price |
| `3` | 1-month return |
| `4` | 6-month return |
| `5` | 1-year return |
| `6` | P/E ratio |
| `7` | P/B ratio |
| `8` | ROE |
| `9` | Dividend yield |
| `0` | RSI |
| `-` | Margin of Safety |
| `i` | Sector |

### Stock Detail View

| Key | Action |
|-----|--------|
| `w` | Add to watchlist |
| `l` | Add to long list |
| `x` | Add to short list |
| `d` | Deep research (SEC filings) |
| `q` | Quarterly trends |
| `m` | More like this (find similar stocks) |

## Deep Research (Optional)

Analyze SEC filings (10-K, 10-Q) using an LLM. Set one of these environment variables:

```bash
# OpenRouter (recommended - has free models)
export OPENROUTER_API_KEY=sk-or-v1-...

# Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check .
ruff format .
```

## Tech Stack

- **Typer** - CLI framework
- **yfinance** - Market data (stocks + forex)
- **pandas** - Data processing
- **Rich** - Terminal formatting
- **Textual** - TUI framework
- **FastAPI** - REST API with scheduled refresh
- **SQLite** - Caching and persistence
- **httpx** - HTTP client for remote API calls
- **APScheduler** - Background refresh tasks

## License

MIT
