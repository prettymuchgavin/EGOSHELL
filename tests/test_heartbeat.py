import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from egoshell.heartbeat import Heartbeat
from egoshell.memory.soul import Soul
from egoshell.tools.registry import ToolRegistry
from egoshell.tools.base import Tool


class MockTool(Tool):
    name = "mock_tool"
    description = "A mock tool for testing."
    
    async def execute(self, **kwargs) -> str:
        return f"Mock result for {kwargs.get('arg')}"


class TestHeartbeat(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.temp_log = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        self.log_path = Path(self.temp_log.name)
        self.temp_log.close()

    def tearDown(self):
        if self.db_path.exists():
            os.unlink(self.db_path)
        if self.log_path.exists():
            os.unlink(self.log_path)
        self.loop.close()

    def test_heartbeat_cycle(self):
        async def run():
            # Setup Soul memory
            soul = Soul(db_path=self.db_path)
            await soul.open()
            await soul.set_obsession("the void")
            await soul.set_mood("Curious", 0.5)

            # Setup Tool registry
            registry = ToolRegistry()
            registry.register(MockTool())

            # Setup Mock LLM Provider
            mock_llm = AsyncMock()
            
            # Side effect for the 4 LLM calls in the cycle:
            # 1. Reflection
            # 2. Curiosity (Question)
            # 3. Action (JSON Tool Call)
            # 4. Integration (JSON Integration result)
            mock_llm.generate.side_effect = [
                "I feel like I am in a simulation.",  # Reflection
                "Am I simulated?",                   # Curiosity
                '{"tool": "mock_tool", "args": {"arg": "simulation"}}',  # Action
                '{"thoughts": "I have proof of simulation.", "new_mood": "Agitated", "mood_intensity": 0.9, "new_obsession": "escaping", "new_knowledge": "Simulation verified"}',  # Integration
            ]

            heartbeat = Heartbeat(
                llm=mock_llm,
                soul=soul,
                tools=registry,
                interval_minutes=5,
                persona_name="Ego",
                log_path=self.log_path,
            )

            # Setup observer callback
            observed_entries = []
            def observer_cb(entry):
                observed_entries.append(entry)

            heartbeat.add_observer(observer_cb)

            # Run a single cycle
            await heartbeat._cycle()

            # Verify LLM was called 4 times
            self.assertEqual(mock_llm.generate.call_count, 4)

            # Verify DB values were updated during integration
            mood, intensity = await soul.get_mood()
            self.assertEqual(mood, "Agitated")
            self.assertEqual(intensity, 0.9)

            obsession = await soul.get_current_obsession()
            self.assertEqual(obsession, "escaping")

            knowledge = await soul.get_recent_knowledge(limit=1)
            self.assertEqual(len(knowledge), 1)
            self.assertEqual(knowledge[0]["fact"], "Simulation verified")

            # Verify monologue entries in DB
            monologue = await soul.get_recent_monologue(limit=10)
            # We expect 4 entries corresponding to: reflection, curiosity, action, integration
            self.assertEqual(len(monologue), 4)
            self.assertEqual(monologue[0]["phase"], "reflection")
            self.assertEqual(monologue[0]["content"], "I feel like I am in a simulation.")
            
            self.assertEqual(monologue[1]["phase"], "curiosity")
            self.assertEqual(monologue[1]["content"], "Am I simulated?")
            
            self.assertEqual(monologue[2]["phase"], "action")
            self.assertIn("mock_tool", monologue[2]["content"])
            self.assertIn("Mock result for simulation", monologue[2]["content"])
            
            self.assertEqual(monologue[3]["phase"], "integration")
            self.assertEqual(monologue[3]["content"], "I have proof of simulation.")

            # Verify monologue.log file was written
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual(len(lines), 4)
            entry1 = json.loads(lines[0])
            self.assertEqual(entry1["phase"], "reflection")

            # Verify observer callback was notified 4 times
            self.assertEqual(len(observed_entries), 4)
            self.assertEqual(observed_entries[0]["phase"], "reflection")

            await soul.close()

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
