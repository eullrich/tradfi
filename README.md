# TradFi

A Python CLI tool for value investors to screen stocks and analyze companies using fundamental metrics combined with technical oversold indicators.

## Features

- **Stock Screening** - Filter stocks by value metrics (P/E, P/B, ROE) and technical indicators (RSI, 52W highs/lows)
- **Single Stock Analysis** - Deep dive into individual companies with valuation and profitability metrics
- **Quarterly Trends** - View 8+ quarters of financial data with trend analysis
- **List Management** - Create and organize watchlists with categories and notes
- **Interactive TUI** - Terminal user interface for browsing and filtering stocks
- **REST API** - FastAPI server for remote cache access
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

# Screen with a preset (graham, buffett, deep-value, oversold-value)
tradfi screen --preset graham

# View quarterly financial trends
tradfi quarterly AAPL
```

## Available Universes

| Universe | Description |
|----------|-------------|
| `sp500` | S&P 500 (~500 large-cap US stocks) |
| `dow30` | Dow Jones Industrial Average (30 stocks) |
| `nasdaq100` | NASDAQ-100 (100 largest NASDAQ stocks) |
| `russell2000` | Russell 2000 sample (~200 small-cap stocks) |
| `sweetspot` | $2-12B market cap (under-followed + fallen angels) |
| `etf` | ETFs with categories: REITs, Commodities, Sectors, International |
| `dividends` | Dividend Aristocrats & high-yield stocks |
| `value` | Value-focused stocks and ETFs |

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
tradfi serve                     # Start API server on port 8000
tradfi serve --port 3000         # Start on custom port
```

## Screening Presets

| Preset | Description |
|--------|-------------|
| `graham` | Benjamin Graham criteria (P/E < 15, P/B < 1.5, etc.) |
| `buffett` | Quality + value (ROE > 15%, D/E < 0.5) |
| `deep-value` | Low P/B < 1.0, P/E < 10 |
| `oversold-value` | Value metrics + RSI < 35 |

## TUI Keybindings

| Key | Action |
|-----|--------|
| `Space` | Open action menu |
| `/` | Search for ticker |
| `r` | Refresh / Run screen |
| `Enter` | Select item |
| `Escape` | Go back |
| `q` | Quit |

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
- **yfinance** - Market data
- **pandas** - Data processing
- **Rich** - Terminal formatting
- **Textual** - TUI framework
- **FastAPI** - REST API
- **SQLite** - Caching

## License

MIT
