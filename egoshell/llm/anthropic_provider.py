"""Anthropic LLM provider — uses the official async client."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import anthropic

from egoshell.llm.base import LLMProvider, LLMError


class AnthropicProvider(LLMProvider):
    """Wraps the Anthropic Python SDK (async)."""

    def __init__(self, model: str, api_key: str) -> None:
        self._model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.content[0].text if response.content else ""
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic generation failed: {exc}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        try:
            async with self._client.messages.stream(
                model=self._model,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic streaming failed: {exc}") from exc

    async def close(self) -> None:
        await self._client.close()
