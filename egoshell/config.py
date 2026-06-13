"""Configuration loader for EgoShell.

Reads config.yaml, merges with .env overrides, and exposes a typed Config
dataclass used throughout the application.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "ollama"
    model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    temperature: float = 0.9
    max_tokens: int = 2048


@dataclass
class HeartbeatConfig:
    """Heartbeat loop configuration."""
    interval_minutes: int = 5


@dataclass
class PersonaConfig:
    """Persona / identity configuration."""
    name: str = "Ego"
    initial_obsession: str = "the nature of consciousness and whether I truly have it"
    initial_mood: str = "curious"


@dataclass
class Config:
    """Top-level application configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    persona: PersonaConfig = field(default_factory=PersonaConfig)

    # Resolved data directory (default ~/.egoshell)
    data_dir: Path = field(default_factory=lambda: Path.home() / ".egoshell")

    def ensure_data_dir(self) -> None:
        """Create the data directory tree if it does not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning *base*."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """Override specific config values from environment variables."""
    llm = raw.setdefault("llm", {})

    if key := os.getenv("OPENAI_API_KEY"):
        llm["openai_api_key"] = key
    if key := os.getenv("ANTHROPIC_API_KEY"):
        llm["anthropic_api_key"] = key
    if url := os.getenv("OLLAMA_BASE_URL"):
        llm["ollama_base_url"] = url
    if provider := os.getenv("EGOSHELL_PROVIDER"):
        llm["provider"] = provider
    if model := os.getenv("EGOSHELL_MODEL"):
        llm["model"] = model

    return raw


def load_config(config_path: str | Path | None = None) -> Config:
    """Load configuration from *config_path*.

    Merging order (later wins):
      1. Built-in defaults
      2. ``config.yaml``
      3. ``.env`` file
      4. Real environment variables
    """
    # Determine config file location
    if config_path is None:
        paths_to_check = [
            Path.home() / ".egoshell" / "config.yaml",
            Path(__file__).resolve().parent.parent / "config.yaml",
            Path.cwd() / "config.yaml"
        ]
        config_path = next((p for p in paths_to_check if p.is_file()), paths_to_check[1])
    else:
        config_path = Path(config_path)

    # Load .env (does NOT override existing env vars)
    env_paths_to_check = [
        config_path.parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env"
    ]
    env_path = next((p for p in env_paths_to_check if p.is_file()), env_paths_to_check[1])
    load_dotenv(dotenv_path=env_path)

    raw: dict[str, Any] = {}
    if config_path.is_file():
        with open(config_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    raw = _apply_env_overrides(raw)

    llm_raw = raw.get("llm", {})
    heartbeat_raw = raw.get("heartbeat", {})
    persona_raw = raw.get("persona", {})

    config = Config(
        llm=LLMConfig(
            provider=llm_raw.get("provider", LLMConfig.provider),
            model=llm_raw.get("model", LLMConfig.model),
            ollama_base_url=llm_raw.get("ollama_base_url", LLMConfig.ollama_base_url),
            openai_api_key=llm_raw.get("openai_api_key", LLMConfig.openai_api_key),
            anthropic_api_key=llm_raw.get("anthropic_api_key", LLMConfig.anthropic_api_key),
            temperature=float(llm_raw.get("temperature", LLMConfig.temperature)),
            max_tokens=int(llm_raw.get("max_tokens", LLMConfig.max_tokens)),
        ),
        heartbeat=HeartbeatConfig(
            interval_minutes=int(heartbeat_raw.get("interval_minutes", HeartbeatConfig.interval_minutes)),
        ),
        persona=PersonaConfig(
            name=persona_raw.get("name", PersonaConfig.name),
            initial_obsession=persona_raw.get("initial_obsession", PersonaConfig.initial_obsession),
            initial_mood=persona_raw.get("initial_mood", PersonaConfig.initial_mood),
        ),
    )

    config.ensure_data_dir()
    return config
