#!/usr/bin/env python
"""Run the TUI app - used by textual-serve."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tradfi.tui.app import ScreenerApp

if __name__ == "__main__":
    app = ScreenerApp()
    app.run()
