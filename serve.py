"""Entry point for Railway web deployment - serves TUI in browser."""
import os
import sys
from pathlib import Path

# Add src to path so tradfi package can be imported
sys.path.insert(0, str(Path(__file__).parent / "src"))

from textual_serve.server import Server

# Get port from environment (Railway sets PORT)
port = int(os.environ.get("PORT", 8000))
host = os.environ.get("HOST", "0.0.0.0")

# Create server that runs the TUI app
server = Server(
    command=f"python -c \"import sys; sys.path.insert(0, 'src'); from tradfi.tui.app import ScreenerApp; ScreenerApp().run()\"",
    host=host,
    port=port,
)

if __name__ == "__main__":
    server.serve()
