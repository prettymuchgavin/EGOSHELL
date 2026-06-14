import asyncio
import logging
import json
from pathlib import Path
from typing import Set
from aiohttp import web

logger = logging.getLogger("egoshell.web")


class WebServer:
    """The EgoShell Web Console server.

    Runs an asynchronous HTTP/WebSocket server alongside the agent.
    """

    def __init__(self, agent, host: str = "127.0.0.1", port: int = 5050) -> None:
        self.agent = agent
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self.clients: Set[web.WebSocketResponse] = set()
        self._tasks: Set[asyncio.Task] = set()

        # Route definitions
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/ws", self.handle_ws)

        # Static assets folder (if additional resources are added later)
        static_path = Path(__file__).resolve().parent / "static"
        self.app.router.add_static("/static/", static_path, name="static")

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve the single-page application dashboard."""
        index_file = Path(__file__).resolve().parent / "static" / "index.html"
        if not index_file.is_file():
            return web.Response(text="EgoShell Web UI index.html not found.", status=404)
        return web.FileResponse(index_file)

    async def handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle real-time WebSocket connection to sync state and stream chat."""
        ws = web.WebSocketResponse(max_msg_size=1024*1024)
        await ws.prepare(request)

        self.clients.add(ws)
        logger.info("WebSocket connection established.")

        # Send initial agent state, chat history, and monologue log
        try:
            soul = self.agent.soul
            mood, intensity = await soul.get_mood()
            obsession = await soul.get_current_obsession()
            history = await soul.get_recent_conversations(limit=50)
            monologue = await soul.get_recent_monologue(limit=50)

            initial_payload = {
                "type": "init",
                "name": self.agent.config.persona.name,
                "mood": mood,
                "intensity": intensity,
                "obsession": obsession,
                "history": history,
                "monologue": monologue,
            }
            await ws.send_json(initial_payload)
        except Exception as e:
            logger.error(f"Failed to transmit initialization data over WS: {e}")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("type") == "chat":
                            text = data.get("text", "").strip()
                            if text:
                                # Stream response in the background to avoid blocking socket read
                                task = asyncio.create_task(self.stream_chat_response(ws, text))
                                self._tasks.add(task)
                                task.add_done_callback(self._tasks.discard)
                    except Exception as e:
                        logger.error(f"WebSocket parse error: {e}")
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.clients.discard(ws)
            logger.info("WebSocket connection closed.")
        return ws

    async def stream_chat_response(self, ws: web.WebSocketResponse, text: str) -> None:
        """Call agent chat stream and forward chunks to the client."""
        try:
            # Broadcast the user's message to update all open tabs
            self.broadcast({
                "type": "user_message",
                "text": text
            })

            # Stream response chunks from the agent
            async for chunk in self.agent.chat(text):
                if ws.closed:
                    break
                await ws.send_json({
                    "type": "chat_chunk",
                    "text": chunk
                })

            if not ws.closed:
                await ws.send_json({
                    "type": "chat_done"
                })

            # Fetch and broadcast updated mood/obsession status
            soul = self.agent.soul
            mood, intensity = await soul.get_mood()
            obsession = await soul.get_current_obsession()
            self.broadcast({
                "type": "status_update",
                "mood": mood,
                "intensity": intensity,
                "obsession": obsession,
            })
        except Exception as e:
            logger.error(f"Error in stream_chat_response: {e}")
            if not ws.closed:
                try:
                    await ws.send_json({
                        "type": "chat_error",
                        "error": str(e)
                    })
                except Exception:
                    pass

    def broadcast(self, data: dict) -> None:
        """Send a payload to all connected clients."""
        for ws in list(self.clients):
            if not ws.closed:
                task = asyncio.create_task(ws.send_json(data))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

    def on_monologue_entry(self, entry: dict) -> None:
        """Callback to push background heartbeat thoughts to clients in real-time."""
        self.broadcast({
            "type": "monologue_entry",
            "entry": entry
        })

    async def start(self) -> None:
        """Setup and start HTTP TCP server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        try:
            await self.site.start()
            logger.info(f"Web Console listening at http://{self.host}:{self.port}")
            # Hook into the agent's heartbeat loop to listen to monologue reflections
            self.agent.heartbeat.add_observer(self.on_monologue_entry)
        except OSError as e:
            logger.warning(
                f"Web Server failed to bind to {self.host}:{self.port}: {e}. "
                "The port might be occupied (likely another EgoShell instance is running)."
            )
            self.site = None
            if self.runner:
                await self.runner.cleanup()
                self.runner = None

    async def stop(self) -> None:
        """Shutdown TCP server and active client connections."""
        # Cancel active background tasks
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Clean up registered observer callback
        try:
            self.agent.heartbeat.remove_observer(self.on_monologue_entry)
        except Exception:
            pass

        if self.site:
            await self.site.stop()
            self.site = None

        if self.runner:
            await self.runner.cleanup()
            self.runner = None

        for ws in list(self.clients):
            try:
                await ws.close()
            except Exception:
                pass
        self.clients.clear()
