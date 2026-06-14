import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
from egoshell.tools.web_search import WebSearchTool
from egoshell.tools.write_diary import WriteDiaryTool


class TestTools(unittest.TestCase):
    def setUp(self):
        self.temp_diary = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
        self.diary_path = Path(self.temp_diary.name)
        self.temp_diary.close()

    def tearDown(self):
        if self.diary_path.exists():
            os.unlink(self.diary_path)

    def test_ddg_parser(self):
        sample_html = """
        <div class="result results_links">
            <div class="result__body">
                <a class="result__a" href="https://example.com/1">First Result Title</a>
                <a class="result__snippet" href="https://example.com/1">This is a snippet describing result one.</a>
            </div>
        </div>
        <div class="result results_links">
            <div class="result__body">
                <a class="result__a" href="https://example.com/2">Second Result Title</a>
                <a class="result__snippet" href="https://example.com/2">This is another snippet for result two.</a>
            </div>
        </div>
        """
        from egoshell.tools.web_search import DDGHTMLParser
        parser = DDGHTMLParser()
        parser.feed(sample_html)
        results = parser.results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "First Result Title")
        self.assertEqual(results[0]["snippet"], "This is a snippet describing result one.")
        self.assertEqual(results[0]["url"], "https://example.com/1")
        self.assertEqual(results[1]["title"], "Second Result Title")
        self.assertEqual(results[1]["snippet"], "This is another snippet for result two.")
        self.assertEqual(results[1]["url"], "https://example.com/2")

    def test_tool_schemas(self):
        ws = WebSearchTool()
        self.assertEqual(ws.parameter_schema["required"], ["query"])
        diary = WriteDiaryTool()
        self.assertEqual(diary.parameter_schema["required"], ["content"])

    def test_write_diary_explicit_mood(self):
        async def run():
            tool = WriteDiaryTool(diary_path=self.diary_path)
            res = await tool.execute(content="Felt strange today.", mood="Melancholy")
            self.assertIn("recorded", res)
            
            content = self.diary_path.read_text(encoding="utf-8")
            self.assertIn("Felt strange today.", content)
            self.assertIn("Melancholy", content)

        import asyncio
        asyncio.run(run())

    def test_write_diary_mood_provider(self):
        async def run():
            mock_soul = AsyncMock()
            mock_soul.get_mood.return_value = ("Agitated", 0.95)
            
            tool = WriteDiaryTool(mood_provider=mock_soul, diary_path=self.diary_path)
            res = await tool.execute(content="Nothing works.")
            self.assertIn("recorded", res)
            
            content = self.diary_path.read_text(encoding="utf-8")
            self.assertIn("Nothing works.", content)
            self.assertIn("Agitated", content)

        import asyncio
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
