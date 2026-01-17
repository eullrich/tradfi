"""Entry point for Railway web deployment - serves TUI in browser."""
import os

from textual_serve.server import Server

# Get port from environment (Railway sets PORT)
port = int(os.environ.get("PORT", 8000))
host = os.environ.get("HOST", "0.0.0.0")

# Create server that runs the TUI app via run_tui.py
server = Server(
    command="python run_tui.py",
    host=host,
    port=port,
)

if __name__ == "__main__":
    server.serve()
