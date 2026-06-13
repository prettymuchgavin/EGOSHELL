import asyncio
import unittest
from textual.app import App, ComposeResult
from egoshell.ui.app import ChatMessage


class TestApp(App):
    def compose(self) -> ComposeResult:
        self.msg = ChatMessage(role="assistant", content="Initial")
        yield self.msg


class TestUI(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_chat_message_parsing(self):
        async def run():
            app = TestApp()
            async with app.run_test() as pilot:
                msg = app.msg
                
                # Test initial state (no think tag)
                self.assertEqual(str(msg.body_static.render()), "Initial")
                self.assertFalse(msg.collapsible.display)

                # Test message with complete think tag
                msg.update_content("<think>I am pondering</think>Hello world")
                self.assertTrue(msg.collapsible.display)
                thinking_content = msg.collapsible.query_one("#thinking-content")
                self.assertEqual(str(thinking_content.render()), "I am pondering")
                self.assertEqual(str(msg.body_static.render()), "Hello world")

                # Test message with unclosed think tag (streaming)
                msg.update_content("<think>Pondering...")
                self.assertTrue(msg.collapsible.display)
                self.assertEqual(str(thinking_content.render()), "Pondering...")
                self.assertEqual(str(msg.body_static.render()), "")

                # Test message with normal content (no think tag)
                msg.update_content("Just normal text")
                self.assertFalse(msg.collapsible.display)
                self.assertEqual(str(msg.body_static.render()), "Just normal text")

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
