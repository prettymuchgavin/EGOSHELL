"""Ollama LLM provider — talks to a local Ollama instance via HTTP."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import aiohttp

from egoshell.llm.base import LLMProvider, LLMError


class OllamaProvider(LLMProvider):
    """Connects to Ollama's REST API."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=300)
            )
        return self._session

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        stream: bool = False,
    ) -> dict:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        return {
            "model": self._model,
            "messages": full_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        session = await self._get_session()
        payload = self._build_payload(messages, system_prompt, temperature, max_tokens)
        url = f"{self._base_url}/api/chat"

        try:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("message", {}).get("content", "")
        except aiohttp.ClientError as exc:
            raise LLMError(f"Ollama generation failed: {exc}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        session = await self._get_session()
        payload = self._build_payload(
            messages, system_prompt, temperature, max_tokens, stream=True
        )
        url = f"{self._base_url}/api/chat"

        try:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.content:
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if not decoded:
                        continue
                    try:
                        chunk = json.loads(decoded)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except aiohttp.ClientError as exc:
            raise LLMError(f"Ollama streaming failed: {exc}") from exc

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
