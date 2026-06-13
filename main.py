#!/usr/bin/env python3
"""EgoShell — launch the autonomous ego agent."""

import sys
from pathlib import Path


def main() -> None:
    home_config = Path.home() / ".egoshell" / "config.yaml"
    project_config = Path(__file__).resolve().parent / "config.yaml"

    # If config is missing or still has placeholder keys, suggest the setup wizard
    if not home_config.exists() and not project_config.exists():
        print("\n  ⚠  No config.yaml found.")
        print("  Run the setup wizard first:\n")
        print("    python setup.py\n")
        sys.exit(1)

    from egoshell.ui.app import EgoShellApp

    app = EgoShellApp()
    app.run()


if __name__ == "__main__":
    main()
