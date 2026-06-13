import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from egoshell.agent import Agent
from egoshell.config import Config, LLMConfig, HeartbeatConfig, PersonaConfig


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.db_path = self.data_dir / "soul.db"
        self.log_path = self.data_dir / "monologue.log"

        self.config = Config(
            llm=LLMConfig(provider="ollama", model="llama3.1:8b"),
            heartbeat=HeartbeatConfig(interval_minutes=5),
            persona=PersonaConfig(
                name="EgoTest",
                initial_obsession="testing things",
                initial_mood="brooding"
            ),
            data_dir=self.data_dir
        )

    def tearDown(self):
        self.temp_dir.cleanup()
        self.loop.close()

    def test_agent_lifecycle_and_chat(self):
        async def run():
            # Mock the LLM provider creation
            from unittest.mock import MagicMock
            mock_llm = AsyncMock()
            mock_llm.stream = MagicMock(side_effect=lambda *args, **kwargs: self.async_generator_mock(["Thinking", "...", " Done."]))

            with patch("egoshell.agent.create_provider", return_value=mock_llm), \
                 patch("egoshell.memory.soul._DB_PATH", self.db_path), \
                 patch("egoshell.heartbeat.Path.home", return_value=self.data_dir):
                
                agent = Agent(config=self.config)
                await agent.start()

                # Check that soul was initialized and seeded with config defaults
                obsession = await agent.soul.get_current_obsession()
                self.assertEqual(obsession, "testing things")

                mood, intensity = await agent.soul.get_mood()
                self.assertEqual(mood, "Brooding")  # Capitalized
                self.assertEqual(intensity, 0.6)

                # Test chat streaming
                response_tokens = []
                async for token in agent.chat("Are you there?"):
                    response_tokens.append(token)

                self.assertEqual("".join(response_tokens), "Thinking... Done.")

                # Verify conversation was recorded
                convs = await agent.soul.get_recent_conversations(limit=2)
                self.assertEqual(len(convs), 2)
                self.assertEqual(convs[0]["role"], "user")
                self.assertEqual(convs[0]["content"], "Are you there?")
                self.assertEqual(convs[1]["role"], "assistant")
                self.assertEqual(convs[1]["content"], "Thinking... Done.")

                await agent.stop()

        self.loop.run_until_complete(run())

    @staticmethod
    async def async_generator_mock(items):
        for item in items:
            yield item


if __name__ == "__main__":
    unittest.main()
