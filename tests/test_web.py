import asyncio
import unittest
import aiohttp
from unittest.mock import AsyncMock, MagicMock
from egoshell.config import Config, WebConfig, PersonaConfig
from egoshell.web.server import WebServer


class TestWeb(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_web_server_endpoints(self):
        async def run():
            # Mock Agent
            mock_agent = MagicMock()
            mock_agent.config = Config(
                web=WebConfig(enabled=True, host="127.0.0.1", port=5959),
                persona=PersonaConfig(name="MockEgo"),
            )
            mock_agent.soul = AsyncMock()
            mock_agent.soul.get_mood.return_value = ("Brooding", 0.6)
            mock_agent.soul.get_current_obsession.return_value = "testing things"
            mock_agent.soul.get_recent_conversations.return_value = []
            mock_agent.soul.get_recent_monologue.return_value = []
            
            mock_agent.heartbeat = MagicMock()
            mock_agent.heartbeat.add_observer = MagicMock()
            mock_agent.heartbeat.remove_observer = MagicMock()

            # Initialize and start WebServer
            server = WebServer(agent=mock_agent, host="127.0.0.1", port=5959)
            await server.start()

            # Verify it registered monologue observer
            mock_agent.heartbeat.add_observer.assert_called_once_with(server.on_monologue_entry)

            # Test HTTP GET /
            session = aiohttp.ClientSession()
            try:
                async with session.get("http://127.0.0.1:5959/") as resp:
                    self.assertEqual(resp.status, 200)
                    text = await resp.text()
                    self.assertIn("EGOSHELL", text)

                # Test WebSocket
                async with session.ws_connect("http://127.0.0.1:5959/ws") as ws:
                    msg = await ws.receive_json(timeout=2)
                    self.assertEqual(msg["type"], "init")
                    self.assertEqual(msg["name"], "MockEgo")
                    self.assertEqual(msg["mood"], "Brooding")
                    self.assertEqual(msg["obsession"], "testing things")
            finally:
                await session.close()
                await server.stop()

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
