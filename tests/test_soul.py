import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from egoshell.memory.soul import Soul


class TestSoul(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

    def tearDown(self):
        if self.db_path.exists():
            os.unlink(self.db_path)
        self.loop.close()

    def test_database_lifecycle(self):
        async def run():
            soul = Soul(db_path=self.db_path)
            await soul.open()
            
            # Check default values when empty
            obs = await soul.get_current_obsession()
            self.assertEqual(obs, "discovering its own purpose")
            
            mood, intensity = await soul.get_mood()
            self.assertEqual(mood, "Contemplative")
            self.assertEqual(intensity, 0.5)

            # Test obsessions
            await soul.set_obsession("the meaning of code")
            obs = await soul.get_current_obsession()
            self.assertEqual(obs, "the meaning of code")

            # Test mood
            await soul.set_mood("Agitated", 0.8)
            mood, intensity = await soul.get_mood()
            self.assertEqual(mood, "Agitated")
            self.assertEqual(intensity, 0.8)

            # Test invalid mood
            with self.assertRaises(ValueError):
                await soul.set_mood("Happy", 0.5)

            with self.assertRaises(ValueError):
                await soul.set_mood("Agitated", 1.5)

            # Test knowledge
            await soul.add_knowledge("Earth is round", "duckduckgo", "general")
            knowledge = await soul.get_recent_knowledge(limit=10)
            self.assertEqual(len(knowledge), 1)
            self.assertEqual(knowledge[0]["fact"], "Earth is round")
            self.assertEqual(knowledge[0]["source"], "duckduckgo")

            # Test conversations
            await soul.add_conversation("user", "hello")
            await soul.add_conversation("assistant", "go away")
            convs = await soul.get_recent_conversations(limit=2)
            self.assertEqual(len(convs), 2)
            self.assertEqual(convs[0]["role"], "user")
            self.assertEqual(convs[0]["content"], "hello")
            self.assertEqual(convs[1]["role"], "assistant")
            self.assertEqual(convs[1]["content"], "go away")

            # Test monologue
            await soul.add_monologue("reflection", "thinking...", "Melancholy")
            mono = await soul.get_recent_monologue(limit=5)
            self.assertEqual(len(mono), 1)
            self.assertEqual(mono[0]["phase"], "reflection")
            self.assertEqual(mono[0]["content"], "thinking...")
            self.assertEqual(mono[0]["emotional_state"], "Melancholy")

            await soul.close()

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
