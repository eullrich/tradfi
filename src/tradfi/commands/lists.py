"""List management commands - view, manage, and export saved stock lists."""

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from tradfi.utils.cache import (
    list_saved_lists,
    get_saved_list,
    delete_saved_list,
    save_list,
    add_to_saved_list,
    remove_from_saved_list,
    create_category,
    list_categories,
    delete_category,
    add_list_to_category,
    remove_list_from_category,
    get_lists_in_category,
    set_item_note,
    get_item_note,
    get_all_item_notes,
)

console = Console()

# Reserved list names for long/short positions
LONG_LIST = "_long"
SHORT_LIST = "_short"

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
    lists = list_saved_lists()

    if not lists:
        console.print("[yellow]No saved lists found.[/]")
        console.print("[dim]Create one with: tradfi screen --pe-max 15 --save my-list[/]")
        return

    table = Table(
        title="Saved Lists",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )

    table.add_column("Name", style="bold cyan")
    table.add_column("Stocks", justify="right")
    table.add_column("Description")
    table.add_column("Updated", justify="right")

    for lst in lists:
        updated = datetime.fromtimestamp(lst["updated_at"]).strftime("%Y-%m-%d %H:%M")
        table.add_row(
            lst["name"],
            str(lst["count"]),
            lst["description"] or "-",
            updated,
        )

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
    tickers = get_saved_list(name)

    if tickers is None:
        console.print(f"[red]List '{name}' not found.[/]")
        console.print("[dim]See available lists: tradfi list ls[/]")
        raise typer.Exit(1)

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
    console.print(f"[dim]  Screen this list: tradfi screen -t {','.join(tickers[:5])}{',...' if len(tickers) > 5 else ''}[/]")
    console.print(f"[dim]  Export tickers:   tradfi list show {name} --export[/]")
    console.print(f"[dim]  Delete list:      tradfi list delete {name}[/]")


