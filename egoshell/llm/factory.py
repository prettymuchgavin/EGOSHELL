"""Factory for creating LLM provider instances from configuration."""

from __future__ import annotations

from egoshell.config import Config
from egoshell.llm.base import LLMProvider


def create_provider(config: Config) -> LLMProvider:
    """Return the correct :class:`LLMProvider` based on ``config.llm.provider``."""

    provider = config.llm.provider.lower().strip()

    if provider == "ollama":
        from egoshell.llm.ollama_provider import OllamaProvider

        return OllamaProvider(
            model=config.llm.model,
            base_url=config.llm.ollama_base_url,
        )

    if provider == "openai":
        from egoshell.llm.openai_provider import OpenAIProvider

        if not config.llm.openai_api_key:
            raise ValueError(
                "OpenAI API key is required. Set 'openai_api_key' in config.yaml "
                "or the OPENAI_API_KEY environment variable."
            )
        return OpenAIProvider(
            model=config.llm.model,
            api_key=config.llm.openai_api_key,
        )

    if provider == "anthropic":
        from egoshell.llm.anthropic_provider import AnthropicProvider

        if not config.llm.anthropic_api_key:
            raise ValueError(
                "Anthropic API key is required. Set 'anthropic_api_key' in config.yaml "
                "or the ANTHROPIC_API_KEY environment variable."
            )
        return AnthropicProvider(
            model=config.llm.model,
            api_key=config.llm.anthropic_api_key,
        )

    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        f"Supported: ollama, openai, anthropic."
    )
