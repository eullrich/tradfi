# Value Investing CLI Tool - Implementation Plan

## Overview
A Python CLI tool for value investors to screen stocks and analyze companies using fundamental metrics combined with technical oversold indicators.

## Tech Stack
- **Language**: Python 3.11+
- **Data Source**: yfinance (free, no API key required)
- **CLI Framework**: Typer (modern, type-hinted CLI)
- **Data Processing**: pandas
- **Output Formatting**: Rich (beautiful terminal output with tables/colors)
- **Storage**: SQLite (for caching and watchlists)

## Data Source: yfinance

yfinance provides free access to:
- Real-time and historical price data
- Financial statements (income, balance sheet, cash flow)
- Key ratios (P/E, P/B, ROE, etc.)
- Company info and profile
- Technical data for calculating RSI, moving averages, etc.
- No API key or rate limits (reasonable use)

### Key yfinance Methods
```python
ticker = yf.Ticker("AAPL")
ticker.info          # Company info + key ratios
ticker.financials    # Income statement
ticker.balance_sheet # Balance sheet
ticker.cashflow      # Cash flow statement
ticker.history()     # Price history (for RSI, MAs)
```

---

## Project Structure

```
tradfi/
├── pyproject.toml           # Project config & dependencies
├── README.md
├── src/
│   └── tradfi/
│       ├── __init__.py
│       ├── cli.py           # Main CLI entry point (Typer app)
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── screen.py    # Stock screener command
│       │   ├── analyze.py   # Company analysis command
│       │   └── watchlist.py # Watchlist management
│       ├── core/
│       │   ├── __init__.py
│       │   ├── data.py      # yfinance data fetching
│       │   ├── metrics.py   # Value metric calculations
│       │   ├── technical.py # RSI, moving averages, oversold indicators
│       │   ├── screener.py  # Screening logic
│       │   └── valuation.py # Fair value calculations
│       ├── models/
│       │   ├── __init__.py
│       │   └── stock.py     # Stock data models
│       └── utils/
│           ├── __init__.py
│           ├── cache.py     # SQLite caching
│           └── display.py   # Rich formatting helpers
├── data/
│   └── sp500.csv            # S&P 500 tickers list
└── tests/
    └── ...
```

---

## Core Features

### 1. Stock Screener (`tradfi screen`)

Screen stocks based on value investing criteria + oversold indicators.

**Commands:**
```bash
# Screen with default value criteria
tradfi screen

# Screen with custom filters
tradfi screen --pe-max 15 --pb-max 1.5 --roe-min 15 --debt-equity-max 0.5

# Screen specific universe
tradfi screen --universe sp500
tradfi screen --universe dow30
tradfi screen --tickers AAPL,MSFT,GOOGL

# Pre-built screens
tradfi screen --preset graham      # Benjamin Graham criteria
tradfi screen --preset buffett     # Buffett-style quality + value
tradfi screen --preset deep-value  # Low P/B, P/E
tradfi screen --preset oversold-value  # Value + technically oversold

# Combine value + oversold
tradfi screen --preset graham --rsi-max 30
tradfi screen --pe-max 15 --roe-min 12 --near-52w-low 15
tradfi screen --rsi-max 35 --below-200ma --roe-min 15
```

**Value Screening Metrics:**
| Metric | Flag | Description |
|--------|------|-------------|
| P/E Ratio | `--pe-max`, `--pe-min` | Price to earnings |
| P/B Ratio | `--pb-max`, `--pb-min` | Price to book |
| P/S Ratio | `--ps-max`, `--ps-min` | Price to sales |
| ROE | `--roe-min` | Return on equity % |
| ROA | `--roa-min` | Return on assets % |
| Debt/Equity | `--debt-equity-max` | Leverage ratio |
| Current Ratio | `--current-min` | Liquidity |
| Dividend Yield | `--div-min` | Dividend yield % |
| Market Cap | `--mcap-min`, `--mcap-max` | Size filter |
| EPS Growth | `--eps-growth-min` | Earnings growth |

