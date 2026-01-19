"""Cache management commands."""

import time
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich import box

from tradfi.utils.cache import (
    clear_cache,
    get_cache_stats,
    get_config,
    get_cached_stock_data,
    set_cache_ttl,
    set_rate_limit_delay,
    set_cache_enabled,
    set_offline_mode,
)
from tradfi.core.screener import load_tickers, AVAILABLE_UNIVERSES

console = Console()
app = typer.Typer(help="Manage the stock data cache")


@app.command("status")
def cache_status() -> None:
    """Show cache status and statistics."""
    stats = get_cache_stats()
    config = get_config()

    table = Table(title="Cache Status", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Cache Enabled", "Yes" if stats["cache_enabled"] else "No")
    offline_status = "[bold green]Yes (DB only)[/]" if config.offline_mode else "No"
    table.add_row("Offline Mode", offline_status)
    table.add_row("Cache TTL", f"{stats['cache_ttl_minutes']} minutes")
    table.add_row("Rate Limit Delay", f"{stats['rate_limit_delay']}s between requests")
    table.add_row("", "")
    table.add_row("Total Cached Stocks", str(stats["total_cached"]))
    table.add_row("Fresh (within TTL)", f"[green]{stats['fresh']}[/]")
    table.add_row("Stale (expired)", f"[yellow]{stats['stale']}[/]")

    console.print()
    console.print(table)
    console.print()


@app.command("clear")
def cache_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Clear all cached stock data."""
    stats = get_cache_stats()

    if stats["total_cached"] == 0:
        console.print("[yellow]Cache is already empty.[/]")
        return

    if not force:
        confirm = typer.confirm(f"Clear {stats['total_cached']} cached stocks?")
        if not confirm:
            console.print("Cancelled.")
            return

    count = clear_cache()
    console.print(f"[green]Cleared {count} cached stocks.[/]")


@app.command("ttl")
def cache_ttl(
    minutes: int = typer.Argument(..., help="Cache TTL in minutes (e.g., 30, 60)"),
) -> None:
    """Set cache TTL (time-to-live) in minutes."""
    if minutes < 1:
        console.print("[red]TTL must be at least 1 minute.[/]")
        raise typer.Exit(1)

    set_cache_ttl(minutes)
    console.print(f"[green]Cache TTL set to {minutes} minutes.[/]")


@app.command("delay")
def cache_delay(
    seconds: float = typer.Argument(..., help="Delay between API requests in seconds (e.g., 0.5, 1.0)"),
) -> None:
    """Set rate limit delay between API requests."""
    if seconds < 0:
        console.print("[red]Delay cannot be negative.[/]")
        raise typer.Exit(1)

    set_rate_limit_delay(seconds)
    console.print(f"[green]Rate limit delay set to {seconds}s.[/]")


@app.command("enable")
def cache_enable() -> None:
    """Enable caching."""
    set_cache_enabled(True)
    console.print("[green]Caching enabled.[/]")


@app.command("disable")
def cache_disable() -> None:
    """Disable caching (always fetch fresh data)."""
    set_cache_enabled(False)
    console.print("[yellow]Caching disabled. All data will be fetched fresh.[/]")
    console.print("[dim]Note: This may cause rate limiting issues with large universes.[/]")


@app.command("offline")
def cache_offline() -> None:
    """Enable offline mode (only load from DB, no API calls)."""
    set_offline_mode(True)
    console.print("[green]Offline mode enabled.[/]")
    console.print("[dim]All data will be loaded from the local database only.[/]")
    console.print("[dim]Stocks not in cache will return no data.[/]")


@app.command("online")
def cache_online() -> None:
    """Disable offline mode (allow API calls for missing/stale data)."""
    set_offline_mode(False)
    console.print("[green]Online mode enabled.[/]")
    console.print("[dim]Missing or stale data will be fetched from the API.[/]")


@app.command("prefetch")
def cache_prefetch(
    universe: Optional[str] = typer.Argument(
        None,
        help="Universe to prefetch (sp500, nasdaq100, etc.) or 'all' for everything",
    ),
    skip_cached: bool = typer.Option(
        True, "--skip-cached/--refresh",
        help="Skip already cached stocks (default) or refresh all",
    ),
    delay: Optional[float] = typer.Option(
        None, "--delay", "-d",
        help="Override rate limit delay (seconds). Use 5-10 for large batches to avoid rate limits.",
    ),
) -> None:
    """
    Pre-fetch and cache stock data for faster screening.

    Yahoo Finance limits: ~360 requests/hour. For large prefetches, use --delay 5 or higher.

    Examples:
        tradfi cache prefetch dow30             # Small, uses default delay
        tradfi cache prefetch sp500 --delay 5   # Safer for 500 stocks
        tradfi cache prefetch all --delay 10    # Safest for all 1241 stocks
    """
    from tradfi.core.data import fetch_stock_from_api

    # Determine which universes to fetch
    if universe is None:
        # Show available options
        console.print()
        console.print("[bold]Available universes to prefetch:[/]")
        console.print()

        all_tickers = set()
        for name in AVAILABLE_UNIVERSES.keys():
            try:
                tickers = load_tickers(name)
                all_tickers.update(tickers)
                console.print(f"  [cyan]{name:15}[/] {len(tickers):4} stocks")
            except:
                pass

        console.print()
        console.print(f"  [bold green]{'all':15}[/] {len(all_tickers):4} unique stocks (all universes)")
        console.print()
        console.print("[dim]Usage: tradfi cache prefetch <universe>[/]")
        console.print("[dim]Example: tradfi cache prefetch sp500[/]")
        return

    # Collect tickers to fetch
    if universe.lower() == "all":
        tickers_to_fetch = set()
        for name in AVAILABLE_UNIVERSES.keys():
            try:
                tickers = load_tickers(name)
                tickers_to_fetch.update(tickers)
            except:
                pass
        tickers_to_fetch = sorted(tickers_to_fetch)
        console.print(f"[bold]Prefetching all universes ({len(tickers_to_fetch)} unique stocks)[/]")
    else:
        try:
            tickers_to_fetch = load_tickers(universe)
            console.print(f"[bold]Prefetching {universe} ({len(tickers_to_fetch)} stocks)[/]")
        except FileNotFoundError:
            console.print(f"[red]Unknown universe: {universe}[/]")
            console.print(f"[dim]Available: {', '.join(AVAILABLE_UNIVERSES.keys())}, all[/]")
            raise typer.Exit(1)

    # Skip already cached if requested
    if skip_cached:
        original_count = len(tickers_to_fetch)
        tickers_to_fetch = [t for t in tickers_to_fetch if get_cached_stock_data(t) is None]
        skipped = original_count - len(tickers_to_fetch)
        if skipped > 0:
            console.print(f"[dim]Skipping {skipped} already cached stocks[/]")

    if not tickers_to_fetch:
        console.print("[green]All stocks already cached![/]")
        return

    # Apply delay override if specified
    config = get_config()
    effective_delay = delay if delay is not None else config.rate_limit_delay

    # Warn about rate limits for large batches
    if len(tickers_to_fetch) > 100 and effective_delay < 5:
        console.print(f"[yellow]Warning: {len(tickers_to_fetch)} stocks with {effective_delay}s delay may hit rate limits.[/]")
        console.print(f"[yellow]Consider using: tradfi cache prefetch {universe} --delay 5[/]")
        console.print()

    # Temporarily set the delay if overridden
    if delay is not None:
        original_delay = config.rate_limit_delay
        set_rate_limit_delay(delay)

    # Estimate time
    est_time = len(tickers_to_fetch) * (effective_delay + 0.8)
    console.print(f"[dim]Estimated time: {est_time/60:.0f} minutes (delay: {effective_delay}s)[/]")
    console.print()

    # Fetch with progress
    fetched = 0
    failed = 0
    failed_tickers = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Prefetching...", total=len(tickers_to_fetch))

        for ticker in tickers_to_fetch:
            progress.update(task, description=f"Fetching {ticker}...")

            # Fetch from yfinance API and save to cache
            stock = fetch_stock_from_api(ticker)
            if stock:
                fetched += 1
            else:
                failed += 1
                failed_tickers.append(ticker)

            progress.advance(task)

    # Restore original delay if we overrode it
    if delay is not None:
        set_rate_limit_delay(original_delay)

    # Summary
    console.print()
    console.print(f"[green]Prefetched {fetched} stocks[/]")
    if failed > 0:
        console.print(f"[yellow]Failed: {failed} stocks[/]")
        if len(failed_tickers) <= 10:
            console.print(f"[dim]  {', '.join(failed_tickers)}[/]")

    stats = get_cache_stats()
    console.print()
    console.print(f"[dim]Cache now has {stats['total_cached']} stocks[/]")
