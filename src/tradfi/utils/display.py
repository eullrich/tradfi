"""Rich display utilities for terminal output."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tradfi.core.currency import (
    convert_currency,
    get_currency_symbol,
)
from tradfi.core.technical import interpret_rsi
from tradfi.models.stock import Stock
from tradfi.utils.cache import get_display_currency

console = Console()


def format_number(
    value: float | None, decimals: int = 2, prefix: str = "", suffix: str = ""
) -> str:
    """Format a number with optional prefix/suffix."""
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def format_pct(value: float | None, decimals: int = 1) -> str:
    """Format a percentage value."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_large_number(
    value: float | None,
    currency: str = "USD",
    display_currency: str | None = None,
) -> str:
    """Format large numbers with B/M/K suffixes and currency symbol.

    Args:
        value: The value to format
        currency: Original currency of the value (default USD)
        display_currency: Target display currency (None = use config default)

    Returns:
        Formatted string like "$1.23B" or "£45.67M"
    """
    if value is None:
        return "N/A"

    # Get display currency from config if not specified
    if display_currency is None:
        display_currency = get_display_currency()

    # Convert if needed (skip for now if currencies match or no conversion available)
    if currency != display_currency:
        converted = convert_currency(value, currency, display_currency)
        if converted is not None:
            value = converted
            currency = display_currency

    symbol = get_currency_symbol(currency)

    # Special handling for gold (XAU)
    if currency == "XAU":
        if abs(value) >= 1000:
            return f"XAU {value:,.0f}"
        return f"XAU {value:.2f}"

    if abs(value) >= 1e12:
        return f"{symbol}{value / 1e12:.2f}T"
    if abs(value) >= 1e9:
        return f"{symbol}{value / 1e9:.2f}B"
    if abs(value) >= 1e6:
        return f"{symbol}{value / 1e6:.2f}M"
    if abs(value) >= 1e3:
        return f"{symbol}{value / 1e3:.2f}K"
    return f"{symbol}{value:.2f}"


def format_price(
    value: float | None,
    currency: str = "USD",
    display_currency: str | None = None,
    decimals: int = 2,
) -> str:
    """Format a price value with currency symbol.

    Args:
        value: The price to format
        currency: Original currency of the value (default USD)
        display_currency: Target display currency (None = use config default)
        decimals: Number of decimal places

    Returns:
        Formatted string like "$123.45" or "£89.12"
    """
    if value is None:
        return "N/A"

    # Get display currency from config if not specified
    if display_currency is None:
        display_currency = get_display_currency()

    # Convert if needed
    if currency != display_currency:
        converted = convert_currency(value, currency, display_currency)
        if converted is not None:
            value = converted
            currency = display_currency

    symbol = get_currency_symbol(currency)

    # Special handling for gold (XAU)
    if currency == "XAU":
        return f"XAU {value:.{decimals}f}"

    return f"{symbol}{value:,.{decimals}f}"


def colorize_rsi(rsi_str: str, rsi_val: float | None) -> str:
    """Apply Rich markup color to a pre-formatted RSI string based on thresholds."""
    if rsi_val is None:
        return rsi_str
    if rsi_val < 30:
        return f"[green]{rsi_str}[/]"
    if rsi_val < 40:
        return f"[yellow]{rsi_str}[/]"
    return rsi_str


def get_signal_display(signal: str) -> Text:
    """Get colored signal display."""
    signal_map = {
        "STRONG_BUY": ("STRONG BUY", "bold green"),
        "BUY": ("BUY", "green"),
        "WATCH": ("WATCH", "yellow"),
        "NEUTRAL": ("NEUTRAL", "white"),
        "NO_SIGNAL": ("--", "dim"),
    }
    text, style = signal_map.get(signal, ("--", "dim"))
    return Text(text, style=style)


def get_rsi_display(rsi: float | None) -> Text:
    """Get colored RSI display with interpretation."""
    if rsi is None:
        return Text("N/A", style="dim")

    interpretation = interpret_rsi(rsi)

    if rsi < 20:
        style = "bold red"
    elif rsi < 30:
        style = "red"
    elif rsi < 40:
        style = "yellow"
    elif rsi < 60:
        style = "white"
    elif rsi < 70:
        style = "yellow"
    else:
        style = "red"

    return Text(f"{rsi:.1f} ({interpretation})", style=style)


def get_margin_of_safety_display(mos: float | None) -> Text:
    """Get colored margin of safety display."""
    if mos is None:
        return Text("N/A", style="dim")

    if mos >= 30:
        style = "bold green"
        label = "UNDERVALUED"
    elif mos >= 10:
        style = "green"
        label = "UNDERVALUED"
    elif mos >= 0:
        style = "yellow"
        label = "FAIR VALUE"
    elif mos >= -10:
        style = "yellow"
        label = "SLIGHTLY OVERVALUED"
    else:
        style = "red"
        label = "OVERVALUED"

    return Text(f"{mos:+.1f}% ({label})", style=style)


