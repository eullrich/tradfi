"""Analyze command - deep dive into a single stock or compare multiple."""

import csv
import json
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from tradfi.core.data import fetch_stock
from tradfi.models.stock import Stock
from tradfi.utils.display import (
    display_stock_analysis,
    format_large_number,
    format_number,
    format_pct,
    get_signal_display,
)

console = Console()


def analyze(
    tickers: list[str] = typer.Argument(
        ..., help="Stock ticker symbol(s) (e.g., AAPL or AAPL MSFT GOOGL)"
    ),
    compare: bool = typer.Option(
        False, "--compare", "-c", help="Compare multiple stocks side by side"
    ),
    export: Optional[str] = typer.Option(
        None, "--export", "-e", help="Export to file (json or csv)"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """
    Analyze a stock with valuation metrics and oversold indicators.

    Displays comprehensive analysis including:
    - Valuation (P/E, P/B, Graham Number, DCF, margin of safety)
    - Profitability (ROE, ROA, margins)
    - Financial health (debt, liquidity)
    - Technical indicators (RSI, moving averages, 52-week range)
    - Buy/Watch/Neutral signal based on value + oversold criteria

    Examples:
        tradfi analyze AAPL
        tradfi analyze AAPL MSFT GOOGL --compare
        tradfi analyze AAPL --export json
        tradfi analyze AAPL MSFT --export csv -o comparison.csv
    """
    # Clean up tickers
    tickers = [t.upper().strip() for t in tickers]

    # Fetch all stocks
    stocks: list[Stock] = []
    for ticker in tickers:
        with console.status(f"[bold green]Fetching data for {ticker}...[/]"):
            stock = fetch_stock(ticker)

        if stock is None:
            console.print(f"[yellow]Warning: Could not fetch data for '{ticker}'[/]")
        else:
            stocks.append(stock)

    if not stocks:
        console.print("[red]Error: Could not fetch data for any ticker[/]")
        raise typer.Exit(1)

    # Handle export
    if export:
        export_stocks(stocks, export, output)
        return

    # Single stock or comparison
    if len(stocks) == 1 and not compare:
        display_stock_analysis(stocks[0])
    else:
        display_comparison(stocks)


def display_comparison(stocks: list[Stock]) -> None:
    """Display side-by-side comparison of multiple stocks."""
    console.print()

    # Header
    console.print(f"[bold]Comparing {len(stocks)} stocks[/]")
    console.print()

    # Build comparison table
    table = Table(
        title="Stock Comparison",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    # Add metric column
    table.add_column("Metric", style="dim")

    # Add a column for each stock
    for stock in stocks:
        table.add_column(stock.ticker, justify="right")

    # Basic Info
    table.add_row(
        "Name",
        *[
            s.name[:20] + "..." if s.name and len(s.name) > 20 else (s.name or "N/A")
            for s in stocks
        ],
    )
    table.add_row("Sector", *[s.sector or "N/A" for s in stocks])
    table.add_row(
        "Price", *[f"${s.current_price:.2f}" if s.current_price else "N/A" for s in stocks]
    )
    table.add_row("Market Cap", *[format_large_number(s.valuation.market_cap) for s in stocks])

    # Separator
    table.add_row("", *["" for _ in stocks], style="dim")
    table.add_row("[bold]VALUATION[/]", *["" for _ in stocks])

    # Valuation metrics
    table.add_row("P/E (TTM)", *[format_number(s.valuation.pe_trailing, 1) for s in stocks])
    table.add_row("P/E (Forward)", *[format_number(s.valuation.pe_forward, 1) for s in stocks])
    table.add_row("P/B", *[format_number(s.valuation.pb_ratio, 2) for s in stocks])
    table.add_row("P/S", *[format_number(s.valuation.ps_ratio, 2) for s in stocks])
    table.add_row("EV/EBITDA", *[format_number(s.valuation.ev_ebitda, 1) for s in stocks])

    # Fair value
    table.add_row(
        "Graham Number", *[format_number(s.fair_value.graham_number, 2, "$") for s in stocks]
    )
    table.add_row("DCF Value", *[format_number(s.fair_value.dcf_value, 2, "$") for s in stocks])
    table.add_row(
        "Margin of Safety", *[format_pct(s.fair_value.margin_of_safety_pct) for s in stocks]
    )

    # Separator
    table.add_row("", *["" for _ in stocks], style="dim")
    table.add_row("[bold]PROFITABILITY[/]", *["" for _ in stocks])

    # Profitability
    table.add_row("ROE", *[format_pct(s.profitability.roe) for s in stocks])
    table.add_row("ROA", *[format_pct(s.profitability.roa) for s in stocks])
    table.add_row("Gross Margin", *[format_pct(s.profitability.gross_margin) for s in stocks])
    table.add_row("Net Margin", *[format_pct(s.profitability.net_margin) for s in stocks])

    # Separator
    table.add_row("", *["" for _ in stocks], style="dim")
    table.add_row("[bold]FINANCIAL HEALTH[/]", *["" for _ in stocks])

    # Financial health
    table.add_row(
        "Current Ratio", *[format_number(s.financial_health.current_ratio, 2) for s in stocks]
    )
    de_values = []
    for s in stocks:
        de = s.financial_health.debt_to_equity
        de_values.append(format_number(de / 100, 2) if de is not None else "N/A")
    table.add_row("Debt/Equity", *de_values)
    table.add_row(
        "Free Cash Flow", *[format_large_number(s.financial_health.free_cash_flow) for s in stocks]
    )

    # Separator
    table.add_row("", *["" for _ in stocks], style="dim")
    table.add_row("[bold]TECHNICAL[/]", *["" for _ in stocks])

    # Technical
    table.add_row("RSI (14)", *[format_number(s.technical.rsi_14, 0) for s in stocks])
    table.add_row("vs 200-day MA", *[format_pct(s.technical.price_vs_ma_200_pct) for s in stocks])
    table.add_row("vs 52W Low", *[format_pct(s.technical.pct_from_52w_low) for s in stocks])
    table.add_row("vs 52W High", *[format_pct(s.technical.pct_from_52w_high) for s in stocks])

    # Separator
    table.add_row("", *["" for _ in stocks], style="dim")
    table.add_row("[bold]GROWTH & DIVIDENDS[/]", *["" for _ in stocks])

    # Growth
    table.add_row("Revenue Growth", *[format_pct(s.growth.revenue_growth_yoy) for s in stocks])
    table.add_row("Earnings Growth", *[format_pct(s.growth.earnings_growth_yoy) for s in stocks])
    table.add_row("Dividend Yield", *[format_pct(s.dividends.dividend_yield) for s in stocks])

    # Separator
    table.add_row("", *["" for _ in stocks], style="dim")

    # Signal
    signals = []
    for s in stocks:
        sig = get_signal_display(s.signal)
        signals.append(sig)
    table.add_row("[bold]Signal[/]", *signals)

    console.print(table)
    console.print()
    console.print(
        "[dim italic]Disclaimer: This is for informational purposes only, not financial advice.[/]"
    )
    console.print()


def _validate_output_path(output_path: str) -> str:
    """Validate that output path doesn't escape the current working directory."""
    from pathlib import Path

    resolved = Path(output_path).resolve()
    cwd = Path.cwd().resolve()
    if not str(resolved).startswith(str(cwd)):
        raise typer.BadParameter(
            f"Output path must be within the current directory. Got: {output_path}"
        )
    return str(resolved)


def export_stocks(stocks: list[Stock], format: str, output_path: Optional[str]) -> None:
    """Export stock data to JSON or CSV."""
    format = format.lower()

    if format not in ("json", "csv"):
        console.print(f"[red]Error: Unknown export format '{format}'. Use 'json' or 'csv'.[/]")
        raise typer.Exit(1)

    # Prepare data
    data = []
    for stock in stocks:
        stock_data = {
            "ticker": stock.ticker,
            "name": stock.name,
            "sector": stock.sector,
            "industry": stock.industry,
            "price": stock.current_price,
            "market_cap": stock.valuation.market_cap,
            "pe_trailing": stock.valuation.pe_trailing,
            "pe_forward": stock.valuation.pe_forward,
            "pb_ratio": stock.valuation.pb_ratio,
            "ps_ratio": stock.valuation.ps_ratio,
            "ev_ebitda": stock.valuation.ev_ebitda,
            "graham_number": stock.fair_value.graham_number,
            "dcf_value": stock.fair_value.dcf_value,
            "margin_of_safety_pct": stock.fair_value.margin_of_safety_pct,
            "roe": stock.profitability.roe,
            "roa": stock.profitability.roa,
            "gross_margin": stock.profitability.gross_margin,
            "net_margin": stock.profitability.net_margin,
            "current_ratio": stock.financial_health.current_ratio,
            "debt_to_equity": stock.financial_health.debt_to_equity,
            "free_cash_flow": stock.financial_health.free_cash_flow,
            "rsi_14": stock.technical.rsi_14,
            "price_vs_200ma_pct": stock.technical.price_vs_ma_200_pct,
            "pct_from_52w_low": stock.technical.pct_from_52w_low,
            "pct_from_52w_high": stock.technical.pct_from_52w_high,
            "revenue_growth_yoy": stock.growth.revenue_growth_yoy,
            "earnings_growth_yoy": stock.growth.earnings_growth_yoy,
            "dividend_yield": stock.dividends.dividend_yield,
            "signal": stock.signal,
        }
        data.append(stock_data)

    # Determine output path
    if output_path is None:
        if len(stocks) == 1:
            output_path = f"{stocks[0].ticker.lower()}.{format}"
        else:
            output_path = f"comparison.{format}"

    # Validate output path to prevent path traversal
    output_path = _validate_output_path(output_path)

    # Export
    if format == "json":
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
    else:  # csv
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    console.print(f"[green]Exported to {output_path}[/]")
