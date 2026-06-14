"""OpenAI LLM provider — uses the official async client."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI, OpenAIError

from egoshell.llm.base import LLMProvider, LLMError


class OpenAIProvider(LLMProvider):
    """Wraps the OpenAI Python SDK (async)."""

    def __init__(self, model: str, api_key: str) -> None:
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as exc:
            raise LLMError(f"OpenAI generation failed: {exc}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except OpenAIError as exc:
            raise LLMError(f"OpenAI streaming failed: {exc}") from exc

    async def close(self) -> None:
        await self._client.close()
