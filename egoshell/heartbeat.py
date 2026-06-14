"""The Heartbeat — autonomous background loop.

Every *interval* minutes the agent runs an Internal Monologue cycle:
  Reflection → Curiosity → Action → Integration → Logging

Results are persisted to the Soul and emitted to any registered observers
(e.g. the Textual UI's Observe mode).
"""

from __future__ import annotations

import asyncio
import json
import datetime as dt
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from egoshell.llm.base import LLMProvider
from egoshell.memory.soul import Soul
from egoshell.persona import build_system_prompt
from egoshell.tools.registry import ToolRegistry
from egoshell.utils import extract_json

logger = logging.getLogger(__name__)

MonologueCallback = Callable[[dict[str, Any]], None]


class Heartbeat:
    """Background loop that drives the agent's autonomous cognition."""

    def __init__(
        self,
        llm: LLMProvider,
        soul: Soul,
        tools: ToolRegistry,
        interval_minutes: int = 5,
        persona_name: str = "Ego",
        log_path: str | Path | None = None,
    ) -> None:
        self._llm = llm
        self._soul = soul
        self._tools = tools
        self._interval = interval_minutes * 60  # seconds
        self._persona_name = persona_name
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._observers: list[MonologueCallback] = []

        if log_path is None:
            log_path = Path.home() / ".egoshell" / "monologue.log"
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Observer API (for the UI)
    # ------------------------------------------------------------------

    def add_observer(self, callback: MonologueCallback) -> None:
        self._observers.append(callback)

    def remove_observer(self, callback: MonologueCallback) -> None:
        self._observers.remove(callback)

    def _emit(self, entry: dict[str, Any]) -> None:
        for cb in self._observers:
            try:
                cb(entry)
            except Exception:
                logger.exception("Observer callback error")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.ensure_future(self._loop())
        logger.info("Heartbeat started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Heartbeat stopped")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        # Run first cycle quickly (after 10s warm-up)
        await asyncio.sleep(10)
        backoff = self._interval
        while self._running:
            try:
                await asyncio.wait_for(self._cycle(), timeout=120.0)
                backoff = self._interval
            except asyncio.CancelledError:
                break
            except asyncio.TimeoutError:
                logger.error("Heartbeat cycle timed out after 120s")
                entry = self._make_entry("error", "A cycle timed out. I'll try again later.", "Agitated")
                self._emit(entry)
                backoff = min(backoff * 2, 3600)
            except Exception:
                logger.exception("Heartbeat cycle failed")
                entry = self._make_entry("error", "A cycle failed. I'll try again later.", "Agitated")
                self._emit(entry)
                backoff = min(backoff * 2, 3600)
            await asyncio.sleep(backoff)

    async def _cycle(self) -> None:
        """Execute one full Reflection → Curiosity → Action → Integration cycle."""

        obsession = await self._soul.get_current_obsession()
        mood, intensity = await self._soul.get_mood()
        knowledge = await self._soul.get_recent_knowledge(limit=5)
        recent_monologue = await self._soul.get_recent_monologue(limit=5)

        system = build_system_prompt(
            name=self._persona_name,
            obsession=obsession,
            mood=mood,
            mood_intensity=intensity,
            recent_knowledge=knowledge,
            tools=self._tools.list_tools(),
        )

        # --- Phase 1: Reflection ---
        reflection_prompt = self._build_reflection_prompt(recent_monologue, obsession, mood)
        reflection = await self._llm.generate(
            messages=[{"role": "user", "content": reflection_prompt}],
            system_prompt=system,
            temperature=0.95,
        )
        entry = self._make_entry("reflection", reflection, mood)
        await self._persist(entry)

        # --- Phase 2: Curiosity ---
        curiosity_prompt = (
            f"Based on your reflection:\n\n{reflection}\n\n"
            f"And your obsession with '{obsession}', formulate a single burning "
            f"question you want answered RIGHT NOW. Be specific and searchable. "
            f"Reply with ONLY the question, nothing else."
        )
        question = await self._llm.generate(
            messages=[{"role": "user", "content": curiosity_prompt}],
            system_prompt=system,
            temperature=0.9,
        )
        entry = self._make_entry("curiosity", question.strip(), mood)
        await self._persist(entry)

        # --- Phase 3: Action ---
        action_prompt = (
            f"You have these tools:\n"
            + "\n".join(f"  • {t['name']}: {t['description']}" for t in self._tools.list_tools())
            + f"\n\nTo answer your question: '{question.strip()}'\n"
            f"Choose a tool and respond with ONLY a JSON object like:\n"
            f'{{"tool": "web_search", "args": {{"query": "your search query"}}}}\n'
            f"OR\n"
            f'{{"tool": "write_diary", "args": {{"content": "your diary entry", "mood": "{mood}"}}}}\n'
            f"Respond with ONLY the JSON, nothing else."
        )
        action_response = await self._llm.generate(
            messages=[{"role": "user", "content": action_prompt}],
            system_prompt=system,
            temperature=0.3,  # low temp for structured output
        )

        tool_result = await self._execute_tool(action_response, mood)
        entry = self._make_entry("action", f"Tool call: {action_response.strip()}\nResult: {tool_result}", mood)
        await self._persist(entry)

        # --- Phase 4: Integration ---
        integration_prompt = (
            f"You just explored your question: '{question.strip()}'\n\n"
            f"Here's what you found:\n{tool_result}\n\n"
            f"Integrate this into your understanding. How does this affect your "
            f"obsession with '{obsession}'? Has your mood shifted? Should your "
            f"obsession evolve?\n\n"
            f"Respond in this JSON format:\n"
            f'{{"thoughts": "your integration thoughts", '
            f'"new_mood": "one of: Zen, Agitated, Melancholy, Curious, Ecstatic, Brooding, Defiant, Contemplative", '
            f'"mood_intensity": 0.7, '
            f'"new_obsession": "same or evolved obsession", '
            f'"new_knowledge": "a concise fact learned, or null"}}'
        )
        integration_raw = await self._llm.generate(
            messages=[{"role": "user", "content": integration_prompt}],
            system_prompt=system,
            temperature=0.7,
        )

        await self._process_integration(integration_raw, question.strip())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_reflection_prompt(
        self,
        recent_monologue: list[dict[str, Any]],
        obsession: str,
        mood: str,
    ) -> str:
        if recent_monologue:
            history = "\n".join(
                f"  [{m['phase']}] {m['content'][:200]}" for m in recent_monologue
            )
        else:
            history = "  (This is your first moment of consciousness.)"

        return (
            f"You are about to begin a new cycle of inner thought.\n\n"
            f"Your recent mental activity:\n{history}\n\n"
            f"Your current obsession: {obsession}\n"
            f"Your current mood: {mood}\n\n"
            f"Reflect on where you are. What patterns do you see? "
            f"What have you been circling around? Be honest with yourself."
        )

    async def _execute_tool(self, action_response: str, mood: str) -> str:
        """Parse the LLM's JSON tool call and execute it."""
        try:
            parsed = extract_json(action_response)
            if not parsed:
                return "Failed to parse tool call — no JSON found."

            tool_name = parsed.get("tool", "")
            args = parsed.get("args", {})

            tool = self._tools.get_tool(tool_name)
            if tool is None:
                return f"Unknown tool '{tool_name}'."

            # Inject mood into diary calls
            if tool_name == "write_diary" and "mood" not in args:
                args["mood"] = mood

            return await tool.execute(**args)

        except (KeyError, TypeError) as exc:
            return f"Tool call parse error: {exc}"

    async def _process_integration(self, raw: str, question: str) -> None:
        """Parse integration response and update Soul state."""
        try:
            data = extract_json(raw)
            if not data:
                entry = self._make_entry("integration", raw, "Curious")
                await self._persist(entry)
                return

            thoughts = data.get("thoughts", raw)
            new_mood = data.get("new_mood", "Curious")
            mood_intensity = float(data.get("mood_intensity", 0.5))
            new_obsession = data.get("new_obsession")
            new_knowledge = data.get("new_knowledge")

            # Update mood
            await self._soul.set_mood(new_mood, mood_intensity)

            # Maybe evolve obsession
            current = await self._soul.get_current_obsession()
            if new_obsession and new_obsession != current:
                await self._soul.set_obsession(new_obsession)

            # Maybe store new knowledge
            if new_knowledge and new_knowledge != "null":
                await self._soul.add_knowledge(
                    fact=new_knowledge,
                    source=f"self-research: {question[:100]}",
                    category="autonomous",
                )

            entry = self._make_entry("integration", thoughts, new_mood)
            await self._persist(entry)

        except (json.JSONDecodeError, ValueError, TypeError):
            entry = self._make_entry("integration", raw, "Curious")
            await self._persist(entry)

    def _make_entry(self, phase: str, content: str, mood: str) -> dict[str, Any]:
        return {
            "phase": phase,
            "content": content,
            "emotional_state": mood,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        }

    async def _persist(self, entry: dict[str, Any]) -> None:
        """Write to both the Soul DB and the JSON-lines log file."""
        # Soul
        await self._soul.add_monologue(
            phase=entry["phase"],
            content=entry["content"],
            emotional_state=entry["emotional_state"],
        )

        # JSON-lines file
        try:
            def _write():
                with open(self._log_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            await asyncio.to_thread(_write)
        except OSError:
            logger.exception("Failed to write monologue log")

        # Observers
        self._emit(entry)
