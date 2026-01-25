"""Screen command - filter stocks by value and technical criteria."""

from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box

from tradfi.core.data import fetch_stock
from tradfi.core.screener import (
    ScreenCriteria,
    load_tickers,
    screen_stock,
    get_preset_screen,
    list_available_universes,
    PRESET_SCREENS,
    AVAILABLE_UNIVERSES,
)
from tradfi.models.stock import Stock
from tradfi.utils.display import format_number, format_pct, get_signal_display
from tradfi.utils.cache import save_list

console = Console()


def screen(
    # Universe selection
    universe: str = typer.Option(
        "sp500",
        "--universe", "-u",
        help="Stock universe(s): sp500, dow30, nasdaq100, russell2000, etc. Use comma to combine (e.g., sp500,nasdaq100)",
    ),
    all_universes: bool = typer.Option(
        False,
        "--all", "-a",
        help="Search across ALL universes",
    ),
    exclude: Optional[str] = typer.Option(
        None,
        "--exclude", "-x",
        help="Exclude universe(s) from search. Comma-separated (e.g., --exclude russell2000,international)",
    ),
    list_universes: bool = typer.Option(
        False,
        "--list-universes", "--universes",
        help="List all available stock universes",
    ),
    tickers: Optional[str] = typer.Option(
        None,
        "--tickers", "-t",
        help="Comma-separated list of tickers to screen (overrides universe)",
    ),
    # Pre-built screens
    preset: Optional[str] = typer.Option(
        None,
        "--preset", "-p",
        help="Pre-built screen: graham, buffett, dividend, fallen-angels, hidden-gems, oversold, turnaround",
    ),
    # Valuation filters
    pe_max: Optional[float] = typer.Option(None, "--pe-max", help="Maximum P/E ratio"),
    pe_min: Optional[float] = typer.Option(None, "--pe-min", help="Minimum P/E ratio"),
    pb_max: Optional[float] = typer.Option(None, "--pb-max", help="Maximum P/B ratio"),
    pb_min: Optional[float] = typer.Option(None, "--pb-min", help="Minimum P/B ratio"),
    ps_max: Optional[float] = typer.Option(None, "--ps-max", help="Maximum P/S ratio"),
    # Profitability filters
    roe_min: Optional[float] = typer.Option(None, "--roe-min", help="Minimum ROE (%)"),
    roe_max: Optional[float] = typer.Option(None, "--roe-max", help="Maximum ROE (%) - for finding weak stocks"),
    roa_min: Optional[float] = typer.Option(None, "--roa-min", help="Minimum ROA (%)"),
    margin_min: Optional[float] = typer.Option(None, "--margin-min", help="Minimum net margin (%)"),
    margin_max: Optional[float] = typer.Option(None, "--margin-max", help="Maximum net margin (%) - for finding weak stocks"),
    # Financial health filters
    debt_equity_max: Optional[float] = typer.Option(
        None, "--debt-equity-max", "--de-max",
        help="Maximum debt/equity ratio (e.g., 0.5 for 50%)",
    ),
    current_ratio_min: Optional[float] = typer.Option(
        None, "--current-min",
        help="Minimum current ratio",
    ),
    # Dividend filters
    dividend_yield_min: Optional[float] = typer.Option(
        None, "--div-min",
        help="Minimum dividend yield (%)",
    ),
    # Technical / Oversold filters
    rsi_max: Optional[float] = typer.Option(
        None, "--rsi-max",
        help="Maximum RSI (e.g., 30 for oversold)",
    ),
    rsi_min: Optional[float] = typer.Option(
        None, "--rsi-min",
        help="Minimum RSI",
    ),
    near_52w_low: Optional[float] = typer.Option(
        None, "--near-52w-low",
        help="Within X% of 52-week low",
    ),
    below_200ma: bool = typer.Option(
        False, "--below-200ma",
        help="Price below 200-day moving average",
    ),
    below_50ma: bool = typer.Option(
        False, "--below-50ma",
        help="Price below 50-day moving average",
    ),
    # Sector filter
    sector: Optional[str] = typer.Option(
        None, "--sector", "-i",
        help="Filter by sector (e.g., 'Technology', 'Healthcare', 'Financial'). Partial match. Comma-separated for multiple.",
    ),
    exclude_sector: Optional[str] = typer.Option(
        None, "--exclude-sector", "-xi",
        help="Exclude sectors. Comma-separated (e.g., --exclude-sector Technology,Energy)",
    ),
    list_sectors: bool = typer.Option(
        False, "--list-sectors", "--sectors",
        help="List all available sectors",
    ),
    # Output options
    limit: int = typer.Option(
        20, "--limit", "-l",
        help="Maximum number of results to show",
    ),
    sort_by: str = typer.Option(
        "pe",
        "--sort", "-s",
        help="Sort by: pe, pb, roe, rsi, div, margin-of-safety (mos), sector",
    ),
    group_by_sector: bool = typer.Option(
        False, "--group-by-sector", "-g",
        help="Group results by sector",
    ),
    # Save results
    save_as: Optional[str] = typer.Option(
        None, "--save",
        help="Save results to a named list (e.g., --save my-value-picks)",
    ),
) -> None:
    """
    Screen stocks by value metrics and oversold indicators.

    Examples:
        tradfi screen --list-universes
        tradfi screen --list-sectors
        tradfi screen --preset graham
        tradfi screen --universe nasdaq100 --pe-max 25
        tradfi screen --universe sp500,nasdaq100 --pe-max 20
        tradfi screen --sector Technology --pe-max 25
        tradfi screen --sector Technology,Healthcare --all
        tradfi screen --sector Technology --all --exclude russell2000
        tradfi screen --universe sp500 --exclude-sector Energy,Utilities
        tradfi screen --universe sp500 --group-by-sector
        tradfi screen --pe-max 15 --roe-min 15 --rsi-max 30
        tradfi screen -t AAPL,MSFT,GOOGL,AMZN --pe-max 30
    """
    # Handle --list-universes flag
    if list_universes:
        _display_universes()
        return

    # Handle --list-sectors flag
    if list_sectors:
        _display_sectors()
        return

    # Build criteria
    if preset:
        try:
            criteria = get_preset_screen(preset)
            console.print(f"[dim]Using preset: {preset}[/]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/]")
            raise typer.Exit(1)
    else:
        criteria = ScreenCriteria()

    # Override with CLI options
    if pe_max is not None:
        criteria.pe_max = pe_max
    if pe_min is not None:
        criteria.pe_min = pe_min
    if pb_max is not None:
        criteria.pb_max = pb_max
    if pb_min is not None:
        criteria.pb_min = pb_min
    if ps_max is not None:
        criteria.ps_max = ps_max
    if roe_min is not None:
        criteria.roe_min = roe_min
    if roe_max is not None:
        criteria.roe_max = roe_max
    if roa_min is not None:
        criteria.roa_min = roa_min
    if margin_min is not None:
        criteria.margin_min = margin_min
    if margin_max is not None:
        criteria.margin_max = margin_max
    if debt_equity_max is not None:
        # Convert ratio to percentage for internal use
        criteria.debt_equity_max = debt_equity_max * 100
    if current_ratio_min is not None:
        criteria.current_ratio_min = current_ratio_min
    if dividend_yield_min is not None:
        criteria.dividend_yield_min = dividend_yield_min
    if rsi_max is not None:
        criteria.rsi_max = rsi_max
    if rsi_min is not None:
        criteria.rsi_min = rsi_min
    if near_52w_low is not None:
        criteria.near_52w_low_pct = near_52w_low
    if below_200ma:
        criteria.below_200ma = True
    if below_50ma:
        criteria.below_50ma = True

    # Get ticker list
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        console.print(f"[dim]Screening {len(ticker_list)} tickers[/]")
    else:
        # Parse exclusions
        excluded_universes = set()
        if exclude:
            excluded_universes = {x.strip().lower() for x in exclude.split(",")}

        # Build ticker list from universes
        ticker_set: set[str] = set()
        universes_used: list[str] = []

        if all_universes:
            # Use all available universes except excluded ones
            for name in AVAILABLE_UNIVERSES.keys():
                if name.lower() not in excluded_universes:
                    try:
                        ticker_set.update(load_tickers(name))
                        universes_used.append(name)
                    except FileNotFoundError:
                        pass
        else:
            # Parse comma-separated universes
            universe_names = [u.strip() for u in universe.split(",")]
            for name in universe_names:
                if name.lower() not in excluded_universes:
                    try:
                        ticker_set.update(load_tickers(name))
                        universes_used.append(name)
                    except FileNotFoundError as e:
                        console.print(f"[red]Error: Unknown universe '{name}'[/]")
                        raise typer.Exit(1)

        ticker_list = sorted(ticker_set)

        if not ticker_list:
            console.print("[red]No tickers to screen. Check universe/exclude options.[/]")
            raise typer.Exit(1)

        # Display info
        if len(universes_used) == 1:
            console.print(f"[dim]Screening {universes_used[0]} ({len(ticker_list)} tickers)[/]")
        else:
            console.print(f"[dim]Screening {len(universes_used)} universes ({len(ticker_list)} unique tickers)[/]")
            if excluded_universes:
                console.print(f"[dim]Excluded: {', '.join(excluded_universes)}[/]")

    # Screen stocks with progress bar
    passing_stocks: list[Stock] = []
    failed_tickers: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Screening stocks...", total=len(ticker_list))

        for ticker in ticker_list:
            progress.update(task, description=f"Checking {ticker}...")

            stock = fetch_stock(ticker)
            if stock is None:
                failed_tickers.append(ticker)
            elif screen_stock(stock, criteria):
                # Apply sector filter if specified (inclusion)
                if sector:
                    stock_sector = stock.sector or ""
                    # Support comma-separated sectors (match any)
                    sector_filters = [s.strip().lower() for s in sector.split(",")]
                    if not any(f in stock_sector.lower() for f in sector_filters):
                        progress.advance(task)
                        continue
                # Apply sector exclusion filter
                if exclude_sector:
                    stock_sector = stock.sector or ""
                    excluded_sectors = [s.strip().lower() for s in exclude_sector.split(",")]
                    if any(ex in stock_sector.lower() for ex in excluded_sectors):
                        progress.advance(task)
                        continue
                passing_stocks.append(stock)

            progress.advance(task)

    # Sort results
    passing_stocks = sort_stocks(passing_stocks, sort_by)

    # Limit results
    if len(passing_stocks) > limit:
        passing_stocks = passing_stocks[:limit]

    # Display results
    console.print()

    if not passing_stocks:
        console.print("[yellow]No stocks matched the screening criteria.[/]")
        if failed_tickers:
            console.print(f"[dim]({len(failed_tickers)} tickers failed to fetch)[/]")
        return

    # Group by sector if requested
    if group_by_sector:
        _display_grouped_by_sector(passing_stocks, failed_tickers)
        return

    # Build results table
    table = Table(
        title=f"Screening Results ({len(passing_stocks)} stocks)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("Ticker", style="bold cyan")
    table.add_column("Sector", max_width=20)
    table.add_column("Price", justify="right")
    table.add_column("P/E", justify="right")
    table.add_column("P/B", justify="right")
    table.add_column("ROE", justify="right")
    table.add_column("D/E", justify="right")
    table.add_column("RSI", justify="right")
    table.add_column("vs 52W Low", justify="right")
    table.add_column("Signal", justify="center")

    for stock in passing_stocks:
        # Format values
        price = f"${stock.current_price:.2f}" if stock.current_price else "N/A"
        pe = format_number(stock.valuation.pe_trailing, 1)
        pb = format_number(stock.valuation.pb_ratio, 2)
        roe = format_pct(stock.profitability.roe)

        # D/E ratio (convert from percentage)
        de = stock.financial_health.debt_to_equity
        de_str = format_number(de / 100, 2) if de is not None else "N/A"

        rsi = format_number(stock.technical.rsi_14, 0)
        vs_low = format_pct(stock.technical.pct_from_52w_low)

        # Format sector (compact)
        sector_display = _truncate_sector(stock.sector) if stock.sector else "N/A"

        # Color RSI
        rsi_val = stock.technical.rsi_14
        if rsi_val is not None:
            if rsi_val < 30:
                rsi = f"[green]{rsi}[/]"
            elif rsi_val < 40:
                rsi = f"[yellow]{rsi}[/]"

        # Color vs 52W Low
        low_val = stock.technical.pct_from_52w_low
        if low_val is not None and low_val < 15:
            vs_low = f"[green]{vs_low}[/]"

        signal = get_signal_display(stock.signal)

        table.add_row(
            stock.ticker,
            sector_display,
            price,
            pe,
            pb,
            roe,
            de_str,
            rsi,
            vs_low,
            signal,
        )

    console.print(table)

    # Save results if requested
    if save_as and passing_stocks:
        tickers_to_save = [s.ticker for s in passing_stocks]
        description = f"Screen results: {preset or 'custom'}"
        if universe != "sp500" or tickers:
            description += f" from {universe if not tickers else 'custom tickers'}"
        save_list(save_as, tickers_to_save, description)
        console.print(f"\n[green]✓ Saved {len(tickers_to_save)} stocks to list '{save_as}'[/]")
        console.print(f"[dim]View with: tradfi list show {save_as}[/]")

    # Footer
    console.print()
    console.print(f"[dim]Use 'tradfi analyze <ticker>' for detailed analysis[/]")

    if failed_tickers:
        console.print(f"[dim]({len(failed_tickers)} tickers failed to fetch)[/]")


def _truncate_sector(sector: str) -> str:
    """Truncate sector name for compact display."""
    # Shorten common sector names
    sec = sector
    sec = sec.replace("Communication Services", "Comm Services")
    sec = sec.replace("Consumer Cyclical", "Consumer Cyc")
    sec = sec.replace("Consumer Defensive", "Consumer Def")
    sec = sec.replace("Financial Services", "Financial")
    # Truncate if still too long
    if len(sec) > 20:
        sec = sec[:18] + ".."
    return sec


def sort_stocks(stocks: list[Stock], sort_by: str) -> list[Stock]:
    """Sort stocks by the specified metric."""
    sort_by = sort_by.lower()

    def safe_sort_key(stock: Stock, getter, reverse: bool = False):
        val = getter(stock)
        if val is None:
            return float("inf") if not reverse else float("-inf")
        return val

    if sort_by == "pe":
        return sorted(stocks, key=lambda s: safe_sort_key(s, lambda x: x.valuation.pe_trailing))
    elif sort_by == "pb":
        return sorted(stocks, key=lambda s: safe_sort_key(s, lambda x: x.valuation.pb_ratio))
    elif sort_by == "roe":
        return sorted(
            stocks,
            key=lambda s: safe_sort_key(s, lambda x: x.profitability.roe, reverse=True),
            reverse=True,
        )
    elif sort_by == "rsi":
        return sorted(stocks, key=lambda s: safe_sort_key(s, lambda x: x.technical.rsi_14))
    elif sort_by == "div":
        return sorted(
            stocks,
            key=lambda s: safe_sort_key(s, lambda x: x.dividends.dividend_yield, reverse=True),
            reverse=True,
        )
    elif sort_by in ("mos", "margin-of-safety"):
        return sorted(
            stocks,
            key=lambda s: safe_sort_key(s, lambda x: x.fair_value.margin_of_safety_pct, reverse=True),
            reverse=True,
        )
    elif sort_by == "sector":
        return sorted(stocks, key=lambda s: (s.sector or "ZZZ", s.valuation.pe_trailing or float("inf")))
    else:
        return stocks


def _display_universes() -> None:
    """Display all available stock universes."""
    universes = list_available_universes()

    console.print()

    table = Table(
        title="Available Stock Universes",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("Universe", style="bold cyan")
    table.add_column("Description")
    table.add_column("Stocks", justify="right")

    for name, (description, count) in universes.items():
        table.add_row(name, description, str(count))

    console.print(table)
    console.print()
    console.print("[dim]Usage: tradfi screen --universe <name> [filters][/]")
    console.print("[dim]Example: tradfi screen -u nasdaq100 --pe-max 25[/]")
    console.print()


# Common sectors for reference
COMMON_SECTORS = [
    "Technology",
    "Healthcare",
    "Financial Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Industrials",
    "Energy",
    "Basic Materials",
    "Real Estate",
    "Utilities",
    "Communication Services",
]


def _display_sectors() -> None:
    """Display all common sectors."""
    console.print()

    table = Table(
        title="Common Stock Sectors",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("Sector", style="bold cyan")
    table.add_column("Filter Example")

    for sector in COMMON_SECTORS:
        # Create filter example with lowercase for partial matching
        filter_key = sector.split()[0].lower()
        table.add_row(sector, f"--sector {filter_key}")

    console.print(table)
    console.print()
    console.print("[dim]Note: Sector filter uses partial matching (case-insensitive)[/]")
    console.print("[dim]Example: tradfi screen --sector tech --pe-max 25[/]")
    console.print("[dim]Example: tradfi screen --sector healthcare --roe-min 15[/]")
    console.print()


def _display_grouped_by_sector(stocks: list[Stock], failed_tickers: list[str]) -> None:
    """Display stocks grouped by sector."""
    from collections import defaultdict

    # Group stocks by sector
    sectors: dict[str, list[Stock]] = defaultdict(list)
    for stock in stocks:
        sector = stock.sector or "Unknown"
        sectors[sector].append(stock)

    # Sort sectors alphabetically
    sorted_sectors = sorted(sectors.keys())

    console.print(f"\n[bold]Screening Results ({len(stocks)} stocks in {len(sorted_sectors)} sectors)[/]\n")

    for sector in sorted_sectors:
        sector_stocks = sectors[sector]

        # Create table for this sector
        table = Table(
            title=f"{sector} ({len(sector_stocks)})",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold",
            title_style="bold magenta",
        )

        table.add_column("Ticker", style="bold cyan")
        table.add_column("Price", justify="right")
        table.add_column("P/E", justify="right")
        table.add_column("P/B", justify="right")
        table.add_column("ROE", justify="right")
        table.add_column("RSI", justify="right")
        table.add_column("Signal", justify="center")

        # Sort stocks within sector by P/E
        sector_stocks_sorted = sorted(
            sector_stocks,
            key=lambda s: s.valuation.pe_trailing if s.valuation.pe_trailing and s.valuation.pe_trailing > 0 else float("inf")
        )

        for stock in sector_stocks_sorted:
            price = f"${stock.current_price:.2f}" if stock.current_price else "N/A"
            pe = format_number(stock.valuation.pe_trailing, 1)
            pb = format_number(stock.valuation.pb_ratio, 2)
            roe = format_pct(stock.profitability.roe)
            rsi = format_number(stock.technical.rsi_14, 0)

            # Color RSI
            rsi_val = stock.technical.rsi_14
            if rsi_val is not None:
                if rsi_val < 30:
                    rsi = f"[green]{rsi}[/]"
                elif rsi_val < 40:
                    rsi = f"[yellow]{rsi}[/]"

            signal = get_signal_display(stock.signal)

            table.add_row(
                stock.ticker,
                price,
                pe,
                pb,
                roe,
                rsi,
                signal,
            )

        console.print(table)
        console.print()

    # Footer
    console.print(f"[dim]Use 'tradfi analyze <ticker>' for detailed analysis[/]")

    if failed_tickers:
        console.print(f"[dim]({len(failed_tickers)} tickers failed to fetch)[/]")
