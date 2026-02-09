"""CLI command for quarterly financial analysis."""

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tradfi.core.quarterly import fetch_quarterly_financials, get_quarterly_summary
from tradfi.utils.sparkline import format_large_number, sparkline, trend_indicator

console = Console()


def quarterly(
    tickers: list[str] = typer.Argument(
        ...,
        help="Stock ticker(s) to analyze (e.g., AAPL or AAPL MSFT GOOGL)",
    ),
    periods: int = typer.Option(
        8,
        "--periods",
        "-p",
        help="Number of quarters to fetch (default 8)",
    ),
    compare: bool = typer.Option(
        False,
        "--compare",
        "-c",
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


def _color_value(
    value: float | None,
    formatted: str,
    thresholds: list[tuple[float, str]],
    default_style: str = "",
) -> str:
    """Apply Rich color markup based on value thresholds.

    Args:
        value: The numeric value to evaluate
        formatted: The pre-formatted string to wrap
        thresholds: List of (threshold, style) pairs, checked in order.
                    First threshold where value < threshold wins.
        default_style: Style if no threshold matches
    """
    if value is None:
        return formatted
    for threshold, style in thresholds:
        if value < threshold:
            return f"[{style}]{formatted}[/]"
    return f"[{default_style}]{formatted}[/]" if default_style else formatted


def _display_quarterly(ticker: str, periods: int) -> None:
    """Display quarterly analysis for a single ticker."""
    console.print(f"\n[bold cyan]Fetching quarterly data for {ticker}...[/]")

    trends = fetch_quarterly_financials(ticker, periods)

    if not trends or not trends.quarters:
        console.print(f"[red]Could not fetch quarterly data for {ticker}.[/]")
        return

    summary = get_quarterly_summary(trends)

    # Header
    console.print(
        Panel(
            f"[bold]{ticker}[/] - Quarterly Financial Analysis\n"
            f"[dim]Latest: {summary['latest_quarter']}"
            f" | {summary['quarters_available']} quarters of data[/]",
            style="cyan",
        )
    )

    # Revenue sparkline
    revenues = trends.get_metric_values("revenue")
    rev_spark = sparkline(list(reversed(revenues)), width=periods)
    rev_trend = trend_indicator(list(reversed(revenues)))
    qoq_rev = summary.get("qoq_revenue_growth")
    qoq_rev_str = f"{qoq_rev:+.1f}%" if qoq_rev is not None else "N/A"

    console.print("\n[bold magenta]Revenue[/]")
    console.print(f"  Latest:   {format_large_number(summary['revenue'])}")
    console.print(f"  Trend:    {rev_spark}  {rev_trend}  [dim]({summary['revenue_trend']})[/]")
    console.print(f"  QoQ:      {qoq_rev_str}")

    # Earnings sparkline
    earnings = trends.get_metric_values("net_income")
    earn_spark = sparkline(list(reversed(earnings)), width=periods)
    earn_trend = trend_indicator(list(reversed(earnings)))
    qoq_earn = summary.get("qoq_earnings_growth")
    qoq_earn_str = f"{qoq_earn:+.1f}%" if qoq_earn is not None else "N/A"

    console.print("\n[bold magenta]Net Income[/]")
    console.print(f"  Latest:   {format_large_number(summary['net_income'])}")
    console.print(f"  Trend:    {earn_spark}  {earn_trend}")
    console.print(f"  QoQ:      {qoq_earn_str}")

    # Margins sparkline
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

    # P/E sparkline
    pe_values = trends.get_metric_values("pe_ratio")
    if pe_values:
        pe_spark = sparkline(list(reversed(pe_values)), width=periods)
        pe_trend = trend_indicator(list(reversed(pe_values)))
        pe_latest = pe_values[0]
        pe_color = "green" if pe_latest < 15 else "yellow" if pe_latest < 25 else "red"
        console.print("\n[bold magenta]Trailing P/E[/]")
        console.print(f"  Latest:   [{pe_color}]{pe_latest:.1f}[/]")
        console.print(f"  Trend:    {pe_spark}  {pe_trend}")

    # FCF sparkline
    fcfs = trends.get_metric_values("free_cash_flow")
    if fcfs:
        fcf_spark = sparkline(list(reversed(fcfs)), width=periods)
        fcf_trend = trend_indicator(list(reversed(fcfs)))
        console.print("\n[bold magenta]Free Cash Flow[/]")
        console.print(f"  Latest:   {format_large_number(fcfs[0])}")
        console.print(f"  Trend:    {fcf_spark}  {fcf_trend}")

    # Valuation Evolution Table
    console.print("\n[bold magenta]Valuation Evolution[/]")
    table = Table(
        show_header=True,
        header_style="bold",
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("Quarter", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Mkt Cap", justify="right")
    table.add_column("P/E", justify="right")
    table.add_column("P/B", justify="right")
    table.add_column("PEG", justify="right")
    table.add_column("D/E", justify="right")
    table.add_column("EPS", justify="right")
    table.add_column("Revenue", justify="right")
    table.add_column("Op %", justify="right")
    table.add_column("FCF", justify="right")
    table.add_column("Shares", justify="right")

    for q in trends.quarters:
        # Price
        price_str = f"${q.price_at_quarter_end:.2f}" if q.price_at_quarter_end is not None else "-"

        # Market Cap
        mcap_str = format_large_number(q.market_cap) if q.market_cap is not None else "-"

        # P/E with Graham thresholds
        if q.pe_ratio is not None:
            pe_str = _color_value(
                q.pe_ratio,
                f"{q.pe_ratio:.1f}",
                [(15, "green"), (25, "yellow")],
                default_style="red",
            )
        else:
            pe_str = "-"

        # P/B with Graham thresholds
        if q.pb_ratio is not None:
            pb_str = _color_value(
                q.pb_ratio,
                f"{q.pb_ratio:.1f}",
                [(1.5, "green"), (3.0, "yellow")],
                default_style="red",
            )
        else:
            pb_str = "-"

        # PEG with negative handling
        if q.peg_ratio is not None:
            if q.peg_ratio < 0:
                peg_str = f"[red]{q.peg_ratio:.2f}[/]"
            else:
                peg_str = _color_value(
                    q.peg_ratio,
                    f"{q.peg_ratio:.2f}",
                    [(1.0, "green"), (2.0, "yellow")],
                    default_style="red",
                )
        else:
            peg_str = "-"

        # D/E ratio with Burry thresholds
        if q.debt_to_equity is not None:
            de_str = _color_value(
                q.debt_to_equity,
                f"{q.debt_to_equity:.2f}",
                [(0.5, "green"), (1.0, "yellow")],
                default_style="red",
            )
        else:
            de_str = "-"

        # EPS with color
        if q.eps is not None:
            eps_color = "green" if q.eps > 0 else "red"
            eps_str = f"[{eps_color}]{q.eps:.2f}[/]"
        else:
            eps_str = "-"

        # Revenue
        rev_str = format_large_number(q.revenue) if q.revenue is not None else "-"

        # Operating margin
        if q.operating_margin is not None:
            om_color = "green" if q.operating_margin > 0 else "red"
            om_str_cell = f"[{om_color}]{q.operating_margin:.1f}%[/]"
        else:
            om_str_cell = "-"

        # FCF
        if q.free_cash_flow is not None:
            fcf_color = "green" if q.free_cash_flow > 0 else "red"
            fcf_str = f"[{fcf_color}]{format_large_number(q.free_cash_flow)}[/]"
        else:
            fcf_str = "-"

        # Shares outstanding
        shares_str = (
            format_large_number(q.shares_outstanding) if q.shares_outstanding is not None else "-"
        )

        table.add_row(
            q.quarter,
            price_str,
            mcap_str,
            pe_str,
            pb_str,
            peg_str,
            de_str,
            eps_str,
            rev_str,
            om_str_cell,
            fcf_str,
            shares_str,
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
