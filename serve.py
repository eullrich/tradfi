"""Entry point for Railway web deployment - serves TUI in browser."""
import os

from textual_serve.server import Server

# Set PYTHONPATH so subprocess can find tradfi package
os.environ["PYTHONPATH"] = os.path.join(os.getcwd(), "src")

# Get port from environment (Railway sets PORT)
port = int(os.environ.get("PORT", 8000))
host = os.environ.get("HOST", "0.0.0.0")

# Get public URL for Railway (needed for HTTPS proxy)
public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
public_url = f"https://{public_domain}" if public_domain else None

# Create server that runs the TUI app via run_tui.py
server = Server(
    command="python run_tui.py",
    host=host,
    port=port,
    public_url=public_url,
)

if __name__ == "__main__":
    server.serve()
