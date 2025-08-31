#!/usr/bin/env python3
"""Main entry point for the Coding Swarm CLI package."""
from __future__ import annotations

import sys
from .modern_ui import modern_cli
from .interactive import app

if __name__ == "__main__":
    # Check if running interactively
    if len(sys.argv) == 1 and sys.stdin.isatty():
        # Interactive mode with modern UI
        modern_cli.show_main_menu()
    else:
        # Command-line mode with typer
        app()