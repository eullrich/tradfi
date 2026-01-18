"""Entry point for Railway deployment."""
import sys
from pathlib import Path

# Add src to path so tradfi package can be imported
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import FastAPI explicitly so Railpack can detect it
from fastapi import FastAPI  # noqa: F401, E402

# Import the actual app instance
from tradfi.api.main import app  # noqa: E402

# Re-export for uvicorn
__all__ = ["app"]
