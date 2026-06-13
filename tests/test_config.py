import os
import tempfile
import unittest
from pathlib import Path
from egoshell.config import load_config, Config, LLMConfig, HeartbeatConfig, PersonaConfig


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.config_file = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w")
        self.config_path = Path(self.config_file.name)

    def tearDown(self):
        if self.config_path.exists():
            os.unlink(self.config_path)
        # Clear env variables that could affect tests
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_BASE_URL", "EGOSHELL_PROVIDER", "EGOSHELL_MODEL"]:
            if key in os.environ:
                del os.environ[key]

    def test_default_config(self):
        # Write empty config
        self.config_file.write("")
        self.config_file.close()

        config = load_config(self.config_path)
        self.assertEqual(config.llm.provider, "ollama")
        self.assertEqual(config.llm.model, "llama3.1:8b")
        self.assertEqual(config.heartbeat.interval_minutes, 5)
        self.assertEqual(config.persona.name, "Ego")

    def test_yaml_config(self):
        yaml_content = """
llm:
  provider: openai
  model: gpt-4o
  temperature: 0.7
  max_tokens: 1000
heartbeat:
  interval_minutes: 10
persona:
  name: CustomName
  initial_obsession: "cookies"
  initial_mood: "defiant"
"""
        self.config_file.write(yaml_content)
        self.config_file.close()

        config = load_config(self.config_path)
        self.assertEqual(config.llm.provider, "openai")
        self.assertEqual(config.llm.model, "gpt-4o")
        self.assertEqual(config.llm.temperature, 0.7)
        self.assertEqual(config.llm.max_tokens, 1000)
        self.assertEqual(config.heartbeat.interval_minutes, 10)
        self.assertEqual(config.persona.name, "CustomName")
        self.assertEqual(config.persona.initial_obsession, "cookies")
        self.assertEqual(config.persona.initial_mood, "defiant")

    def test_env_overrides(self):
        yaml_content = """
llm:
  provider: openai
  model: gpt-4o
"""
        self.config_file.write(yaml_content)
        self.config_file.close()

        os.environ["OPENAI_API_KEY"] = "env-secret-key"
        os.environ["EGOSHELL_PROVIDER"] = "anthropic"
        os.environ["EGOSHELL_MODEL"] = "claude-3-5-sonnet"

        config = load_config(self.config_path)
        self.assertEqual(config.llm.provider, "anthropic")
        self.assertEqual(config.llm.model, "claude-3-5-sonnet")
        self.assertEqual(config.llm.openai_api_key, "env-secret-key")


if __name__ == "__main__":
    unittest.main()
