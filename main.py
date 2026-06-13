#!/usr/bin/env python3
"""EgoShell — launch the autonomous ego agent."""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path


async def run_headless() -> None:
    from egoshell.agent import Agent

    # Set up logging for headless mode
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    agent = Agent()
    logging.info("Starting EgoShell agent '%s' in headless mode...", agent.config.persona.name)
    logging.info("Press Ctrl+C to stop.")

    await agent.start()

    stop_event = asyncio.Event()

    def handle_signal():
        logging.info("Shutdown signal received. Stopping agent...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    finally:
        await agent.stop()
        logging.info("Agent stopped gracefully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="EgoShell — launch the autonomous ego agent.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the agent in headless background mode (no UI)"
    )
    args = parser.parse_args()

    home_config = Path.home() / ".egoshell" / "config.yaml"
    project_config = Path(__file__).resolve().parent / "config.yaml"

    # If config is missing or still has placeholder keys, suggest the setup wizard
    if not home_config.exists() and not project_config.exists():
        print("\n  ⚠  No config.yaml found.")
        print("  Run the setup wizard first:\n")
        print("    python setup.py\n")
        sys.exit(1)

    if args.headless:
        try:
            asyncio.run(run_headless())
        except KeyboardInterrupt:
            pass
    else:
        from egoshell.ui.app import EgoShellApp
        app = EgoShellApp()
        app.run()


if __name__ == "__main__":
    main()
