"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class LLMProvider(ABC):
    """Provider-agnostic interface for large language model backends."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        """Return a complete response for the given conversation."""

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive."""

    async def close(self) -> None:
        """Release any resources held by the provider."""