@app.command("delete")
def delete_list(
    name: str = typer.Argument(..., help="Name of the list to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Delete a saved list.

    Example:
        tradfi list delete my-old-picks
        tradfi list delete my-old-picks --force
    """
    tickers = get_saved_list(name)

    if tickers is None:
        console.print(f"[red]List '{name}' not found.[/]")
        raise typer.Exit(1)

    if not force:
        console.print(f"Delete list '{name}' with {len(tickers)} stocks?")
        if not typer.confirm("Continue?"):
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(0)

    if delete_saved_list(name):
        console.print(f"[green]Deleted list '{name}'[/]")
    else:
        console.print(f"[red]Failed to delete list '{name}'[/]")


@app.command("create")
def create_list(
    name: str = typer.Argument(..., help="Name for the new list"),
    tickers: str = typer.Argument(..., help="Comma-separated list of tickers"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description for the list"),
) -> None:
    """
    Create a new list from tickers.

    Example:
        tradfi list create tech-picks AAPL,MSFT,GOOGL,NVDA
        tradfi list create dividends KO,PG,JNJ --desc "Dividend aristocrats"
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    if not ticker_list:
        console.print("[red]No valid tickers provided.[/]")
        raise typer.Exit(1)

    save_list(name, ticker_list, description)
    console.print(f"[green]Created list '{name}' with {len(ticker_list)} stocks[/]")


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
    ticker = ticker.upper()

    if add_to_saved_list(name, ticker):
        console.print(f"[green]Added {ticker} to '{name}'[/]")
    else:
        # Check if list exists
        if get_saved_list(name) is None:
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
    ticker = ticker.upper()

    if remove_from_saved_list(name, ticker):
        console.print(f"[green]Removed {ticker} from '{name}'[/]")
    else:
        console.print(f"[yellow]{ticker} not found in '{name}'[/]")


@app.command("screen")
def screen_list(
    name: str = typer.Argument(..., help="Name of the list to screen"),
) -> None:
    """
    Run a screen on stocks in a saved list.

    This is a shortcut that passes the list's tickers to the screen command.

    Example:
        tradfi list screen my-picks
    """
    tickers = get_saved_list(name)

    if tickers is None:
        console.print(f"[red]List '{name}' not found.[/]")
        raise typer.Exit(1)

    # Import and call screen with these tickers
    from tradfi.commands.screen import screen as screen_cmd

    console.print(f"[dim]Screening {len(tickers)} stocks from list '{name}'[/]")

    # Call screen with the tickers - we need to invoke it via Typer context
    # For now, just print the command to run
    tickers_str = ",".join(tickers)
    console.print(f"\n[dim]Run: tradfi screen -t {tickers_str}[/]")
    console.print(f"[dim]Or add filters: tradfi screen -t {tickers_str} --pe-max 15[/]")


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
    # Ensure the list exists
    if get_saved_list(LONG_LIST) is None:
        save_list(LONG_LIST, [], "Stocks to go long on")

    if clear:
        save_list(LONG_LIST, [], "Stocks to go long on")
        console.print("[green]Long list cleared[/]")
        return

    if ticker:
        ticker = ticker.upper()
        if remove:
            if remove_from_saved_list(LONG_LIST, ticker):
                console.print(f"[green]Removed {ticker} from long list[/]")
            else:
                console.print(f"[yellow]{ticker} not in long list[/]")
        else:
            if add_to_saved_list(LONG_LIST, ticker):
                console.print(f"[green]Added {ticker} to long list[/]")
            else:
                console.print(f"[yellow]{ticker} already in long list[/]")
        return

    # View the list
    tickers = get_saved_list(LONG_LIST) or []
    _display_position_list("Long List", tickers, "green", "buy")


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
    # Ensure the list exists
    if get_saved_list(SHORT_LIST) is None:
        save_list(SHORT_LIST, [], "Stocks to short")

    if clear:
        save_list(SHORT_LIST, [], "Stocks to short")
        console.print("[red]Short list cleared[/]")
        return

    if ticker:
        ticker = ticker.upper()
        if remove:
            if remove_from_saved_list(SHORT_LIST, ticker):
                console.print(f"[red]Removed {ticker} from short list[/]")
            else:
                console.print(f"[yellow]{ticker} not in short list[/]")
        else:
            if add_to_saved_list(SHORT_LIST, ticker):
                console.print(f"[red]Added {ticker} to short list[/]")
            else:
                console.print(f"[yellow]{ticker} already in short list[/]")
        return

    # View the list
    tickers = get_saved_list(SHORT_LIST) or []
    _display_position_list("Short List", tickers, "red", "short")


def _display_position_list(title: str, tickers: list[str], color: str, action: str) -> None:
    """Display a long or short position list with current prices."""
    from tradfi.core.data import fetch_stock

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
        stock = fetch_stock(ticker)
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
    color: Optional[str] = typer.Option(None, "--color", "-c", help="Color for the category"),
) -> None:
    """
    Create a new category for organizing lists.

    Examples:
        tradfi list category create "Value Picks"
        tradfi list category create "Tech" --icon "💻" --color blue
    """
    category_id = create_category(name, color=color, icon=icon)
    if category_id:
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
    categories = list_categories()

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
    table.add_column("Color")
    table.add_column("Lists", justify="right")

    for cat in categories:
        lists_in_cat = get_lists_in_category(cat["id"])
        list_count = len(lists_in_cat) if lists_in_cat else 0
        table.add_row(
            str(cat["id"]),
            cat["name"],
            cat["icon"] or "-",
            cat["color"] or "-",
            str(list_count),
        )

    console.print(table)


@category_app.command("delete")
def category_delete(
    name: str = typer.Argument(..., help="Category name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Delete a category.

    Example:
        tradfi list category delete "Old Category"
    """
    if not force:
        if not typer.confirm(f"Delete category '{name}'?"):
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(0)

    if delete_category(name):
        console.print(f"[green]Deleted category '{name}'[/]")
    else:
        console.print(f"[red]Category '{name}' not found[/]")


@app.command("move")
def move_list(
    list_name: str = typer.Argument(..., help="Name of the list to move"),
    category_name: str = typer.Argument(..., help="Target category name"),
) -> None:
    """
    Move a list to a category.

    Example:
        tradfi list move my-picks "Value Picks"
    """
    # Find category ID
    categories = list_categories()
    category = next((c for c in categories if c["name"].lower() == category_name.lower()), None)

    if not category:
        console.print(f"[red]Category '{category_name}' not found.[/]")
        console.print("[dim]Create it with: tradfi list category create \"{category_name}\"[/]")
        raise typer.Exit(1)

    # Check list exists
    if get_saved_list(list_name) is None:
        console.print(f"[red]List '{list_name}' not found.[/]")
        raise typer.Exit(1)

    if add_list_to_category(list_name, category["id"]):
        icon = category.get("icon", "")
        console.print(f"[green]Moved '{list_name}' to {icon} {category_name}[/]")
    else:
        console.print(f"[yellow]'{list_name}' is already in '{category_name}'[/]")


@app.command("unmove")
def unmove_list(
    list_name: str = typer.Argument(..., help="Name of the list to remove from category"),
    category_name: str = typer.Argument(..., help="Category name to remove from"),
) -> None:
    """
    Remove a list from a category.

    Example:
        tradfi list unmove my-picks "Value Picks"
    """
    categories = list_categories()
    category = next((c for c in categories if c["name"].lower() == category_name.lower()), None)

    if not category:
        console.print(f"[red]Category '{category_name}' not found.[/]")
        raise typer.Exit(1)

    if remove_list_from_category(list_name, category["id"]):
        console.print(f"[green]Removed '{list_name}' from '{category_name}'[/]")
    else:
        console.print(f"[yellow]'{list_name}' was not in '{category_name}'[/]")


# ============================================================================
# Enhanced Notes Commands
# ============================================================================

@app.command("note")
def note_ticker(
    list_name: str = typer.Argument(..., help="Name of the list"),
    ticker: str = typer.Argument(..., help="Ticker to add note to"),
    notes: Optional[str] = typer.Argument(None, help="Note text (omit to view current note)"),
    thesis: Optional[str] = typer.Option(None, "--thesis", "-t", help="Investment thesis"),
    entry: Optional[float] = typer.Option(None, "--entry", "-e", help="Entry price target"),
    target: Optional[float] = typer.Option(None, "--target", "-T", help="Target price"),
) -> None:
    """
    Add or view notes for a ticker in a list.

    Examples:
        tradfi list note my-picks AAPL "Strong moat, waiting for pullback"
        tradfi list note my-picks AAPL --thesis "Services growth play"
        tradfi list note my-picks AAPL --entry 165 --target 200
        tradfi list note my-picks AAPL  # View current note
    """
    ticker = ticker.upper()

    # Check list exists and has ticker
    tickers = get_saved_list(list_name)
    if tickers is None:
        console.print(f"[red]List '{list_name}' not found.[/]")
        raise typer.Exit(1)

    if ticker not in tickers:
        console.print(f"[yellow]{ticker} is not in list '{list_name}'[/]")
        console.print(f"[dim]Add it first: tradfi list add {list_name} {ticker}[/]")
        raise typer.Exit(1)

    # If no new data provided, show current note
    if notes is None and thesis is None and entry is None and target is None:
        existing = get_item_note(list_name, ticker)
        if existing:
            console.print(f"\n[bold cyan]{ticker}[/] in [bold]{list_name}[/]\n")
            if existing.get("notes"):
                console.print(f"[bold]Notes:[/] {existing['notes']}")
            if existing.get("thesis"):
                console.print(f"[bold]Thesis:[/] {existing['thesis']}")
            if existing.get("entry_price"):
                console.print(f"[bold]Entry:[/] ${existing['entry_price']:.2f}")
            if existing.get("target_price"):
                console.print(f"[bold]Target:[/] ${existing['target_price']:.2f}")
            console.print()
        else:
            console.print(f"[yellow]No notes for {ticker} in '{list_name}'[/]")
        return

    # Set/update note
    set_item_note(
        list_name=list_name,
        ticker=ticker,
        notes=notes,
        thesis=thesis,
        entry_price=entry,
        target_price=target,
    )
    console.print(f"[green]Updated notes for {ticker} in '{list_name}'[/]")


@app.command("notes")
def show_notes(
    list_name: str = typer.Argument(..., help="Name of the list"),
) -> None:
    """
    Show all notes for a list.

    Example:
        tradfi list notes my-picks
    """
    tickers = get_saved_list(list_name)
    if tickers is None:
        console.print(f"[red]List '{list_name}' not found.[/]")
        raise typer.Exit(1)

    notes = get_all_item_notes(list_name)

    if not notes:
        console.print(f"[yellow]No notes in list '{list_name}'[/]")
        console.print(f"[dim]Add notes with: tradfi list note {list_name} <TICKER> \"Your note\"[/]")
        return

    console.print(f"\n[bold cyan]{list_name}[/] Notes\n")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Notes")
    table.add_column("Thesis", style="dim")
    table.add_column("Entry", justify="right")
    table.add_column("Target", justify="right")

    for note in notes:
        entry_str = f"${note['entry_price']:.2f}" if note.get("entry_price") else "-"
        target_str = f"${note['target_price']:.2f}" if note.get("target_price") else "-"
        notes_str = (note.get("notes") or "")[:40]
        if len(note.get("notes") or "") > 40:
            notes_str += "..."
        thesis_str = (note.get("thesis") or "")[:30]
        if len(note.get("thesis") or "") > 30:
            thesis_str += "..."

        table.add_row(
            note["ticker"],
            notes_str,
            thesis_str,
            entry_str,
            target_str,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]View full note: tradfi list note {list_name} <TICKER>[/]")
