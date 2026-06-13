"""Agent — the top-level coordinator that wires everything together."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from egoshell.config import Config, load_config
from egoshell.heartbeat import Heartbeat
from egoshell.llm.base import LLMProvider
from egoshell.llm.factory import create_provider
from egoshell.memory.soul import Soul
from egoshell.persona import build_system_prompt
from egoshell.tools.registry import ToolRegistry


class Agent:
    """Top-level EgoShell agent.

    Owns the LLM provider, Soul memory, tool registry, and heartbeat loop.
    Exposes a streaming ``chat()`` method for the interactive UI.
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self._llm: LLMProvider | None = None
        self._soul: Soul | None = None
        self._tools: ToolRegistry | None = None
        self._heartbeat: Heartbeat | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialise all subsystems and start the heartbeat."""
        self._llm = create_provider(self.config)

        self._soul = Soul()
        await self._soul.open()

        # Seed initial obsession & mood if DB is fresh
        async with self._soul.db.execute("SELECT COUNT(*) as cnt FROM obsessions") as cur:
            row = await cur.fetchone()
            has_obsessions = row["cnt"] > 0 if row else False

        if not has_obsessions:
            await self._soul.set_obsession(self.config.persona.initial_obsession)
            await self._soul.set_mood(
                self.config.persona.initial_mood.capitalize(), 0.6
            )

        self._tools = ToolRegistry.default()

        self._heartbeat = Heartbeat(
            llm=self._llm,
            soul=self._soul,
            tools=self._tools,
            interval_minutes=self.config.heartbeat.interval_minutes,
            persona_name=self.config.persona.name,
        )
        self._heartbeat.start()

    async def stop(self) -> None:
        """Gracefully shut everything down."""
        if self._heartbeat:
            await self._heartbeat.stop()
        if self._llm:
            await self._llm.close()
        if self._soul:
            await self._soul.close()

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def soul(self) -> Soul:
        assert self._soul is not None, "Agent.start() must be called first"
        return self._soul

    @property
    def heartbeat(self) -> Heartbeat:
        assert self._heartbeat is not None, "Agent.start() must be called first"
        return self._heartbeat

    @property
    def llm(self) -> LLMProvider:
        assert self._llm is not None, "Agent.start() must be called first"
        return self._llm

    @property
    def tools(self) -> ToolRegistry:
        assert self._tools is not None, "Agent.start() must be called first"
        return self._tools

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(self, user_message: str) -> AsyncGenerator[str, None]:
        """Stream the agent's response to *user_message*.

        Yields tokens as they arrive so the UI can render incrementally.
        """
        soul = self.soul

        # Persist user message
        await soul.add_conversation("user", user_message)

        # Build context
        obsession = await soul.get_current_obsession()
        mood, intensity = await soul.get_mood()
        knowledge = await soul.get_recent_knowledge(limit=5)
        history = await soul.get_recent_conversations(limit=20)

        system = build_system_prompt(
            name=self.config.persona.name,
            obsession=obsession,
            mood=mood,
            mood_intensity=intensity,
            recent_knowledge=knowledge,
            tools=self.tools.list_tools(),
        )

        # Convert history to messages
        messages = [
            {"role": h["role"], "content": h["content"]}
            for h in history
        ]

        # Stream response
        full_response: list[str] = []
        async for token in self.llm.stream(
            messages=messages,
            system_prompt=system,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        ):
            full_response.append(token)
            yield token

        # Persist assistant response
        complete = "".join(full_response)
        await soul.add_conversation("assistant", complete)

        # Check if the agent tried to use a tool
        await self._maybe_handle_tool(complete)

    async def _maybe_handle_tool(self, response: str) -> None:
        """If the response contains a tool call JSON, execute it."""
        try:
            json_match = re.search(r'\{"tool":\s*".*?\}', response, re.DOTALL)
            if not json_match:
                return
            data = json.loads(json_match.group())
            tool_name = data.get("tool", "")
            args = data.get("args", {})
            tool = self.tools.get_tool(tool_name)
            if tool:
                mood, _ = await self.soul.get_mood()
                if tool_name == "write_diary" and "mood" not in args:
                    args["mood"] = mood
                result = await tool.execute(**args)
                await self.soul.add_conversation(
                    "system", f"[Tool {tool_name} result]: {result}"
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
