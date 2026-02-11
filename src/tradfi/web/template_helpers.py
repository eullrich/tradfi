"""Jinja2 template filters, globals, and metric thresholds for the web frontend.

Threshold tuples define color-coding rules for stock metrics. Each tuple
contains (operator, threshold_value, css_color) entries evaluated in order.
The first matching rule wins.

These thresholds are extracted from tui/app.py to keep a single source of
truth for what constitutes "good", "bad", or "neutral" values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import Environment

# ============================================================================
# Metric Thresholds
# ============================================================================
# Each threshold list is evaluated in order. First match wins.
# Format: (operator, threshold_value, css_color)
#   "gt" = value > threshold
#   "lt" = value < threshold

PE_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 25, "red"),
    ("gt", 20, "yellow"),
    ("lt", 12, "green"),
]

PE_FWD_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 22, "red"),
    ("gt", 18, "yellow"),
    ("lt", 12, "green"),
]

PB_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 3.0, "red"),
    ("gt", 1.5, "yellow"),
    ("lt", 1.0, "green"),
]

EV_EBITDA_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 15, "red"),
    ("gt", 12, "yellow"),
    ("lt", 8, "green"),
]

PS_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 5, "red"),
    ("gt", 3, "yellow"),
    ("lt", 1, "green"),
]

PEG_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 2, "red"),
    ("gt", 1.5, "yellow"),
    ("lt", 1, "green"),
]

ROE_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 5, "red"),
    ("lt", 8, "yellow"),
    ("gt", 15, "green"),
]

ROA_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 2, "red"),
    ("lt", 5, "yellow"),
    ("gt", 10, "green"),
]

MARGIN_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 5, "red"),
    ("lt", 10, "yellow"),
    ("gt", 20, "green"),
]

NET_MARGIN_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 3, "red"),
    ("lt", 8, "yellow"),
    ("gt", 15, "green"),
]

DE_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 1.5, "red"),
    ("gt", 1.0, "yellow"),
    ("lt", 0.3, "green"),
]

CR_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 1, "red"),
    ("lt", 1.5, "yellow"),
    ("gt", 2, "green"),
]

IC_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 1.5, "red"),
    ("lt", 2, "yellow"),
    ("gt", 5, "green"),
]

RSI_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 30, "green"),
    ("lt", 40, "yellow"),
    ("gt", 70, "red"),
]

MOS_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 0, "red"),
    ("lt", 20, "yellow"),
    ("gt", 20, "green"),
]

FCF_YIELD_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 2, "red"),
    ("lt", 4, "yellow"),
    ("gt", 8, "green"),
]

DIV_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 3, "green"),
    ("gt", 1.5, "yellow"),
]

PAYOUT_THRESHOLDS: list[tuple[str, float, str]] = [
    ("gt", 90, "red"),
    ("gt", 75, "yellow"),
    ("lt", 50, "green"),
]

REV_GROWTH_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", 0, "red"),
    ("gt", 10, "green"),
]

EARN_GROWTH_THRESHOLDS: list[tuple[str, float, str]] = [
    ("lt", -10, "red"),
    ("gt", 10, "green"),
]


# ============================================================================
# Metric Thresholds Lookup
# ============================================================================
# Maps Stock model field paths to their threshold tuples for use in templates.

METRIC_THRESHOLDS: dict[str, list[tuple[str, float, str]]] = {
    "pe_trailing": PE_THRESHOLDS,
    "pe_forward": PE_FWD_THRESHOLDS,
    "pb_ratio": PB_THRESHOLDS,
    "ps_ratio": PS_THRESHOLDS,
    "peg_ratio": PEG_THRESHOLDS,
    "ev_ebitda": EV_EBITDA_THRESHOLDS,
    "roe": ROE_THRESHOLDS,
    "roa": ROA_THRESHOLDS,
    "gross_margin": MARGIN_THRESHOLDS,
    "operating_margin": MARGIN_THRESHOLDS,
    "net_margin": NET_MARGIN_THRESHOLDS,
    "debt_to_equity": DE_THRESHOLDS,
    "current_ratio": CR_THRESHOLDS,
    "interest_coverage": IC_THRESHOLDS,
    "rsi_14": RSI_THRESHOLDS,
    "margin_of_safety_pct": MOS_THRESHOLDS,
    "fcf_yield_pct": FCF_YIELD_THRESHOLDS,
    "dividend_yield": DIV_THRESHOLDS,
    "payout_ratio": PAYOUT_THRESHOLDS,
    "revenue_growth_yoy": REV_GROWTH_THRESHOLDS,
    "earnings_growth_yoy": EARN_GROWTH_THRESHOLDS,
}


# ============================================================================
# Indicator Tooltips
# ============================================================================
# Human-readable descriptions for each metric, shown on hover in the web UI.

INDICATOR_TOOLTIPS: dict[str, dict[str, str]] = {
    "pe_trailing": {
        "label": "P/E Ratio (Trailing)",
        "desc": "Price / earnings per share over last 12 months",
        "good": "Below 15 (Graham considers cheap)",
        "bad": "Above 25 (may be overvalued)",
    },
    "pe_forward": {
        "label": "P/E Ratio (Forward)",
        "desc": "Price / estimated future earnings per share",
        "good": "Below 12 (cheap on forward estimates)",
        "bad": "Above 22 (priced for perfection)",
    },
    "pb_ratio": {
        "label": "Price / Book",
        "desc": "Market price relative to book value per share",
        "good": "Below 1.0 (trading below book value)",
        "bad": "Above 3.0 (significant premium to book)",
    },
    "ps_ratio": {
        "label": "Price / Sales",
        "desc": "Market cap divided by annual revenue",
        "good": "Below 1.0 (cheap relative to revenue)",
        "bad": "Above 5.0 (very expensive for revenue generated)",
    },
    "peg_ratio": {
        "label": "PEG Ratio",
        "desc": "P/E divided by earnings growth rate",
        "good": "Below 1.0 (undervalued relative to growth)",
        "bad": "Above 2.0 (overvalued relative to growth)",
    },
    "ev_ebitda": {
        "label": "EV / EBITDA",
        "desc": "Enterprise value relative to operating earnings",
        "good": "Below 8 (cheap on cash earnings basis)",
        "bad": "Above 15 (expensive enterprise valuation)",
    },
    "graham_number": {
        "label": "Graham Number",
        "desc": "Fair value: sqrt(22.5 x EPS x Book Value)",
        "good": "Price below = undervalued",
        "bad": "Price well above = overvalued",
    },
    "roe": {
        "label": "Return on Equity",
        "desc": "Net income as percentage of shareholder equity",
        "good": "Above 15% (strong capital efficiency)",
        "bad": "Below 5% (poor returns on equity)",
    },
    "roa": {
        "label": "Return on Assets",
        "desc": "Net income as percentage of total assets",
        "good": "Above 10% (strong asset efficiency)",
        "bad": "Below 2% (poor use of assets)",
    },
    "gross_margin": {
        "label": "Gross Margin",
        "desc": "Revenue minus cost of goods sold, as percentage",
        "good": "Above 20% (strong pricing power)",
        "bad": "Below 5% (thin margins, commodity business)",
    },
    "operating_margin": {
        "label": "Operating Margin",
        "desc": "Operating income as percentage of revenue",
        "good": "Above 20% (efficient operations)",
        "bad": "Below 5% (high cost structure)",
    },
    "net_margin": {
        "label": "Net Margin",
        "desc": "Net income as percentage of revenue",
        "good": "Above 15% (highly profitable)",
        "bad": "Below 3% (slim profits after all expenses)",
    },
    "debt_to_equity": {
        "label": "Debt / Equity",
        "desc": "Total debt relative to shareholder equity",
        "good": "Below 0.3 (conservatively financed)",
        "bad": "Above 1.5 (heavily leveraged)",
    },
    "current_ratio": {
        "label": "Current Ratio",
        "desc": "Current assets divided by current liabilities",
        "good": "Above 2.0 (strong short-term liquidity)",
        "bad": "Below 1.0 (may struggle to pay near-term obligations)",
    },
    "interest_coverage": {
        "label": "Interest Coverage",
        "desc": "EBIT divided by interest expense",
        "good": "Above 5x (comfortably covers interest)",
        "bad": "Below 1.5x (struggling to service debt)",
    },
    "free_cash_flow": {
        "label": "Free Cash Flow",
        "desc": "Operating cash flow minus capital expenditures",
        "good": "Positive and growing (self-funding business)",
        "bad": "Negative (burning cash, needs external financing)",
    },
    "rsi_14": {
        "label": "RSI (14-day)",
        "desc": "Relative Strength Index over 14 trading days",
        "good": "Below 30 (oversold, potential buying opportunity)",
        "bad": "Above 70 (overbought, potential pullback)",
    },
    "margin_of_safety_pct": {
        "label": "Margin of Safety",
        "desc": "How far below fair value the stock trades",
        "good": "Above 20% (significant discount to intrinsic value)",
        "bad": "Below 0% (trading above estimated fair value)",
    },
    "dividend_yield": {
        "label": "Dividend Yield",
        "desc": "Annual dividend per share as percentage of price",
        "good": "Above 3% (meaningful income stream)",
        "bad": "N/A (depends on investor goals)",
    },
    "payout_ratio": {
        "label": "Payout Ratio",
        "desc": "Percentage of earnings paid as dividends",
        "good": "Below 50% (sustainable, room to grow dividend)",
        "bad": "Above 90% (unsustainable, at risk of cut)",
    },
    "revenue_growth_yoy": {
        "label": "Revenue Growth (YoY)",
        "desc": "Year-over-year revenue change as percentage",
        "good": "Above 10% (healthy top-line growth)",
        "bad": "Below 0% (declining revenue)",
    },
    "earnings_growth_yoy": {
        "label": "Earnings Growth (YoY)",
        "desc": "Year-over-year earnings change as percentage",
        "good": "Above 10% (strong profit growth)",
        "bad": "Below -10% (significant earnings decline)",
    },
    "fcf_yield_pct": {
        "label": "FCF Yield",
        "desc": "Free cash flow as percentage of market cap",
        "good": "Above 8% (generating strong cash relative to price)",
        "bad": "Below 2% (poor cash generation for price paid)",
    },
    "price_vs_ma_50_pct": {
        "label": "Price vs 50-day MA",
        "desc": "Current price relative to 50-day moving average",
        "good": "Below -10% (significantly below short-term trend)",
        "bad": "Above 5% (extended above short-term trend)",
    },
    "price_vs_ma_200_pct": {
        "label": "Price vs 200-day MA",
        "desc": "Current price relative to 200-day moving average",
        "good": "Below -10% (significantly below long-term trend)",
        "bad": "Above 5% (extended above long-term trend)",
    },
    "pct_from_52w_high": {
        "label": "From 52-Week High",
        "desc": "Percentage decline from the highest price in past year",
        "good": "Below -30% (deep pullback, potential value)",
        "bad": "Near 0% (at highs, less upside potential)",
    },
    "pct_from_52w_low": {
        "label": "From 52-Week Low",
        "desc": "Percentage above the lowest price in past year",
        "good": "Below 10% (near lows, potential bottom)",
        "bad": "Above 100% (far from lows, may be stretched)",
    },
}


# ============================================================================
# Jinja2 Template Filters
# ============================================================================


def metric_class(value: float | None, thresholds: list[tuple[str, float, str]]) -> str:
    """Return CSS class for a metric value based on thresholds.

    Evaluates threshold rules in order and returns the CSS class for the
    first matching rule. Returns 'metric--dim' for None values.

    Args:
        value: The numeric metric value, or None.
        thresholds: List of (operator, threshold, color) tuples.

    Returns:
        CSS class string like 'metric--green' or 'metric--dim'.
    """
    if value is None:
        return "metric--dim"
    for op, threshold, color in thresholds:
        if op == "gt" and value > threshold:
            return f"metric--{color}"
        if op == "lt" and value < threshold:
            return f"metric--{color}"
    return ""


def fmt_ratio(value: float | None) -> str:
    """Format a ratio value to 1 decimal place."""
    return f"{value:.1f}" if value is not None else "-"


def fmt_pct(value: float | None) -> str:
    """Format a percentage value with no decimals."""
    return f"{value:.0f}%" if value is not None else "-"


def fmt_pct1(value: float | None) -> str:
    """Format a percentage value to 1 decimal place."""
    return f"{value:.1f}%" if value is not None else "-"


def fmt_signed_pct(value: float | None) -> str:
    """Format a percentage with sign prefix (e.g., +12% or -5%)."""
    return f"{value:+.0f}%" if value is not None else "-"


def fmt_price(value: float | None) -> str:
    """Format a price with dollar sign and 2 decimals."""
    return f"${value:,.2f}" if value is not None else "-"


def fmt_large(value: float | None) -> str:
    """Format large number with B/M/K suffix.

    Args:
        value: Number to format (e.g., 1_500_000_000).

    Returns:
        Formatted string like '$1.5B', '$150M', '$50K', or '-'.
    """
    if value is None:
        return "-"
    av = abs(value)
    sign = "" if value >= 0 else "-"
    if av >= 1_000_000_000:
        return f"{sign}${av / 1_000_000_000:.1f}B"
    if av >= 1_000_000:
        return f"{sign}${av / 1_000_000:.0f}M"
    if av >= 1_000:
        return f"{sign}${av / 1_000:.0f}K"
    return f"{sign}${av:.0f}"


def fmt_de(value: float | None) -> str:
    """Format debt-to-equity: convert from yfinance percentage to ratio display."""
    if value is None:
        return "-"
    return f"{value / 100:.2f}"


def de_class(value: float | None) -> str:
    """Return CSS class for D/E after converting from percentage to ratio."""
    if value is None:
        return "metric--dim"
    return metric_class(value / 100, DE_THRESHOLDS)


def urlencode_value(value: str | None) -> str:
    """URL-encode a value for safe use in query string parameters."""
    if not value:
        return ""
    from urllib.parse import quote
    return quote(str(value), safe="")


def signal_class(signal: str | None) -> str:
    """Return CSS class for a signal value.

    Args:
        signal: Signal string like 'STRONG_BUY', 'BUY', 'WATCH', 'NEUTRAL'.

    Returns:
        CSS class string.
    """
    return {
        "STRONG_BUY": "signal--strong-buy",
        "BUY": "signal--buy",
        "WATCH": "signal--watch",
        "NEUTRAL": "signal--neutral",
    }.get(signal or "", "signal--neutral")


def signal_label(signal: str | None) -> str:
    """Return display label for a signal.

    Args:
        signal: Signal string from the Stock model.

    Returns:
        Human-readable label.
    """
    return {
        "STRONG_BUY": "STRONG BUY",
        "BUY": "BUY",
        "WATCH": "WATCH",
        "NEUTRAL": "NEUTRAL",
        "NO_SIGNAL": "--",
    }.get(signal or "", "--")


# ============================================================================
# Registration
# ============================================================================


def register_filters(env: "Environment") -> None:
    """Register all template filters and globals on a Jinja2 environment.

    Call this after creating your Jinja2Templates instance:

        templates = Jinja2Templates(directory="templates")
        register_filters(templates.env)

    Args:
        env: The Jinja2 Environment to register on.
    """
    # Filters
    env.filters["metric_class"] = metric_class
    env.filters["fmt_ratio"] = fmt_ratio
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_pct1"] = fmt_pct1
    env.filters["fmt_signed_pct"] = fmt_signed_pct
    env.filters["fmt_price"] = fmt_price
    env.filters["fmt_large"] = fmt_large
    env.filters["fmt_de"] = fmt_de
    env.filters["de_class"] = de_class
    env.filters["signal_class"] = signal_class
    env.filters["signal_label"] = signal_label
    env.filters["urlencode_value"] = urlencode_value

    # Globals (accessible in all templates)
    env.globals["METRIC_THRESHOLDS"] = METRIC_THRESHOLDS
    env.globals["INDICATOR_TOOLTIPS"] = INDICATOR_TOOLTIPS
