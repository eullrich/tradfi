"""Cache management commands - status, clear, and refresh via remote API."""

from datetime import datetime
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from tradfi.core.screener import AVAILABLE_UNIVERSES
from tradfi.utils.provider import get_provider as _get_provider

console = Console()


app = typer.Typer(
    name="cache",
    help="Manage server cache (all operations go to remote API).",
    add_completion=False,
)


@app.command("status")
def cache_status() -> None:
    """
    Show cache statistics from the remote server.

    Example:
        tradfi cache status
    """
    provider = _get_provider()
    stats = provider.get_cache_stats()

    if not stats:
        console.print("[red]Could not fetch cache stats from server.[/]")
        console.print(f"[dim]API URL: {provider.api_url}[/]")
        return

    console.print()
    console.print("[bold]Server Cache Status[/]")
    console.print()

    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Total cached", str(stats.get("total_cached", 0)))
    table.add_row("Fresh", f"[green]{stats.get('fresh', 0)}[/]")
    table.add_row("Stale", f"[yellow]{stats.get('stale', 0)}[/]")
    table.add_row("TTL", f"{stats.get('cache_ttl_minutes', 0)} minutes")

    if stats.get("last_updated"):
        last_updated_display = stats.get("last_updated_ago")
        if not last_updated_display:
            # Convert timestamp to readable format
            ts = stats.get("last_updated")
            last_updated_display = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row("Last updated", last_updated_display)

    console.print(table)
    console.print()


@app.command("clear")
def cache_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Clear all cached stock data on the server.

    Example:
        tradfi cache clear
        tradfi cache clear --force
    """
    if not force:
        console.print("[yellow]This will clear ALL cached stock data on the server.[/]")
        if not typer.confirm("Continue?"):
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(0)

    provider = _get_provider()
    count = provider.clear_cache()

    if count > 0:
        console.print(f"[green]Cleared {count} cached entries on server[/]")
    else:
        console.print("[yellow]Cache cleared (or was already empty)[/]")


@app.command("refresh")
def cache_refresh(
    universe: Optional[str] = typer.Argument(
        None,
        help="Universe to refresh (sp500, dow30, etc.) or omit to see options",
    ),
) -> None:
    """
    Trigger a server-side refresh for a universe.

    This tells the server to re-fetch stock data from Yahoo Finance.

    Examples:
        tradfi cache refresh           # Show available universes
        tradfi cache refresh dow30     # Refresh Dow 30
        tradfi cache refresh sp500     # Refresh S&P 500
    """
    provider = _get_provider()

    if universe is None:
        # Show available universes
        console.print()
        console.print("[bold]Available universes to refresh:[/]")
        console.print()

        for name, description in AVAILABLE_UNIVERSES.items():
            console.print(f"  [cyan]{name:15}[/] {description}")

        console.print()
        console.print("[dim]Usage: tradfi cache refresh <universe>[/]")
        console.print("[dim]Example: tradfi cache refresh dow30[/]")
        return

    if universe.lower() not in AVAILABLE_UNIVERSES:
        console.print(f"[red]Unknown universe: {universe}[/]")
        console.print(f"[dim]Available: {', '.join(AVAILABLE_UNIVERSES.keys())}[/]")
        raise typer.Exit(1)

    console.print(f"[dim]Triggering refresh for {universe}...[/]")

    result = provider.trigger_refresh(universe.lower())

    if "error" in result:
        console.print(f"[red]Failed to trigger refresh: {result['error']}[/]")
    else:
        console.print(f"[green]Refresh triggered for {universe}[/]")
        if result.get("message"):
            console.print(f"[dim]{result['message']}[/]")
