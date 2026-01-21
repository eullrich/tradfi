"""List management commands - view, manage, and export saved stock lists."""

import os
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from tradfi.core.remote_provider import RemoteDataProvider

console = Console()

# Reserved list names for long/short positions
LONG_LIST = "_long"
SHORT_LIST = "_short"

# Default API URL - can be overridden with TRADFI_API_URL env var
DEFAULT_API_URL = "https://deepv-production.up.railway.app"


def _get_provider() -> RemoteDataProvider:
    """Get the remote data provider using API URL from environment."""
    api_url = os.environ.get("TRADFI_API_URL", DEFAULT_API_URL)
    return RemoteDataProvider(api_url)


app = typer.Typer(
    name="list",
    help="Manage saved stock lists.",
    add_completion=False,
)


@app.command("ls")
def list_lists() -> None:
    """
    Show all saved lists.

    Example:
        tradfi list ls
    """
    provider = _get_provider()
    lists = provider.get_lists()

    if not lists:
        console.print("[yellow]No saved lists found.[/]")
        console.print("[dim]Create one with: tradfi list create my-list AAPL,MSFT[/]")
        return

    table = Table(
        title="Saved Lists",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("Name", style="bold cyan")
    table.add_column("Stocks", justify="right")

    for name in lists:
        list_data = provider.get_list(name)
        count = len(list_data.get("tickers", [])) if list_data else 0
        table.add_row(name, str(count))

    console.print(table)
    console.print()
    console.print("[dim]View a list: tradfi list show <name>[/]")


@app.command("show")
def show_list(
    name: str = typer.Argument(..., help="Name of the list to show"),
    export: bool = typer.Option(False, "--export", "-e", help="Export as comma-separated tickers"),
) -> None:
    """
    Show tickers in a saved list.

    Examples:
        tradfi list show my-value-picks
        tradfi list show my-value-picks --export
    """
    provider = _get_provider()
    list_data = provider.get_list(name)

    if list_data is None:
        console.print(f"[red]List '{name}' not found.[/]")
        console.print("[dim]See available lists: tradfi list ls[/]")
        raise typer.Exit(1)

    tickers = list_data.get("tickers", [])

    if export:
        # Export as comma-separated for easy copy/paste
        console.print(",".join(tickers))
        return

    console.print(f"\n[bold cyan]{name}[/] ({len(tickers)} stocks)\n")

    # Display in columns
    cols = 5
    for i in range(0, len(tickers), cols):
        row = tickers[i:i+cols]
        console.print("  ".join(f"[cyan]{t:6}[/]" for t in row))

    console.print()
    console.print("[dim]Commands:[/]")
    console.print(f"[dim]  Export tickers:   tradfi list show {name} --export[/]")
    console.print(f"[dim]  Delete list:      tradfi list delete {name}[/]")


@app.command("delete")
def delete_list_cmd(
    name: str = typer.Argument(..., help="Name of the list to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Delete a saved list.

    Example:
        tradfi list delete my-old-picks
        tradfi list delete my-old-picks --force
    """
    provider = _get_provider()
    list_data = provider.get_list(name)

    if list_data is None:
        console.print(f"[red]List '{name}' not found.[/]")
        raise typer.Exit(1)

    tickers = list_data.get("tickers", [])

    if not force:
        console.print(f"Delete list '{name}' with {len(tickers)} stocks?")
        if not typer.confirm("Continue?"):
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(0)

    if provider.delete_list(name):
        console.print(f"[green]Deleted list '{name}'[/]")
    else:
        console.print(f"[red]Failed to delete list '{name}'[/]")


@app.command("create")
def create_list_cmd(
    name: str = typer.Argument(..., help="Name for the new list"),
    tickers: str = typer.Argument(..., help="Comma-separated list of tickers"),
) -> None:
    """
    Create a new list from tickers.

    Example:
        tradfi list create tech-picks AAPL,MSFT,GOOGL,NVDA
    """
    provider = _get_provider()
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    if not ticker_list:
        console.print("[red]No valid tickers provided.[/]")
        raise typer.Exit(1)

    if provider.create_list(name, ticker_list):
        console.print(f"[green]Created list '{name}' with {len(ticker_list)} stocks[/]")
    else:
        console.print(f"[red]Failed to create list '{name}'[/]")


@app.command("add")
def add_ticker(
    name: str = typer.Argument(..., help="Name of the list"),
    ticker: str = typer.Argument(..., help="Ticker to add"),
) -> None:
    """
    Add a ticker to an existing list.

    Example:
        tradfi list add my-picks AAPL
    """
    provider = _get_provider()
    ticker = ticker.upper()

    if provider.add_to_list(name, ticker):
        console.print(f"[green]Added {ticker} to '{name}'[/]")
    else:
        # Check if list exists
        if provider.get_list(name) is None:
            console.print(f"[red]List '{name}' not found.[/]")
        else:
            console.print(f"[yellow]{ticker} is already in '{name}'[/]")


@app.command("remove")
def remove_ticker(
    name: str = typer.Argument(..., help="Name of the list"),
    ticker: str = typer.Argument(..., help="Ticker to remove"),
) -> None:
    """
    Remove a ticker from a list.

    Example:
        tradfi list remove my-picks AAPL
    """
    provider = _get_provider()
    ticker = ticker.upper()

    if provider.remove_from_list(name, ticker):
        console.print(f"[green]Removed {ticker} from '{name}'[/]")
    else:
        console.print(f"[yellow]{ticker} not found in '{name}'[/]")


# ============================================================================
# Long List Commands - for stocks you want to go long on
# ============================================================================

@app.command("long")
def long_list(
    ticker: Optional[str] = typer.Argument(None, help="Ticker to add to long list (omit to view list)"),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove ticker from long list"),
    clear: bool = typer.Option(False, "--clear", help="Clear all tickers from long list"),
) -> None:
    """
    Manage your long list (stocks to buy).

    Examples:
        tradfi list long              # View long list
        tradfi list long AAPL         # Add AAPL to long list
        tradfi list long AAPL -r      # Remove AAPL from long list
        tradfi list long --clear      # Clear entire long list
    """
    provider = _get_provider()

    # Ensure the list exists
    if provider.get_list(LONG_LIST) is None:
        provider.create_list(LONG_LIST, [])

    if clear:
        provider.delete_list(LONG_LIST)
        provider.create_list(LONG_LIST, [])
        console.print("[green]Long list cleared[/]")
        return

    if ticker:
        ticker = ticker.upper()
        if remove:
            if provider.remove_from_list(LONG_LIST, ticker):
                console.print(f"[green]Removed {ticker} from long list[/]")
            else:
                console.print(f"[yellow]{ticker} not in long list[/]")
        else:
            if provider.add_to_list(LONG_LIST, ticker):
                console.print(f"[green]Added {ticker} to long list[/]")
            else:
                console.print(f"[yellow]{ticker} already in long list[/]")
        return

    # View the list
    list_data = provider.get_list(LONG_LIST)
    tickers = list_data.get("tickers", []) if list_data else []
    _display_position_list(provider, "Long List", tickers, "green", "buy")


# ============================================================================
# Short List Commands - for stocks you want to short
# ============================================================================

@app.command("short")
def short_list(
    ticker: Optional[str] = typer.Argument(None, help="Ticker to add to short list (omit to view list)"),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove ticker from short list"),
    clear: bool = typer.Option(False, "--clear", help="Clear all tickers from short list"),
) -> None:
    """
    Manage your short list (stocks to short/sell).

    Examples:
        tradfi list short             # View short list
        tradfi list short TSLA        # Add TSLA to short list
        tradfi list short TSLA -r     # Remove TSLA from short list
        tradfi list short --clear     # Clear entire short list
    """
    provider = _get_provider()

    # Ensure the list exists
    if provider.get_list(SHORT_LIST) is None:
        provider.create_list(SHORT_LIST, [])

    if clear:
        provider.delete_list(SHORT_LIST)
        provider.create_list(SHORT_LIST, [])
        console.print("[red]Short list cleared[/]")
        return

    if ticker:
        ticker = ticker.upper()
        if remove:
            if provider.remove_from_list(SHORT_LIST, ticker):
                console.print(f"[red]Removed {ticker} from short list[/]")
            else:
                console.print(f"[yellow]{ticker} not in short list[/]")
        else:
            if provider.add_to_list(SHORT_LIST, ticker):
                console.print(f"[red]Added {ticker} to short list[/]")
            else:
                console.print(f"[yellow]{ticker} already in short list[/]")
        return

    # View the list
    list_data = provider.get_list(SHORT_LIST)
    tickers = list_data.get("tickers", []) if list_data else []
    _display_position_list(provider, "Short List", tickers, "red", "short")


def _display_position_list(provider: RemoteDataProvider, title: str, tickers: list[str], color: str, action: str) -> None:
    """Display a long or short position list with current prices."""
    if not tickers:
        console.print(f"[yellow]Your {title.lower()} is empty.[/]")
        console.print(f"[dim]Add stocks with: tradfi list {'long' if action == 'buy' else 'short'} <TICKER>[/]")
        return

    console.print(f"\n[bold {color}]{title}[/] ({len(tickers)} stocks)\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("Ticker", style=f"bold {color}")
    table.add_column("Price", justify="right")
    table.add_column("P/E", justify="right")
    table.add_column("52WH", justify="right")
    table.add_column("RSI", justify="right")

    for ticker in tickers:
        stock = provider.fetch_stock(ticker)
        if stock:
            price = f"${stock.current_price:.2f}" if stock.current_price else "-"
            pe = f"{stock.valuation.pe_trailing:.1f}" if stock.valuation.pe_trailing and isinstance(stock.valuation.pe_trailing, (int, float)) else "-"
            pct_52wh = stock.technical.pct_from_52w_high
            high_52 = f"{pct_52wh:.0f}%" if pct_52wh else "-"
            rsi = f"{stock.technical.rsi_14:.0f}" if stock.technical.rsi_14 else "-"
            table.add_row(ticker, price, pe, high_52, rsi)
        else:
            table.add_row(ticker, "-", "-", "-", "-")

    console.print(table)
    console.print()
    console.print(f"[dim]Remove: tradfi list {'long' if action == 'buy' else 'short'} <TICKER> -r[/]")
    console.print(f"[dim]Export: tradfi list show {'_long' if action == 'buy' else '_short'} -e[/]")


# ============================================================================
# Category Commands - organize lists into categories
# ============================================================================

category_app = typer.Typer(
    name="category",
    help="Manage list categories.",
    add_completion=False,
)
app.add_typer(category_app, name="category")


@category_app.command("create")
def category_create(
    name: str = typer.Argument(..., help="Category name"),
    icon: Optional[str] = typer.Option(None, "--icon", "-i", help="Icon/emoji for the category"),
) -> None:
    """
    Create a new category for organizing lists.

    Examples:
        tradfi list category create "Value Picks"
        tradfi list category create "Tech" --icon "💻"
    """
    provider = _get_provider()
    if provider.create_category(name, icon=icon):
        icon_str = f" {icon}" if icon else ""
        console.print(f"[green]Created category '{name}'{icon_str}[/]")
    else:
        console.print(f"[red]Failed to create category (may already exist)[/]")


@category_app.command("ls")
def category_list() -> None:
    """
    List all categories.

    Example:
        tradfi list category ls
    """
    provider = _get_provider()
    categories = provider.get_categories()

    if not categories:
        console.print("[yellow]No categories found.[/]")
        console.print("[dim]Create one with: tradfi list category create \"My Category\"[/]")
        return

    table = Table(
        title="List Categories",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("ID", justify="right", style="dim")
    table.add_column("Name", style="bold cyan")
    table.add_column("Icon")

    for cat in categories:
        table.add_row(
            str(cat.get("id", "-")),
            cat.get("name", "-"),
            cat.get("icon") or "-",
        )

    console.print(table)


@category_app.command("delete")
def category_delete(
    category_id: int = typer.Argument(..., help="Category ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Delete a category by ID.

    Example:
        tradfi list category delete 1
    """
    if not force:
        if not typer.confirm(f"Delete category {category_id}?"):
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(0)

    provider = _get_provider()
    if provider.delete_category(category_id):
        console.print(f"[green]Deleted category {category_id}[/]")
    else:
        console.print(f"[red]Category {category_id} not found[/]")


@app.command("move")
def move_list(
    list_name: str = typer.Argument(..., help="Name of the list to move"),
    category_id: int = typer.Argument(..., help="Target category ID"),
) -> None:
    """
    Move a list to a category.

    Example:
        tradfi list move my-picks 1
    """
    provider = _get_provider()

    # Check list exists
    if provider.get_list(list_name) is None:
        console.print(f"[red]List '{list_name}' not found.[/]")
        raise typer.Exit(1)

    if provider.add_list_to_category(list_name, category_id):
        console.print(f"[green]Moved '{list_name}' to category {category_id}[/]")
    else:
        console.print(f"[yellow]Failed to move '{list_name}' to category {category_id}[/]")


@app.command("unmove")
def unmove_list(
    list_name: str = typer.Argument(..., help="Name of the list to remove from category"),
    category_id: int = typer.Argument(..., help="Category ID to remove from"),
) -> None:
    """
    Remove a list from a category.

    Example:
        tradfi list unmove my-picks 1
    """
    provider = _get_provider()

    if provider.remove_list_from_category(list_name, category_id):
        console.print(f"[green]Removed '{list_name}' from category {category_id}[/]")
    else:
        console.print(f"[yellow]'{list_name}' was not in category {category_id}[/]")


# ============================================================================
# Enhanced Notes Commands
# ============================================================================

@app.command("note")
def note_ticker(
    list_name: str = typer.Argument(..., help="Name of the list"),
    ticker: str = typer.Argument(..., help="Ticker to add note to"),
    notes: Optional[str] = typer.Argument(None, help="Note text"),
    thesis: Optional[str] = typer.Option(None, "--thesis", "-t", help="Investment thesis"),
    entry: Optional[float] = typer.Option(None, "--entry", "-e", help="Entry price target"),
    target: Optional[float] = typer.Option(None, "--target", "-T", help="Target price"),
) -> None:
    """
    Add notes for a ticker in a list.

    Examples:
        tradfi list note my-picks AAPL "Strong moat, waiting for pullback"
        tradfi list note my-picks AAPL --thesis "Services growth play"
        tradfi list note my-picks AAPL --entry 165 --target 200
    """
    provider = _get_provider()
    ticker = ticker.upper()

    # Check list exists and has ticker
    list_data = provider.get_list(list_name)
    if list_data is None:
        console.print(f"[red]List '{list_name}' not found.[/]")
        raise typer.Exit(1)

    tickers = list_data.get("tickers", [])
    if ticker not in tickers:
        console.print(f"[yellow]{ticker} is not in list '{list_name}'[/]")
        console.print(f"[dim]Add it first: tradfi list add {list_name} {ticker}[/]")
        raise typer.Exit(1)

    # Set/update note
    if provider.set_item_note(
        list_name,
        ticker,
        notes=notes,
        thesis=thesis,
        entry_price=entry,
        target_price=target,
    ):
        console.print(f"[green]Updated notes for {ticker} in '{list_name}'[/]")
    else:
        console.print(f"[red]Failed to update notes for {ticker}[/]")


# ============================================================================
# Position/Portfolio Commands
# ============================================================================

@app.command("position")
def set_position_cmd(
    list_name: str = typer.Argument(..., help="Name of the list"),
    ticker: str = typer.Argument(..., help="Ticker symbol"),
    shares: Optional[float] = typer.Option(None, "--shares", "-s", help="Number of shares"),
    entry: Optional[float] = typer.Option(None, "--entry", "-e", help="Entry price per share"),
    target: Optional[float] = typer.Option(None, "--target", "-T", help="Target price"),
    thesis: Optional[str] = typer.Option(None, "--thesis", "-t", help="Investment thesis"),
    clear: bool = typer.Option(False, "--clear", help="Clear position data"),
) -> None:
    """
    Set position data (shares and entry price) for a list item.

    This enables portfolio tracking with P&L calculations.

    Examples:
        tradfi list position my-picks AAPL --shares 100 --entry 150.50
        tradfi list position my-picks AAPL -s 100 -e 150.50 -T 200
        tradfi list position _long MSFT -s 50 -e 380
        tradfi list position my-picks AAPL --clear
    """
    provider = _get_provider()
    ticker = ticker.upper()

    # Check list and ticker exist
    list_data = provider.get_list(list_name)
    if list_data is None:
        console.print(f"[red]List '{list_name}' not found.[/]")
        raise typer.Exit(1)

    tickers = list_data.get("tickers", [])
    if ticker not in tickers:
        console.print(f"[yellow]{ticker} is not in list '{list_name}'[/]")
        console.print(f"[dim]Add it first: tradfi list add {list_name} {ticker}[/]")
        raise typer.Exit(1)

    if clear:
        if provider.clear_position(list_name, ticker):
            console.print(f"[green]Cleared position data for {ticker}[/]")
        else:
            console.print(f"[red]Failed to clear position data[/]")
        return

    if shares is None and entry is None and target is None and thesis is None:
        console.print("[yellow]Specify at least one of: --shares, --entry, --target, --thesis[/]")
        raise typer.Exit(1)

    if provider.set_position(list_name, ticker, shares=shares, entry_price=entry, target_price=target, thesis=thesis):
        parts = []
        if shares is not None:
            parts.append(f"{shares:.0f} shares")
        if entry is not None:
            parts.append(f"${entry:.2f} entry")
        if target is not None:
            parts.append(f"${target:.2f} target")
        console.print(f"[green]Set position for {ticker}: {', '.join(parts) if parts else 'updated'}[/]")
    else:
        console.print(f"[red]Failed to set position for {ticker}[/]")


@app.command("portfolio")
def show_portfolio(
    list_name: str = typer.Argument(..., help="Name of the list"),
    export: bool = typer.Option(False, "--export", "-e", help="Export as CSV"),
) -> None:
    """
    Show portfolio view with P&L for a list.

    Displays positions with gain/loss calculations and allocation percentages.

    Examples:
        tradfi list portfolio my-picks
        tradfi list portfolio _long
        tradfi list portfolio my-picks --export
    """
    provider = _get_provider()
    portfolio = provider.get_portfolio(list_name)

    if portfolio is None:
        console.print(f"[red]List '{list_name}' not found.[/]")
        raise typer.Exit(1)

    if portfolio.get("position_count", 0) == 0:
        console.print(f"[yellow]No positions in '{list_name}'[/]")
        console.print(f"[dim]Add positions with: tradfi list position {list_name} TICKER --shares 100 --entry 50[/]")
        return

    if export:
        _export_portfolio_csv(portfolio, list_name)
        return

    _display_portfolio_table(portfolio, list_name)


def _display_portfolio_table(portfolio: dict, list_name: str) -> None:
    """Display portfolio table with P&L."""
    table = Table(
        title=f"Portfolio: {list_name}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("Ticker", style="bold cyan")
    table.add_column("Shares", justify="right")
    table.add_column("Entry", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("P&L $", justify="right")
    table.add_column("P&L %", justify="right")
    table.add_column("Alloc", justify="right")

    for item in portfolio.get("items", []):
        pnl = item.get("gain_loss")
        pnl_pct = item.get("gain_loss_pct")
        pnl_color = "green" if pnl and pnl >= 0 else "red"
        shares = item.get("shares")
        entry_price = item.get("entry_price")
        current_price = item.get("current_price")
        cost_basis = item.get("cost_basis")
        current_value = item.get("current_value")
        allocation_pct = item.get("allocation_pct")

        table.add_row(
            item.get("ticker", "-"),
            f"{shares:.0f}" if shares is not None else "-",
            f"${entry_price:.2f}" if entry_price is not None else "-",
            f"${current_price:.2f}" if current_price is not None else "-",
            f"${cost_basis:,.0f}" if cost_basis is not None else "-",
            f"${current_value:,.0f}" if current_value is not None else "-",
            f"[{pnl_color}]${pnl:+,.0f}[/]" if pnl is not None else "-",
            f"[{pnl_color}]{pnl_pct:+.1f}%[/]" if pnl_pct is not None else "-",
            f"{allocation_pct:.1f}%" if allocation_pct is not None else "-",
        )

    console.print(table)

    # Summary row
    console.print()
    total_pnl = portfolio.get("total_gain_loss", 0)
    total_pnl_pct = portfolio.get("total_gain_loss_pct")
    total_pnl_color = "green" if total_pnl >= 0 else "red"

    console.print(
        f"[bold]Total:[/]  "
        f"Cost: [cyan]${portfolio.get('total_cost_basis', 0):,.0f}[/]  |  "
        f"Value: [cyan]${portfolio.get('total_current_value', 0):,.0f}[/]  |  "
        f"P&L: [{total_pnl_color}]${total_pnl:+,.0f}[/] "
        f"({total_pnl_pct:+.1f}%)" if total_pnl_pct else ""
    )
    console.print(f"[dim]Positions: {portfolio.get('position_count', 0)}[/]")


def _export_portfolio_csv(portfolio: dict, list_name: str) -> None:
    """Export portfolio as CSV to stdout."""
    # Header
    console.print("Ticker,Shares,Entry,Price,Cost,Value,P&L $,P&L %,Allocation %")

    for item in portfolio.get("items", []):
        shares = item.get("shares")
        entry_price = item.get("entry_price")
        current_price = item.get("current_price")
        cost_basis = item.get("cost_basis")
        current_value = item.get("current_value")
        gain_loss = item.get("gain_loss")
        gain_loss_pct = item.get("gain_loss_pct")
        allocation_pct = item.get("allocation_pct")
        row = [
            item.get("ticker", ""),
            f"{shares:.2f}" if shares is not None else "",
            f"{entry_price:.2f}" if entry_price is not None else "",
            f"{current_price:.2f}" if current_price is not None else "",
            f"{cost_basis:.2f}" if cost_basis is not None else "",
            f"{current_value:.2f}" if current_value is not None else "",
            f"{gain_loss:.2f}" if gain_loss is not None else "",
            f"{gain_loss_pct:.2f}" if gain_loss_pct is not None else "",
            f"{allocation_pct:.2f}" if allocation_pct is not None else "",
        ]
        console.print(",".join(row))
