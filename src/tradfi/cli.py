"""Main CLI entry point for tradfi."""

import os
import typer
from rich.console import Console

from tradfi import __version__

# Default API URL - can be overridden via environment variable
DEFAULT_API_URL = os.environ.get("TRADFI_API_URL", "https://deepv-production.up.railway.app")
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
        DEFAULT_API_URL,
        "--api",
        help="Remote API URL (default: $TRADFI_API_URL or https://deepv-production.up.railway.app)",
    ),
) -> None:
    """
    Launch interactive TUI for browsing and screening stocks.

    Navigate with arrow keys, Enter to select, Escape to go back, q to quit.

    The TUI fetches all data from the remote API server (no local data fetching).
    Set TRADFI_API_URL environment variable to change the default server.
    """
    from tradfi.tui.app import run_tui

    if not api_url:
        console.print("[red]Error: API URL is required.[/]")
        console.print("[dim]Set TRADFI_API_URL environment variable or use --api[/]")
        raise typer.Exit(1)

    console.print(f"[dim]Connecting to API: {api_url}[/]")
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
        DEFAULT_API_URL,
        "--api",
        help="Remote API URL for TUI (default: $TRADFI_API_URL)",
    ),
) -> None:
    """
    TradFi - Value investing CLI tool with oversold indicators.

    Run 'tradfi ui' for interactive mode or use subcommands.

    The TUI requires a remote API server. Set TRADFI_API_URL or use --api.
    """
    if version:
        console.print(f"tradfi version {__version__}")
        raise typer.Exit()

    # If no command provided, launch the TUI
    if ctx.invoked_subcommand is None:
        from tradfi.tui.app import run_tui

        if not api_url:
            console.print("[red]Error: API URL is required for TUI.[/]")
            console.print("[dim]Set TRADFI_API_URL environment variable or use --api[/]")
            raise typer.Exit(1)

        console.print(f"[dim]Connecting to API: {api_url}[/]")
        run_tui(api_url=api_url)


if __name__ == "__main__":
    app()
