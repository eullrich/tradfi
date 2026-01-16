"""Main CLI entry point for tradfi."""

import typer
from rich.console import Console

from tradfi import __version__
from tradfi.commands.analyze import analyze
from tradfi.commands.screen import screen
from tradfi.commands.quarterly import quarterly
from tradfi.commands.compare import compare
from tradfi.commands.watchlist import app as watchlist_app
from tradfi.commands.cache import app as cache_app
from tradfi.commands.lists import app as lists_app

console = Console()

app = typer.Typer(
    name="tradfi",
    help="Value investing CLI tool with oversold indicators.",
    add_completion=False,
)


# Register commands
app.command()(analyze)
app.command()(screen)
app.command()(quarterly)
app.command()(compare)
app.add_typer(watchlist_app, name="watchlist")
app.add_typer(cache_app, name="cache")
app.add_typer(lists_app, name="list")


@app.command()
def ui() -> None:
    """
    Launch interactive TUI for browsing and screening stocks.

    Navigate with arrow keys, Enter to select, Escape to go back, q to quit.
    """
    from tradfi.tui.app import run_tui
    run_tui()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    """
    TradFi - Value investing CLI tool with oversold indicators.

    Run 'tradfi ui' for interactive mode or use subcommands.
    """
    if version:
        console.print(f"tradfi version {__version__}")
        raise typer.Exit()

    # If no command provided, launch the TUI
    if ctx.invoked_subcommand is None:
        from tradfi.tui.app import run_tui
        run_tui()


if __name__ == "__main__":
    app()
