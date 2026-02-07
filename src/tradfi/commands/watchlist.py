"""Watchlist command - manage stock watchlist."""

import os

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from tradfi.core.remote_provider import RemoteDataProvider
from tradfi.utils.display import format_number, format_pct, get_signal_display

console = Console()

# Default API URL - can be overridden with TRADFI_API_URL env var
DEFAULT_API_URL = "https://deepv-production.up.railway.app"


def _get_provider() -> RemoteDataProvider:
    """Get the remote data provider using API URL and admin key from environment."""
    api_url = os.environ.get("TRADFI_API_URL", DEFAULT_API_URL)
    admin_key = os.environ.get("TRADFI_ADMIN_KEY")
    return RemoteDataProvider(api_url, admin_key=admin_key)


# Create a Typer app for watchlist subcommands
app = typer.Typer(help="Manage your stock watchlist")


@app.command("add")
def watchlist_add(
    tickers: list[str] = typer.Argument(..., help="Ticker symbol(s) to add"),
) -> None:
    """Add stock(s) to your watchlist."""
    provider = _get_provider()
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if provider.add_to_watchlist(ticker):
            console.print(f"[green]Added {ticker} to watchlist[/]")
        else:
            console.print(f"[yellow]{ticker} may already be in watchlist[/]")


@app.command("remove")
def watchlist_remove(
    tickers: list[str] = typer.Argument(..., help="Ticker symbol(s) to remove"),
) -> None:
    """Remove stock(s) from your watchlist."""
    provider = _get_provider()
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if provider.remove_from_watchlist(ticker):
            console.print(f"[green]Removed {ticker} from watchlist[/]")
        else:
            console.print(f"[yellow]{ticker} was not in watchlist[/]")


@app.command("show")
def watchlist_show(
    fetch_data: bool = typer.Option(
        True, "--fetch/--no-fetch", help="Fetch current data for stocks"
    ),
) -> None:
    """Show your watchlist with current metrics."""
    provider = _get_provider()
    watchlist = provider.get_watchlist()

    if not watchlist:
        console.print(
            "[dim]Your watchlist is empty. Use 'tradfi watchlist add <ticker>' to add stocks.[/]"
        )
        return

    console.print()

    if fetch_data:
        # Fetch current data and display rich table
        table = Table(
            title=f"Watchlist ({len(watchlist)} stocks)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold",
        )

        table.add_column("Ticker", style="bold cyan")
        table.add_column("Price", justify="right")
        table.add_column("P/E", justify="right")
        table.add_column("RSI", justify="right")
        table.add_column("vs 52W Low", justify="right")
        table.add_column("MoS", justify="right")
        table.add_column("Signal", justify="center")
        table.add_column("Notes", max_width=20)

        for item in watchlist:
            ticker = item.get("ticker", "")
            if not ticker:
                continue
            notes = item.get("notes") or ""

            with console.status(f"[dim]Fetching {ticker}...[/]"):
                stock = provider.fetch_stock(ticker)

            if stock:
                price = f"${stock.current_price:.2f}" if stock.current_price else "N/A"
                pe = format_number(stock.valuation.pe_trailing, 1)
                rsi = format_number(stock.technical.rsi_14, 0)
                vs_low = format_pct(stock.technical.pct_from_52w_low)
                mos = format_pct(stock.fair_value.margin_of_safety_pct)
                signal = get_signal_display(stock.signal)

                # Color RSI
                rsi_val = stock.technical.rsi_14
                if rsi_val is not None and rsi_val < 30:
                    rsi = f"[green]{rsi}[/]"
                elif rsi_val is not None and rsi_val < 40:
                    rsi = f"[yellow]{rsi}[/]"

                table.add_row(
                    ticker, price, pe, rsi, vs_low, mos, signal, notes[:20] if notes else ""
                )
            else:
                table.add_row(
                    ticker, "[red]Error[/]", "", "", "", "", "", notes[:20] if notes else ""
                )

        console.print(table)
    else:
        # Simple list without fetching
        table = Table(
            title=f"Watchlist ({len(watchlist)} stocks)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold",
        )

        table.add_column("Ticker", style="bold cyan")
        table.add_column("Notes")

        for item in watchlist:
            ticker = item.get("ticker", "")
            if not ticker:
                continue
            notes = item.get("notes") or ""
            table.add_row(ticker, notes)

        console.print(table)

    console.print()


@app.command("note")
def watchlist_note(
    ticker: str = typer.Argument(..., help="Ticker symbol"),
    notes: str = typer.Argument(..., help="Notes to add"),
) -> None:
    """Add or update notes for a watchlist stock."""
    provider = _get_provider()
    ticker = ticker.upper().strip()
    if provider.update_watchlist_notes(ticker, notes):
        console.print(f"[green]Updated notes for {ticker}[/]")
    else:
        console.print(f"[yellow]{ticker} is not in your watchlist[/]")
