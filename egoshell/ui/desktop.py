"""Desktop UI launcher using pywebview."""

import asyncio
import sys
import threading
import time
import webview
from egoshell.agent import Agent
from egoshell.config import load_config


def run_desktop() -> None:
    """Launch the EgoShell agent and open the native webview desktop application container."""
    config = load_config()
    # Ensure web server is enabled since the desktop UI embeds it
    config.web.enabled = True

    agent = Agent(config)
    loop = asyncio.new_event_loop()

    def start_agent_loop() -> None:
        asyncio.set_event_loop(loop)
        # Initialize and start agent (Web server starts binding here)
        loop.run_until_complete(agent.start())
        loop.run_forever()

    # Run agent in background thread to avoid blocking pywebview UI
    t = threading.Thread(target=start_agent_loop, daemon=True)
    t.start()

    # Wait a moment for database and web server to bind
    time.sleep(1.2)

    url = f"http://{config.web.host}:{config.web.port}"

    # Create native window
    window = webview.create_window(
        title=f"EgoShell // {config.persona.name}",
        url=url,
        width=1100,
        height=750,
        min_size=(900, 650),
        background_color="#050508",  # Match dark UI theme to prevent white flashes
    )

    def on_closed() -> None:
        """Trigger cleanup of agent database and server resources when window closes."""
        try:
            future = asyncio.run_coroutine_threadsafe(agent.stop(), loop)
            future.result(timeout=5.0)
        except Exception:
            pass
        finally:
            loop.call_soon_threadsafe(loop.stop)

    window.events.closed += on_closed

    # Start the desktop GUI loop
    webview.start()
