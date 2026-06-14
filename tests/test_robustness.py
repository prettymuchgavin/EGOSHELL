"""Robustness and error handling tests."""

import pytest
import asyncio
import aiohttp
from unittest.mock import patch, AsyncMock, MagicMock
from egoshell.llm.base import LLMError
from egoshell.llm.ollama_provider import OllamaProvider
from egoshell.llm.openai_provider import OpenAIProvider
from egoshell.llm.anthropic_provider import AnthropicProvider
from openai import OpenAIError
import anthropic

def test_ollama_provider_error():
    async def run():
        provider = OllamaProvider(model="test-model")
        # Use MagicMock for standard call behavior
        mock_session = MagicMock()
        mock_session.post.side_effect = aiohttp.ClientError("connection refused")
        
        with patch.object(provider, "_get_session", return_value=mock_session):
            with pytest.raises(LLMError) as exc_info:
                await provider.generate(messages=[], system_prompt="test")
            assert "Ollama generation failed" in str(exc_info.value)

            with pytest.raises(LLMError) as exc_info:
                async for _ in provider.stream(messages=[], system_prompt="test"):
                    pass
            assert "Ollama streaming failed" in str(exc_info.value)
            
    asyncio.run(run())

def test_openai_provider_error():
    async def run():
        provider = OpenAIProvider(model="test-model", api_key="test-key")
        provider._client = AsyncMock()
        provider._client.chat.completions.create.side_effect = OpenAIError("rate limit exceeded")

        with pytest.raises(LLMError) as exc_info:
            await provider.generate(messages=[], system_prompt="test")
        assert "OpenAI generation failed" in str(exc_info.value)

        with pytest.raises(LLMError) as exc_info:
            async for _ in provider.stream(messages=[], system_prompt="test"):
                pass
        assert "OpenAI streaming failed" in str(exc_info.value)

    asyncio.run(run())

def test_anthropic_provider_error():
    async def run():
        provider = AnthropicProvider(model="test-model", api_key="test-key")
        provider._client = AsyncMock()
        
        # Correctly instantiate anthropic.APIError
        mock_request = MagicMock()
        err = anthropic.APIError(message="API error", request=mock_request, body=None)
        provider._client.messages.create.side_effect = err
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(messages=[], system_prompt="test")
        assert "Anthropic generation failed" in str(exc_info.value)

    asyncio.run(run())
