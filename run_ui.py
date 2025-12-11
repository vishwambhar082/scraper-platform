#!/usr/bin/env python3
"""
Launch the Scraper Platform Desktop UI.

This is the main entry point for running the desktop application.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.main_window import main

if __name__ == "__main__":
    sys.exit(main())