def display_stock_analysis(stock: Stock) -> None:
    """Display full stock analysis with Rich formatting."""
    # Header
    header_text = f"{stock.name or stock.ticker} ({stock.ticker})"
    subtitle = f"{stock.sector or 'Unknown Sector'} | {stock.industry or 'Unknown Industry'}"

    console.print()
    console.print(
        Panel(
            f"[bold white]{header_text}[/]\n[dim]{subtitle}[/]",
            box=box.DOUBLE,
            padding=(0, 2),
        )
    )

    # Price info line
    stock_currency = stock.currency or "USD"
    price_line = Text()
    price_line.append("Price: ", style="dim")
    price_line.append(
        format_price(stock.current_price, currency=stock_currency)
        if stock.current_price
        else "N/A",
        style="bold",
    )
    price_line.append("    Market Cap: ", style="dim")
    price_line.append(format_large_number(stock.valuation.market_cap, currency=stock_currency))
    price_line.append("    52W Range: ", style="dim")
    if stock.technical.low_52w and stock.technical.high_52w:
        low = format_price(stock.technical.low_52w, currency=stock_currency)
        high = format_price(stock.technical.high_52w, currency=stock_currency)
        price_line.append(f"{low} - {high}")
    else:
        price_line.append("N/A")

    console.print(price_line)
    console.print()

    # Valuation Table
    val_table = Table(title="VALUATION", box=box.ROUNDED, show_header=False, padding=(0, 2))
    val_table.add_column("Metric", style="dim")
    val_table.add_column("Value")
    val_table.add_column("Metric", style="dim")
    val_table.add_column("Value")

    val_table.add_row(
        "P/E (TTM)",
        format_number(stock.valuation.pe_trailing),
        "P/E (Fwd)",
        format_number(stock.valuation.pe_forward),
    )
    val_table.add_row(
        "P/B",
        format_number(stock.valuation.pb_ratio),
        "P/S",
        format_number(stock.valuation.ps_ratio),
    )
    val_table.add_row(
        "EV/EBITDA",
        format_number(stock.valuation.ev_ebitda),
        "PEG",
        format_number(stock.valuation.peg_ratio),
    )
    val_table.add_row("", "", "", "")
    val_table.add_row(
        "Graham Number",
        format_price(stock.fair_value.graham_number, currency=stock_currency),
        "DCF Fair Value",
        format_price(stock.fair_value.dcf_value, currency=stock_currency),
    )
    val_table.add_row(
        "P/E Fair Value",
        format_price(stock.fair_value.pe_fair_value, currency=stock_currency),
        "Current Price",
        format_price(stock.current_price, currency=stock_currency),
    )
    val_table.add_row(
        "Margin of Safety",
        get_margin_of_safety_display(stock.fair_value.margin_of_safety_pct),
        "",
        "",
    )

    console.print(val_table)
    console.print()

    # Profitability Table
    prof_table = Table(title="PROFITABILITY", box=box.ROUNDED, show_header=False, padding=(0, 2))
    prof_table.add_column("Metric", style="dim")
    prof_table.add_column("Value")
    prof_table.add_column("Metric", style="dim")
    prof_table.add_column("Value")

    prof_table.add_row(
        "Gross Margin",
        format_pct(stock.profitability.gross_margin),
        "ROE",
        format_pct(stock.profitability.roe),
    )
    prof_table.add_row(
        "Operating Margin",
        format_pct(stock.profitability.operating_margin),
        "ROA",
        format_pct(stock.profitability.roa),
    )
    prof_table.add_row(
        "Net Margin",
        format_pct(stock.profitability.net_margin),
        "",
        "",
    )

    console.print(prof_table)
    console.print()

    # Financial Health Table
    health_table = Table(
        title="FINANCIAL HEALTH", box=box.ROUNDED, show_header=False, padding=(0, 2)
    )
    health_table.add_column("Metric", style="dim")
    health_table.add_column("Value")
    health_table.add_column("Metric", style="dim")
    health_table.add_column("Value")

    # Convert debt_to_equity from percentage back to ratio for display
    d_e = stock.financial_health.debt_to_equity
    d_e_display = format_number(d_e / 100, 2) if d_e is not None else "N/A"

    health_table.add_row(
        "Current Ratio",
        format_number(stock.financial_health.current_ratio),
        "Debt/Equity",
        d_e_display,
    )
    health_table.add_row(
        "Quick Ratio",
        format_number(stock.financial_health.quick_ratio),
        "Free Cash Flow",
        format_large_number(stock.financial_health.free_cash_flow, currency=stock_currency),
    )

    console.print(health_table)
    console.print()

    # Technical / Oversold Indicators Table
    tech_table = Table(
        title="TECHNICAL / OVERSOLD INDICATORS", box=box.ROUNDED, show_header=False, padding=(0, 2)
    )
    tech_table.add_column("Metric", style="dim")
    tech_table.add_column("Value")
    tech_table.add_column("Metric", style="dim")
    tech_table.add_column("Value")

    tech_table.add_row(
        "RSI (14-day)",
        get_rsi_display(stock.technical.rsi_14),
        "vs 52W High",
        format_pct(stock.technical.pct_from_52w_high),
    )
    tech_table.add_row(
        "vs 50-day MA",
        format_pct(stock.technical.price_vs_ma_50_pct),
        "vs 52W Low",
        format_pct(stock.technical.pct_from_52w_low),
    )
    tech_table.add_row(
        "vs 200-day MA",
        format_pct(stock.technical.price_vs_ma_200_pct),
        "",
        "",
    )

    console.print(tech_table)
    console.print()

    # Growth Table
    growth_table = Table(title="GROWTH", box=box.ROUNDED, show_header=False, padding=(0, 2))
    growth_table.add_column("Metric", style="dim")
    growth_table.add_column("Value")
    growth_table.add_column("Metric", style="dim")
    growth_table.add_column("Value")

    growth_table.add_row(
        "Revenue Growth (YoY)",
        format_pct(stock.growth.revenue_growth_yoy),
        "Earnings Growth (YoY)",
        format_pct(stock.growth.earnings_growth_yoy),
    )

    console.print(growth_table)
    console.print()

    # Dividend Table (if applicable)
    if stock.dividends.dividend_yield and stock.dividends.dividend_yield > 0:
        div_table = Table(title="DIVIDENDS", box=box.ROUNDED, show_header=False, padding=(0, 2))
        div_table.add_column("Metric", style="dim")
        div_table.add_column("Value")
        div_table.add_column("Metric", style="dim")
        div_table.add_column("Value")

        div_table.add_row(
            "Dividend Yield",
            format_pct(stock.dividends.dividend_yield),
            "Payout Ratio",
            format_pct(stock.dividends.payout_ratio),
        )
        div_table.add_row(
            "Annual Dividend",
            format_price(stock.dividends.dividend_rate, currency=stock_currency),
            "",
            "",
        )

        console.print(div_table)
        console.print()

    # Signal Summary
    signal = stock.signal
    signal_display = get_signal_display(signal)

    summary_parts = []

    # Valuation summary
    mos = stock.fair_value.margin_of_safety_pct
    if mos is not None and mos > 0:
        summary_parts.append(f"[green]+ Undervalued: {mos:.1f}% margin of safety[/]")
    elif mos is not None and mos < -10:
        summary_parts.append(f"[red]- Overvalued: {abs(mos):.1f}% above fair value[/]")

    # Oversold summary
    rsi = stock.technical.rsi_14
    if rsi is not None:
        if rsi < 20:
            summary_parts.append(f"[green]+ Strongly oversold: RSI at {rsi:.1f}[/]")
        elif rsi < 30:
            summary_parts.append(f"[green]+ Oversold: RSI at {rsi:.1f}[/]")
        elif rsi < 40:
            summary_parts.append(f"[yellow]~ Approaching oversold: RSI at {rsi:.1f}[/]")

    # 52W low proximity
    pct_from_low = stock.technical.pct_from_52w_low
    if pct_from_low is not None and pct_from_low < 15:
        summary_parts.append(f"[green]+ Near 52-week low: {pct_from_low:.1f}% above[/]")

    # ROE check
    roe = stock.profitability.roe
    if roe is not None and roe > 15:
        summary_parts.append(f"[green]+ Strong ROE: {roe:.1f}%[/]")

    # Debt check
    d_e = stock.financial_health.debt_to_equity
    if d_e is not None:
        d_e_ratio = d_e / 100  # Convert from percentage
        if d_e_ratio < 0.5:
            summary_parts.append(f"[green]+ Low debt: {d_e_ratio:.2f} D/E[/]")
        elif d_e_ratio > 1.5:
            summary_parts.append(f"[red]- High debt: {d_e_ratio:.2f} D/E[/]")

    if summary_parts or signal in ("STRONG_BUY", "BUY", "WATCH"):
        summary_content = (
            "\n".join(summary_parts) if summary_parts else "[dim]No notable signals[/]"
        )

        signal_panel = Panel(
            f"[bold]Signal: [/]{signal_display}\n\n{summary_content}",
            title="ANALYSIS SUMMARY",
            box=box.DOUBLE,
            padding=(1, 2),
        )
        console.print(signal_panel)

    # Disclaimer
    console.print()
    console.print(
        "[dim italic]Disclaimer: This is for informational purposes only, not financial advice.[/]"
    )
    console.print()
