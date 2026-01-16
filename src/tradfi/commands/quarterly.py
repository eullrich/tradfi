"""CLI command for quarterly financial analysis."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tradfi.core.quarterly import fetch_quarterly_financials, get_quarterly_summary
from tradfi.utils.sparkline import sparkline, format_large_number, trend_indicator

console = Console()


def quarterly(
    tickers: list[str] = typer.Argument(
        ...,
        help="Stock ticker(s) to analyze (e.g., AAPL or AAPL MSFT GOOGL)",
    ),
    periods: int = typer.Option(
        8,
        "--periods", "-p",
        help="Number of quarters to fetch (default 8)",
    ),
    compare: bool = typer.Option(
        False,
        "--compare", "-c",
        help="Show side-by-side comparison (for multiple tickers)",
    ),
) -> None:
    """
    Analyze quarterly financial trends for one or more stocks.

    Shows revenue, earnings, and margin trends with sparkline visualizations.

    Examples:
        tradfi quarterly AAPL
        tradfi quarterly AAPL MSFT GOOGL --compare
        tradfi quarterly NVDA --periods 12
    """
    if not tickers:
        console.print("[red]Please provide at least one ticker.[/]")
        raise typer.Exit(1)

    if compare and len(tickers) > 1:
        _display_comparison(tickers, periods)
    else:
        for ticker in tickers:
            _display_quarterly(ticker.upper(), periods)
            if len(tickers) > 1:
                console.print()  # Spacing between tickers


def _display_quarterly(ticker: str, periods: int) -> None:
    """Display quarterly analysis for a single ticker."""
    console.print(f"\n[bold cyan]Fetching quarterly data for {ticker}...[/]")

    trends = fetch_quarterly_financials(ticker, periods)

    if not trends or not trends.quarters:
        console.print(f"[red]Could not fetch quarterly data for {ticker}.[/]")
        return

    summary = get_quarterly_summary(trends)

    # Header
    console.print(Panel(
        f"[bold]{ticker}[/] - Quarterly Financial Analysis\n"
        f"[dim]Latest: {summary['latest_quarter']} | {summary['quarters_available']} quarters of data[/]",
        style="cyan",
    ))

    # Revenue section
    revenues = trends.get_metric_values("revenue")
    rev_spark = sparkline(list(reversed(revenues)), width=periods)
    rev_trend = trend_indicator(list(reversed(revenues)))
    qoq_rev = summary.get("qoq_revenue_growth")
    qoq_rev_str = f"{qoq_rev:+.1f}%" if qoq_rev is not None else "N/A"

    console.print(f"\n[bold magenta]Revenue[/]")
    console.print(f"  Latest:   {format_large_number(summary['revenue'])}")
    console.print(f"  Trend:    {rev_spark}  {rev_trend}  [dim]({summary['revenue_trend']})[/]")
    console.print(f"  QoQ:      {qoq_rev_str}")

    # Earnings section
    earnings = trends.get_metric_values("net_income")
    earn_spark = sparkline(list(reversed(earnings)), width=periods)
    earn_trend = trend_indicator(list(reversed(earnings)))
    qoq_earn = summary.get("qoq_earnings_growth")
    qoq_earn_str = f"{qoq_earn:+.1f}%" if qoq_earn is not None else "N/A"

    console.print(f"\n[bold magenta]Net Income[/]")
    console.print(f"  Latest:   {format_large_number(summary['net_income'])}")
    console.print(f"  Trend:    {earn_spark}  {earn_trend}")
    console.print(f"  QoQ:      {qoq_earn_str}")

    # Margins section
    gross_margins = trends.get_metric_values("gross_margin")
    gm_spark = sparkline(list(reversed(gross_margins)), width=periods)
    gm_latest = summary.get("gross_margin")
    gm_str = f"{gm_latest:.1f}%" if gm_latest is not None else "N/A"

    op_margins = trends.get_metric_values("operating_margin")
    om_spark = sparkline(list(reversed(op_margins)), width=periods)
    om_latest = summary.get("operating_margin")
    om_str = f"{om_latest:.1f}%" if om_latest is not None else "N/A"

    net_margins = trends.get_metric_values("net_margin")
    nm_spark = sparkline(list(reversed(net_margins)), width=periods)
    nm_latest = summary.get("net_margin")
    nm_str = f"{nm_latest:.1f}%" if nm_latest is not None else "N/A"

    console.print(f"\n[bold magenta]Margins[/]  [dim]({summary['margin_trend']})[/]")
    console.print(f"  Gross:    {gm_str:>8}  {gm_spark}")
    console.print(f"  Operating:{om_str:>8}  {om_spark}")
    console.print(f"  Net:      {nm_str:>8}  {nm_spark}")

    # Quarterly detail table
    console.print(f"\n[bold magenta]Quarter Detail[/]")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Quarter", style="cyan")
    table.add_column("Revenue", justify="right")
    table.add_column("Net Inc", justify="right")
    table.add_column("Gross %", justify="right")
    table.add_column("Op %", justify="right")
    table.add_column("Net %", justify="right")

    for q in trends.quarters[:6]:  # Show last 6 quarters
        table.add_row(
            q.quarter,
            format_large_number(q.revenue) if q.revenue else "-",
            format_large_number(q.net_income) if q.net_income else "-",
            f"{q.gross_margin:.1f}%" if q.gross_margin else "-",
            f"{q.operating_margin:.1f}%" if q.operating_margin else "-",
            f"{q.net_margin:.1f}%" if q.net_margin else "-",
        )

    console.print(table)


def _display_comparison(tickers: list[str], periods: int) -> None:
    """Display side-by-side comparison of multiple tickers."""
    console.print(f"\n[bold cyan]Comparing quarterly data for {', '.join(tickers)}...[/]")

    # Fetch data for all tickers
    data = {}
    for ticker in tickers:
        ticker = ticker.upper()
        trends = fetch_quarterly_financials(ticker, periods)
        if trends and trends.quarters:
            data[ticker] = {
                "trends": trends,
                "summary": get_quarterly_summary(trends),
            }
        else:
            console.print(f"[yellow]Warning: Could not fetch data for {ticker}[/]")

    if not data:
        console.print("[red]No data available for comparison.[/]")
        return

    # Create comparison table
    table = Table(title="Quarterly Comparison", show_header=True, header_style="bold")
    table.add_column("Metric", style="magenta")

    for ticker in data.keys():
        table.add_column(ticker, justify="right")

    # Revenue row
    rev_values = [format_large_number(data[t]["summary"]["revenue"]) for t in data.keys()]
    table.add_row("Revenue", *rev_values)

    # Revenue trend sparklines
    rev_sparks = []
    for t in data.keys():
        revenues = data[t]["trends"].get_metric_values("revenue")
        spark = sparkline(list(reversed(revenues)), width=8)
        rev_sparks.append(spark)
    table.add_row("  Trend", *rev_sparks)

    # QoQ Revenue Growth
    qoq_revs = []
    for t in data.keys():
        qoq = data[t]["summary"].get("qoq_revenue_growth")
        qoq_revs.append(f"{qoq:+.1f}%" if qoq is not None else "N/A")
    table.add_row("  QoQ Growth", *qoq_revs)

    table.add_row("", *["" for _ in data.keys()])  # Spacer

    # Net Income row
    ni_values = [format_large_number(data[t]["summary"]["net_income"]) for t in data.keys()]
    table.add_row("Net Income", *ni_values)

    # Net Income trend sparklines
    ni_sparks = []
    for t in data.keys():
        incomes = data[t]["trends"].get_metric_values("net_income")
        spark = sparkline(list(reversed(incomes)), width=8)
        ni_sparks.append(spark)
    table.add_row("  Trend", *ni_sparks)

    table.add_row("", *["" for _ in data.keys()])  # Spacer

    # Margins
    gm_values = []
    for t in data.keys():
        gm = data[t]["summary"].get("gross_margin")
        gm_values.append(f"{gm:.1f}%" if gm is not None else "N/A")
    table.add_row("Gross Margin", *gm_values)

    om_values = []
    for t in data.keys():
        om = data[t]["summary"].get("operating_margin")
        om_values.append(f"{om:.1f}%" if om is not None else "N/A")
    table.add_row("Operating Margin", *om_values)

    nm_values = []
    for t in data.keys():
        nm = data[t]["summary"].get("net_margin")
        nm_values.append(f"{nm:.1f}%" if nm is not None else "N/A")
    table.add_row("Net Margin", *nm_values)

    # Trend summaries
    table.add_row("", *["" for _ in data.keys()])  # Spacer
    rev_trends = [data[t]["summary"]["revenue_trend"] for t in data.keys()]
    table.add_row("Revenue Trend", *rev_trends)

    margin_trends = [data[t]["summary"]["margin_trend"] for t in data.keys()]
    table.add_row("Margin Trend", *margin_trends)

    console.print(table)
