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
def ui(
    api_url: str = typer.Option(
        None,
        "--api",
        help="Remote API URL (e.g., https://deepvalue-production.up.railway.app)",
    ),
) -> None:
    """
    Launch interactive TUI for browsing and screening stocks.

    Navigate with arrow keys, Enter to select, Escape to go back, q to quit.

    Use --api to connect to a remote TradFi server instead of fetching locally.
    """
    from tradfi.tui.app import run_tui
    run_tui(api_url=api_url)


@app.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """
    Start the REST API server.

    The API provides endpoints for stock analysis, screening, and list management.
    Visit http://localhost:8000/docs for interactive API documentation.
    """
    import uvicorn

    console.print(f"[green]Starting TradFi API server on {host}:{port}[/green]")
    console.print(f"[blue]API docs: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs[/blue]")

    uvicorn.run(
        "tradfi.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


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
    api_url: str = typer.Option(
        None,
        "--api",
        help="Remote API URL for TUI (e.g., https://deepvalue-production.up.railway.app)",
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
        run_tui(api_url=api_url)


if __name__ == "__main__":
    app()
