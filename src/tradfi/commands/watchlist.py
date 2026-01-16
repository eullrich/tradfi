"""Watchlist command - manage stock watchlist with alerts."""

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from tradfi.core.data import fetch_stock
from tradfi.utils.cache import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    update_watchlist_notes,
    add_alert,
    get_alerts,
    remove_alert,
)
from tradfi.utils.display import format_number, format_pct, get_signal_display

console = Console()

# Create a Typer app for watchlist subcommands
app = typer.Typer(help="Manage your stock watchlist")


@app.command("add")
def watchlist_add(
    tickers: list[str] = typer.Argument(..., help="Ticker symbol(s) to add"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Notes for this stock"),
) -> None:
    """Add stock(s) to your watchlist."""
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if add_to_watchlist(ticker, notes):
            console.print(f"[green]Added {ticker} to watchlist[/]")
        else:
            console.print(f"[yellow]{ticker} is already in watchlist[/]")


@app.command("remove")
def watchlist_remove(
    tickers: list[str] = typer.Argument(..., help="Ticker symbol(s) to remove"),
) -> None:
    """Remove stock(s) from your watchlist."""
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if remove_from_watchlist(ticker):
            console.print(f"[green]Removed {ticker} from watchlist[/]")
        else:
            console.print(f"[yellow]{ticker} was not in watchlist[/]")


@app.command("show")
def watchlist_show(
    fetch_data: bool = typer.Option(True, "--fetch/--no-fetch", help="Fetch current data for stocks"),
) -> None:
    """Show your watchlist with current metrics."""
    watchlist = get_watchlist()

    if not watchlist:
        console.print("[dim]Your watchlist is empty. Use 'tradfi watchlist add <ticker>' to add stocks.[/]")
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
            ticker = item["ticker"]
            notes = item.get("notes") or ""

            with console.status(f"[dim]Fetching {ticker}...[/]"):
                stock = fetch_stock(ticker)

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

                table.add_row(ticker, price, pe, rsi, vs_low, mos, signal, notes[:20] if notes else "")
            else:
                table.add_row(ticker, "[red]Error[/]", "", "", "", "", "", notes[:20] if notes else "")

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
        table.add_column("Added")
        table.add_column("Notes")

        for item in watchlist:
            added = datetime.fromtimestamp(item["added_at"]).strftime("%Y-%m-%d")
            notes = item.get("notes") or ""
            table.add_row(item["ticker"], added, notes)

        console.print(table)

    console.print()


@app.command("note")
def watchlist_note(
    ticker: str = typer.Argument(..., help="Ticker symbol"),
    notes: str = typer.Argument(..., help="Notes to add"),
) -> None:
    """Add or update notes for a watchlist stock."""
    ticker = ticker.upper().strip()
    if update_watchlist_notes(ticker, notes):
        console.print(f"[green]Updated notes for {ticker}[/]")
    else:
        console.print(f"[yellow]{ticker} is not in your watchlist[/]")


@app.command("alert")
def watchlist_alert(
    ticker: str = typer.Argument(..., help="Ticker symbol"),
    price_below: Optional[float] = typer.Option(None, "--below", "-b", help="Alert when price falls below"),
    price_above: Optional[float] = typer.Option(None, "--above", "-a", help="Alert when price rises above"),
    rsi_below: Optional[float] = typer.Option(None, "--rsi-below", help="Alert when RSI falls below"),
    pe_below: Optional[float] = typer.Option(None, "--pe-below", help="Alert when P/E falls below"),
) -> None:
    """Set price or metric alerts for a stock."""
    ticker = ticker.upper().strip()

    if not any([price_below, price_above, rsi_below, pe_below]):
        console.print("[yellow]Please specify at least one alert condition[/]")
        console.print("[dim]Examples: --below 150, --rsi-below 30, --pe-below 15[/]")
        return

    alerts_added = 0

    if price_below is not None:
        add_alert(ticker, "price_below", price_below)
        console.print(f"[green]Alert set: {ticker} price below ${price_below:.2f}[/]")
        alerts_added += 1

    if price_above is not None:
        add_alert(ticker, "price_above", price_above)
        console.print(f"[green]Alert set: {ticker} price above ${price_above:.2f}[/]")
        alerts_added += 1

    if rsi_below is not None:
        add_alert(ticker, "rsi_below", rsi_below)
        console.print(f"[green]Alert set: {ticker} RSI below {rsi_below:.0f}[/]")
        alerts_added += 1

    if pe_below is not None:
        add_alert(ticker, "pe_below", pe_below)
        console.print(f"[green]Alert set: {ticker} P/E below {pe_below:.1f}[/]")
        alerts_added += 1


@app.command("alerts")
def watchlist_alerts(
    ticker: Optional[str] = typer.Argument(None, help="Filter alerts by ticker"),
) -> None:
    """Show all active alerts."""
    alerts = get_alerts(ticker.upper() if ticker else None)

    if not alerts:
        if ticker:
            console.print(f"[dim]No alerts set for {ticker.upper()}[/]")
        else:
            console.print("[dim]No alerts set. Use 'tradfi watchlist alert <ticker> --below <price>' to set alerts.[/]")
        return

    console.print()

    table = Table(
        title="Active Alerts",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("ID", style="dim")
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Condition")
    table.add_column("Threshold", justify="right")

    for alert in alerts:
        alert_type = alert["alert_type"]
        threshold = alert["threshold"]

        if alert_type == "price_below":
            condition = "Price below"
            threshold_str = f"${threshold:.2f}"
        elif alert_type == "price_above":
            condition = "Price above"
            threshold_str = f"${threshold:.2f}"
        elif alert_type == "rsi_below":
            condition = "RSI below"
            threshold_str = f"{threshold:.0f}"
        elif alert_type == "pe_below":
            condition = "P/E below"
            threshold_str = f"{threshold:.1f}"
        else:
            condition = alert_type
            threshold_str = str(threshold)

        table.add_row(str(alert["id"]), alert["ticker"], condition, threshold_str)

    console.print(table)
    console.print()


@app.command("remove-alert")
def watchlist_remove_alert(
    alert_id: int = typer.Argument(..., help="Alert ID to remove"),
) -> None:
    """Remove an alert by ID."""
    if remove_alert(alert_id):
        console.print(f"[green]Removed alert {alert_id}[/]")
    else:
        console.print(f"[yellow]Alert {alert_id} not found[/]")


@app.command("check")
def watchlist_check() -> None:
    """Check watchlist stocks against their alerts."""
    watchlist = get_watchlist()

    if not watchlist:
        console.print("[dim]Your watchlist is empty.[/]")
        return

    alerts = get_alerts()
    if not alerts:
        console.print("[dim]No alerts set.[/]")
        return

    # Group alerts by ticker
    alerts_by_ticker: dict[str, list[dict]] = {}
    for alert in alerts:
        ticker = alert["ticker"]
        if ticker not in alerts_by_ticker:
            alerts_by_ticker[ticker] = []
        alerts_by_ticker[ticker].append(alert)

    console.print()
    console.print("[bold]Checking alerts...[/]")
    console.print()

    triggered = []

    for ticker, ticker_alerts in alerts_by_ticker.items():
        with console.status(f"[dim]Checking {ticker}...[/]"):
            stock = fetch_stock(ticker)

        if stock is None:
            console.print(f"[yellow]Could not fetch {ticker}[/]")
            continue

        for alert in ticker_alerts:
            alert_type = alert["alert_type"]
            threshold = alert["threshold"]
            is_triggered = False

            if alert_type == "price_below" and stock.current_price is not None:
                if stock.current_price < threshold:
                    is_triggered = True
                    triggered.append(
                        f"[green]{ticker}[/] price ${stock.current_price:.2f} is below ${threshold:.2f}"
                    )

            elif alert_type == "price_above" and stock.current_price is not None:
                if stock.current_price > threshold:
                    is_triggered = True
                    triggered.append(
                        f"[green]{ticker}[/] price ${stock.current_price:.2f} is above ${threshold:.2f}"
                    )

            elif alert_type == "rsi_below" and stock.technical.rsi_14 is not None:
                if stock.technical.rsi_14 < threshold:
                    is_triggered = True
                    triggered.append(
                        f"[green]{ticker}[/] RSI {stock.technical.rsi_14:.0f} is below {threshold:.0f}"
                    )

            elif alert_type == "pe_below" and stock.valuation.pe_trailing is not None:
                if stock.valuation.pe_trailing < threshold:
                    is_triggered = True
                    triggered.append(
                        f"[green]{ticker}[/] P/E {stock.valuation.pe_trailing:.1f} is below {threshold:.1f}"
                    )

    if triggered:
        console.print("[bold yellow]TRIGGERED ALERTS:[/]")
        for msg in triggered:
            console.print(f"  {msg}")
    else:
        console.print("[dim]No alerts triggered.[/]")

    console.print()
