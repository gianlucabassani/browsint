"""Top-level CLI package shim for tests.

This shim allows tests that import `cli.scraper_cli` (without the `src.`
prefix) to work by importing the implementation from `src.cli.scraper_cli`.
It keeps a minimal surface area and avoids duplicating code.
"""
from importlib import import_module
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src` package can be imported
project_root = str(Path(__file__).parent.resolve())
parent = str(Path(project_root).parent)
if parent not in sys.path:
    sys.path.insert(0, parent)

_mod = import_module("src.cli.scraper_cli")

# Re-export the main CLI class and other useful symbols
ScraperCLI = getattr(_mod, "ScraperCLI")

__all__ = ["ScraperCLI"]