**Oversold/Technical Screening Metrics:**
| Metric | Flag | Description |
|--------|------|-------------|
| RSI (14-day) | `--rsi-max`, `--rsi-min` | < 30 = oversold, < 20 = strongly oversold |
| 52-Week Low | `--near-52w-low <pct>` | Within X% of 52-week low |
| Below 200-day MA | `--below-200ma` | Price below 200-day moving average |
| Below 50-day MA | `--below-50ma` | Price below 50-day moving average |
| % Below 200 MA | `--pct-below-200ma <pct>` | At least X% below 200-day MA |

**Pre-built Screens:**

1. **Graham Screen** (Benjamin Graham's criteria):
   - P/E < 15
   - P/B < 1.5
   - P/E × P/B < 22.5
   - Current Ratio > 2.0
   - Debt/Equity < 0.5
   - Positive EPS for 5 years

2. **Buffett Screen** (Quality at reasonable price):
   - ROE > 15%
   - Debt/Equity < 0.5
   - Profit margin > 10%
   - P/E < 25
   - Consistent earnings growth

3. **Deep Value Screen**:
   - P/B < 1.0
   - P/E < 10
   - Positive free cash flow

4. **Oversold Value Screen** (NEW - Value + Mean Reversion):
   - P/E < 15
   - ROE > 10%
   - RSI < 35
   - Within 20% of 52-week low
   - Debt/Equity < 1.0

**Output Example:**
```
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Ticker ┃ Name     ┃ P/E  ┃ P/B  ┃ ROE   ┃ RSI  ┃ vs 52W Low ┃ Signal    ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ XYZ    │ Example  │ 11.2 │ 1.1  │ 16.5% │ 28   │ +8%        │ 🟢 BUY    │
│ ABC    │ AcmeCorp │ 13.5 │ 1.3  │ 14.2% │ 32   │ +12%       │ 🟡 WATCH  │
│ ...    │ ...      │ ...  │ ...  │ ...   │ ...  │ ...        │ ...       │
└────────┴──────────┴──────┴──────┴───────┴──────┴────────────┴───────────┘

Found 15 stocks matching criteria. Use `tradfi analyze <ticker>` for details.
```

**Signal Logic:**
- 🟢 **BUY**: Value criteria met + RSI < 30 OR within 10% of 52W low
- 🟡 **WATCH**: Value criteria met + RSI 30-40 OR within 20% of 52W low
- ⚪ **NEUTRAL**: Value criteria met, not oversold

---

### 2. Company Analysis (`tradfi analyze`)

Deep dive into a single stock with valuation + technical analysis.

**Commands:**
```bash
# Full analysis
tradfi analyze AAPL

# Specific sections
tradfi analyze AAPL --section valuation
tradfi analyze AAPL --section financials
tradfi analyze AAPL --section technical

# Compare multiple stocks
tradfi analyze AAPL MSFT GOOGL --compare

# Export to file
tradfi analyze AAPL --export json
tradfi analyze AAPL --export csv
```

**Analysis Sections:**

1. **Company Overview**
   - Name, sector, industry
   - Market cap, enterprise value
   - 52-week range, current price
   - Description summary

2. **Valuation Metrics**
   - P/E (trailing & forward)
   - P/B, P/S, EV/EBITDA
   - PEG ratio
   - **Fair Value Estimate** (Graham formula, DCF simple)
   - Margin of safety %

3. **Profitability**
   - Gross margin, operating margin, net margin
   - ROE, ROA, ROIC
   - 5-year trends

4. **Financial Health**
   - Current ratio, quick ratio
   - Debt/Equity, Debt/Assets
   - Interest coverage
   - Free cash flow

5. **Growth Metrics**
   - Revenue growth (YoY, 5Y CAGR)
   - EPS growth (YoY, 5Y CAGR)
   - Dividend growth

6. **Technical / Oversold Indicators** (NEW)
   - RSI (14-day) with interpretation
   - Price vs 50-day MA (% above/below)
   - Price vs 200-day MA (% above/below)
   - Distance from 52-week high/low
   - Stochastic oscillator (optional)

7. **Dividend Analysis** (if applicable)
   - Current yield
   - Payout ratio
   - Dividend history
   - Years of consecutive increases

**Fair Value Calculations:**

1. **Graham Number**:
   ```
   √(22.5 × EPS × Book Value per Share)
   ```

2. **Simple DCF** (10-year projection):
   ```
   Sum of discounted future cash flows + terminal value
   ```

3. **Earnings Power Value (EPV)**:
   ```
   Adjusted Earnings / Cost of Capital
   ```

**Output Example:**
```
╭──────────────────────────────────────────────────────────────╮
│                    EXAMPLE CORP (XYZ)                        │
│                Industrials | Manufacturing                   │
╰──────────────────────────────────────────────────────────────╯

Price: $45.20    Market Cap: $12.5B    52W Range: $38 - $72

┌─ VALUATION ──────────────────────────────────────────────────┐
│  P/E (TTM)     11.2       P/E (Fwd)     10.5                │
│  P/B            1.1       P/S           0.8                  │
│  EV/EBITDA      7.2       PEG           0.9                  │
│                                                              │
│  Graham Number:     $52.30                                   │
│  DCF Fair Value:    $58.00                                   │
│  Current Price:     $45.20                                   │
│  Margin of Safety:  +22% ✅ (UNDERVALUED)                    │
└──────────────────────────────────────────────────────────────┘

┌─ PROFITABILITY ──────────────────────────────────────────────┐
│  Gross Margin     32.5%    ROE            16.8%             │
│  Operating Margin 14.2%    ROA            10.2%             │
│  Net Margin        9.8%    ROIC           14.5%             │
└──────────────────────────────────────────────────────────────┘

┌─ FINANCIAL HEALTH ───────────────────────────────────────────┐
│  Current Ratio    2.1      Debt/Equity    0.35              │
│  Quick Ratio      1.4      Interest Cov   12.5x             │
│  Free Cash Flow   $1.8B                                     │
└──────────────────────────────────────────────────────────────┘

┌─ TECHNICAL / OVERSOLD INDICATORS ────────────────────────────┐
│  RSI (14-day)     28       ← OVERSOLD 🔴                    │
│  vs 50-day MA     -12.5%   ← Below                          │
│  vs 200-day MA    -18.2%   ← Below                          │
│  vs 52W High      -37.2%                                    │
│  vs 52W Low       +18.9%   ← Near low                       │
└──────────────────────────────────────────────────────────────┘

┌─ GROWTH (5Y CAGR) ───────────────────────────────────────────┐
│  Revenue          6.2%     EPS            8.5%              │
│  Dividends        4.5%     Book Value     7.2%              │
└──────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════╗
║  🟢 VALUE + OVERSOLD BUY SIGNAL                              ║
║                                                              ║
║  • Undervalued: 22% margin of safety                         ║
║  • Oversold: RSI at 28 (< 30 threshold)                      ║
║  • Near 52W low with solid fundamentals                      ║
║  • Strong ROE (16.8%) with low debt (0.35 D/E)              ║
╚══════════════════════════════════════════════════════════════╝
```

---

### 3. Watchlist Management (`tradfi watchlist`)

```bash
# Add stocks to watchlist
tradfi watchlist add AAPL MSFT GOOGL

# View watchlist with current metrics
tradfi watchlist show

# Remove from watchlist
tradfi watchlist remove AAPL

# Set price alerts
tradfi watchlist alert AAPL --below 150
tradfi watchlist alert AAPL --pe-below 20
tradfi watchlist alert AAPL --rsi-below 30
```

---

## Technical Indicator Calculations

### RSI (Relative Strength Index)
```python
def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss over period
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]
```

### Moving Averages
```python
def calculate_ma(prices: pd.Series, period: int) -> float:
    """Simple Moving Average"""
    return prices.rolling(window=period).mean().iloc[-1]

def price_vs_ma(current_price: float, ma: float) -> float:
    """Returns percentage above/below MA"""
    return ((current_price - ma) / ma) * 100
```

### 52-Week High/Low Analysis
```python
def analyze_52w_range(ticker_data) -> dict:
    """Analyze price position within 52-week range"""
    high_52w = ticker_data['fiftyTwoWeekHigh']
    low_52w = ticker_data['fiftyTwoWeekLow']
    current = ticker_data['currentPrice']

    return {
        'pct_from_high': ((current - high_52w) / high_52w) * 100,
        'pct_from_low': ((current - low_52w) / low_52w) * 100,
        'position_in_range': ((current - low_52w) / (high_52w - low_52w)) * 100
    }
```

---

## Implementation Phases

### Phase 1: Foundation (MVP)
- [ ] Project setup with pyproject.toml
- [ ] Basic yfinance data fetching wrapper
- [ ] Stock data model
- [ ] Single stock analysis command (`analyze`)
- [ ] Basic terminal output with Rich
- [ ] RSI and moving average calculations

### Phase 2: Screener
- [ ] S&P 500 ticker list
- [ ] Screening logic with value filters
- [ ] Screening logic with technical/oversold filters
- [ ] Pre-built screens (Graham, Buffett, Deep Value, Oversold Value)
- [ ] Screener CLI command
- [ ] Buy signal logic

### Phase 3: Enhanced Analysis
- [ ] Fair value calculations (Graham Number, simple DCF)
- [ ] Comparison mode for multiple stocks
- [ ] Export functionality (JSON, CSV)
- [ ] Combined value + oversold signal summary

### Phase 4: Persistence & Polish
- [ ] SQLite caching for API responses
- [ ] Watchlist with SQLite storage
- [ ] Price/metric/RSI alerts
- [ ] Configuration file support

---

## Dependencies

```toml
[project]
name = "tradfi"
version = "0.1.0"
description = "Value investing CLI tool with oversold indicators"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "yfinance>=0.2.40",
    "pandas>=2.0.0",
    "rich>=13.0.0",
]

[project.scripts]
tradfi = "tradfi.cli:app"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Example Usage Flow

```bash
# Install
pip install -e .

# Screen for oversold value stocks
$ tradfi screen --preset oversold-value

Found 8 stocks matching Oversold Value criteria:

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━┓
┃ Ticker ┃ Name             ┃ P/E  ┃ ROE  ┃ D/E   ┃ RSI  ┃ Signal  ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━┩
│ XYZ    │ Example Corp     │ 11.2 │ 16.8 │ 0.35  │ 28   │ 🟢 BUY  │
│ ABC    │ Acme Industries  │ 13.5 │ 14.2 │ 0.42  │ 32   │ 🟡 WATCH│
│ ...    │ ...              │ ...  │ ...  │ ...   │ ...  │ ...     │
└────────┴──────────────────┴──────┴──────┴───────┴──────┴─────────┘

# Analyze a specific stock
$ tradfi analyze XYZ

# Add to watchlist for monitoring
$ tradfi watchlist add XYZ

# Set alert for when it becomes more oversold
$ tradfi watchlist alert XYZ --rsi-below 25
```

---

## Oversold Signal Interpretation Guide

| RSI Level | Interpretation | Action |
|-----------|---------------|--------|
| < 20 | Strongly oversold | Strong buy signal (if fundamentals good) |
| 20-30 | Oversold | Buy signal |
| 30-40 | Approaching oversold | Watch closely |
| 40-60 | Neutral | No technical signal |
| 60-70 | Approaching overbought | Consider taking profits |
| > 70 | Overbought | Potential sell signal |

**Combining Value + Oversold:**
- Value stock + RSI < 30 = High conviction buy
- Value stock + RSI 30-40 + near 52W low = Good entry opportunity
- Value stock + above 200 MA + RSI > 50 = Fair value, wait for pullback

---

## Notes

- **Rate Limiting**: yfinance doesn't have strict rate limits, but add small delays between bulk requests to be respectful
- **Data Freshness**: Cache data for ~15 minutes to avoid redundant API calls
- **Error Handling**: Handle missing data gracefully (some stocks lack certain metrics)
- **RSI Caution**: Stocks can remain oversold for extended periods - always confirm with fundamentals
- **Disclaimer**: Add investment disclaimer - this is for educational/informational purposes only, not financial advice
