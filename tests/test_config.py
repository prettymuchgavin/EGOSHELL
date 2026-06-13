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


    def test_think_defaults_and_yaml(self):
        # Default behavior (think=True)
        self.config_file.write("")
        self.config_file.close()
        config = load_config(self.config_path)
        self.assertTrue(config.llm.think)

        # YAML configuration override
        self.setUp()  # Reset temp file
        yaml_content = """
llm:
  think: false
"""
        self.config_file.write(yaml_content)
        self.config_file.close()
        config = load_config(self.config_path)
        self.assertFalse(config.llm.think)

    def test_web_config_defaults_and_yaml(self):
        # Default behavior (web.enabled=True, host="127.0.0.1", port=5050)
        self.config_file.write("")
        self.config_file.close()
        config = load_config(self.config_path)
        self.assertTrue(config.web.enabled)
        self.assertEqual(config.web.host, "127.0.0.1")
        self.assertEqual(config.web.port, 5050)

        # YAML configuration override
        self.setUp()
        yaml_content = """
web:
  enabled: false
  host: 0.0.0.0
  port: 8080
"""
        self.config_file.write(yaml_content)
        self.config_file.close()
        config = load_config(self.config_path)
        self.assertFalse(config.web.enabled)
        self.assertEqual(config.web.host, "0.0.0.0")
        self.assertEqual(config.web.port, 8080)

    def test_web_env_overrides(self):
        self.config_file.write("")
        self.config_file.close()

        os.environ["EGOSHELL_WEB_ENABLED"] = "false"
        os.environ["EGOSHELL_WEB_HOST"] = "1.2.3.4"
        os.environ["EGOSHELL_WEB_PORT"] = "9999"

        config = load_config(self.config_path)
        self.assertFalse(config.web.enabled)
        self.assertEqual(config.web.host, "1.2.3.4")
        self.assertEqual(config.web.port, 9999)

        # Clean up env
        del os.environ["EGOSHELL_WEB_ENABLED"]
        del os.environ["EGOSHELL_WEB_HOST"]
        del os.environ["EGOSHELL_WEB_PORT"]


if __name__ == "__main__":
    unittest.main()
