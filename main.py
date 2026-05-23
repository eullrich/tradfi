"""FastAPI Cloud entry point — auto-discovered by `fastapi deploy`.

`fastapi-cli` looks for `main.py` / `app.py` / `api.py` at the repo root and
imports `app` from it. This module exists solely to satisfy that contract;
the real FastAPI app lives in `src/tradfi/api/main.py`.
"""

import sys
from pathlib import Path

# When the app is run directly (not pip-installed), make the `tradfi`
# package importable. After `pip install -e .` or `pip install .` this
# insertion is harmless.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tradfi.api.main import app  # noqa: E402

__all__ = ["app"]
