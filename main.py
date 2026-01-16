"""Entry point for Railway deployment."""
import sys
from pathlib import Path

# Add src to path so tradfi package can be imported
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tradfi.api.main import app  # noqa: E402

# Railway/uvicorn will auto-detect this FastAPI app
