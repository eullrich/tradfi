"""CLI command for comparing stock lists."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from tradfi.core.data import fetch_stock
from tradfi.utils.cache import get_saved_list

console = Console()


def compare(
    list1: str = typer.Argument(..., help="First list name"),
    list2: str = typer.Argument(None, help="Second list name (optional)"),
    metrics: str = typer.Option(
        "pe,roe,mos,rsi,div",
        "--metrics",
        "-m",
        help="Comma-separated metrics to compare (pe,pb,roe,roa,mos,rsi,div,price)",
    ),
) -> None:
    """
    Compare metrics across one or two stock lists.

    Shows aggregate statistics (average, min, max) for key value metrics.

    Examples:
        tradfi compare my-longs my-shorts
        tradfi compare my-picks --metrics pe,roe,mos
        tradfi compare watchlist value-picks -m pe,pb,rsi
    """
    # Parse metrics
    metric_list = [m.strip().lower() for m in metrics.split(",")]

    # Fetch first list
    tickers1 = get_saved_list(list1)
    if not tickers1:
        console.print(f"[red]List '{list1}' not found or empty.[/]")
        raise typer.Exit(1)

    # Fetch second list if provided
    tickers2 = None
    if list2:
        tickers2 = get_saved_list(list2)
        if not tickers2:
            console.print(f"[red]List '{list2}' not found or empty.[/]")
            raise typer.Exit(1)

    console.print("\n[bold cyan]Fetching data for comparison...[/]")

    # Fetch stock data
    stocks1 = _fetch_stocks(tickers1, list1)
    stocks2 = _fetch_stocks(tickers2, list2) if tickers2 else None

    if not stocks1:
        console.print(f"[red]Could not fetch data for list '{list1}'.[/]")
        raise typer.Exit(1)

    # Calculate metrics for each list
    metrics1 = _calculate_metrics(stocks1, metric_list)
    metrics2 = _calculate_metrics(stocks2, metric_list) if stocks2 else None

    # Display comparison table
    _display_comparison(list1, metrics1, list2, metrics2, metric_list)


def _fetch_stocks(tickers: list[str], list_name: str) -> list:
    """Fetch stock data for a list of tickers."""
    stocks = []
    for ticker in tickers:
        console.print(f"  [dim]Fetching {ticker}...[/]", end="\r")
        stock = fetch_stock(ticker)
        if stock:
            stocks.append(stock)
    console.print(" " * 40, end="\r")  # Clear line
    return stocks


def _calculate_metrics(stocks: list, metric_list: list[str]) -> dict:
    """Calculate aggregate metrics for a list of stocks."""
    metrics = {}

    metric_extractors = {
        "pe": lambda s: (
            s.valuation.pe_trailing
            if s.valuation.pe_trailing and s.valuation.pe_trailing > 0
            else None
        ),
        "pb": lambda s: (
            s.valuation.pb_ratio if s.valuation.pb_ratio and s.valuation.pb_ratio > 0 else None
        ),
        "ps": lambda s: (
            s.valuation.ps_ratio if s.valuation.ps_ratio and s.valuation.ps_ratio > 0 else None
        ),
        "roe": lambda s: s.profitability.roe,
        "roa": lambda s: s.profitability.roa,
        "mos": lambda s: s.fair_value.margin_of_safety_pct,
        "rsi": lambda s: s.technical.rsi_14,
        "div": lambda s: s.dividends.dividend_yield,
        "price": lambda s: s.current_price,
        "de": lambda s: (
            s.financial_health.debt_to_equity / 100 if s.financial_health.debt_to_equity else None
        ),
    }

    for metric in metric_list:
        if metric not in metric_extractors:
            continue

        extractor = metric_extractors[metric]
        values = [extractor(s) for s in stocks if extractor(s) is not None]

        if values:
            metrics[metric] = {
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }
        else:
            metrics[metric] = {"avg": None, "min": None, "max": None, "count": 0}

    metrics["_total"] = len(stocks)
    return metrics


def _display_comparison(
    list1: str,
    metrics1: dict,
    list2: str | None,
    metrics2: dict | None,
    metric_list: list[str],
) -> None:
    """Display comparison table."""
    table = Table(title="List Comparison", show_header=True, header_style="bold")

    table.add_column("Metric", style="magenta")
    table.add_column(f"{list1} ({metrics1['_total']})", justify="right")
    if metrics2:
        table.add_column(f"{list2} ({metrics2['_total']})", justify="right")
        table.add_column("Diff", justify="right")

    metric_labels = {
        "pe": "P/E Ratio",
        "pb": "P/B Ratio",
        "ps": "P/S Ratio",
        "roe": "ROE %",
        "roa": "ROA %",
        "mos": "Margin of Safety %",
        "rsi": "RSI (14)",
        "div": "Dividend Yield %",
        "price": "Avg Price $",
        "de": "Debt/Equity",
    }

    for metric in metric_list:
        if metric not in metrics1 or metric not in metric_labels:
            continue

        label = metric_labels[metric]
        m1 = metrics1[metric]

        # Format value 1
        if m1["avg"] is not None:
            if metric in ["roe", "roa", "mos", "div"]:
                val1 = f"{m1['avg']:.1f}%"
            elif metric == "price":
                val1 = f"${m1['avg']:.0f}"
            else:
                val1 = f"{m1['avg']:.1f}"
        else:
            val1 = "N/A"

        if metrics2:
            m2 = metrics2.get(metric, {"avg": None})

            # Format value 2
            if m2["avg"] is not None:
                if metric in ["roe", "roa", "mos", "div"]:
                    val2 = f"{m2['avg']:.1f}%"
                elif metric == "price":
                    val2 = f"${m2['avg']:.0f}"
                else:
                    val2 = f"{m2['avg']:.1f}"
            else:
                val2 = "N/A"

            # Calculate difference
            if m1["avg"] is not None and m2["avg"] is not None:
                diff = m1["avg"] - m2["avg"]
                color = "green" if diff > 0 else "red" if diff < 0 else "dim"
                if metric in ["roe", "roa", "mos", "div"]:
                    diff_str = f"[{color}]{diff:+.1f}%[/]"
                elif metric == "price":
                    diff_str = f"[{color}]${diff:+.0f}[/]"
                else:
                    diff_str = f"[{color}]{diff:+.1f}[/]"
            else:
                diff_str = "-"

            table.add_row(label, val1, val2, diff_str)
        else:
            table.add_row(label, val1)

    console.print(table)

    # Summary interpretation
    if metrics2 and "pe" in metrics1 and "mos" in metrics1:
        console.print("\n[bold]Interpretation:[/]")

        pe1 = metrics1["pe"]["avg"]
        pe2 = metrics2["pe"]["avg"] if metrics2 else None
        mos1 = metrics1.get("mos", {}).get("avg")
        mos2 = metrics2.get("mos", {}).get("avg") if metrics2 else None

        if pe1 and pe2:
            if pe1 < pe2:
                console.print(f"  [green]+[/] {list1} trades at lower P/E (cheaper valuation)")
            else:
                console.print(f"  [green]+[/] {list2} trades at lower P/E (cheaper valuation)")

        if mos1 is not None and mos2 is not None:
            if mos1 > mos2:
                console.print(f"  [green]+[/] {list1} has higher margin of safety")
            else:
                console.print(f"  [green]+[/] {list2} has higher margin of safety")
