"""Entry point for Railway deployment."""
import os
import sys
from pathlib import Path

# Add src to path so tradfi package can be imported
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI  # noqa: E402, F401 - needed for Railpack detection

# Import the actual app
from tradfi.api.main import app  # noqa: E402

# For running directly with `python main.py`
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
