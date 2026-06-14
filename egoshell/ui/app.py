"""
EgoShell Terminal UI — Cyberpunk-themed Textual application.

Dual-mode interface:
  • **Chat Mode**   — converse with the ego agent
  • **Observe Mode** — watch the agent's autonomous inner monologue in real-time
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from rich.markup import escape
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from egoshell.agent import Agent
from egoshell.config import load_config

# ═══════════════════════════════════════════════════════════════════════
#  Colour palette — cyberpunk dark theme
# ═══════════════════════════════════════════════════════════════════════
CYAN = "#00e5ff"
MAGENTA = "#ff00e5"
AMBER = "#ffab00"
DIM = "#555555"
BG_DARK = "#0a0a0f"
BG_PANEL = "#111118"
USER_COLOR = CYAN
AGENT_COLOR = MAGENTA
PHASE_COLORS: dict[str, str] = {
    "reflection": "#7c4dff",
    "curiosity": CYAN,
    "action": AMBER,
    "integration": MAGENTA,
    "error": "#ff1744",
}

# ═══════════════════════════════════════════════════════════════════════
#  Custom widgets
# ═══════════════════════════════════════════════════════════════════════


class ChatMessage(Vertical):
    """A single chat bubble with support for collapsible thought processes."""

    DEFAULT_CSS = """
    ChatMessage {
        padding: 0 1;
        margin: 0 0 1 0;
        layout: vertical;
    }
    .chat-header {
        margin: 0;
        padding: 0;
    }
    .chat-body {
        margin: 0;
        padding: 0;
    }
    Collapsible {
        border: none;
        margin: 0;
        padding: 0;
        background: transparent;
    }
    CollapsibleTitle {
        background: transparent;
        color: #7c4dff;
        border: none;
        height: 1;
        min-height: 1;
        padding: 0 1;
    }
    CollapsibleTitle:hover {
        background: rgba(124, 77, 255, 0.1);
        color: #9d7cff;
    }
    Contents {
        border: none;
        background: transparent;
        padding: 0 0 0 2;
    }
    """

    def __init__(self, role: str, content: str = "", **kw: Any) -> None:
        super().__init__(**kw)
        self.role = role
        self._raw_content = content

    def compose(self) -> ComposeResult:
        colour = USER_COLOR if self.role == "user" else AGENT_COLOR
        label = "◈ you" if self.role == "user" else "◉ ego"
        if self.role == "system":
            colour = AMBER
            label = "⚙ sys"

        self.header_static = Static(f"[bold {colour}]{label}[/]", classes="chat-header")
        yield self.header_static

        self.collapsible = Collapsible(
            Static("", id="thinking-content"),
            title="Thought Process",
            collapsed=True,
            id="thinking-collapsible"
        )
        self.collapsible.display = False
        yield self.collapsible

        self.body_static = Static("", classes="chat-body")
        yield self.body_static

    def on_mount(self) -> None:
        self.update_content(self._raw_content)

    def set_error(self) -> None:
        self.header_static.update("[bold red]◉ ego[/]")

    def update_content(self, content: str) -> None:
        self._raw_content = content
        
        # Parse `<think>` and `</think>` tags
        think_content = ""
        response_content = content
        
        start_idx = content.find("<think>")
        if start_idx != -1:
            end_idx = content.find("</think>", start_idx)
            if end_idx != -1:
                think_content = content[start_idx + len("<think>"):end_idx].strip()
                response_content = (content[:start_idx] + content[end_idx + len("</think>"):].strip())
            else:
                think_content = content[start_idx + len("<think>"):].strip()
                response_content = content[:start_idx].strip()
        else:
            think_content = ""
            response_content = content.strip()

        # Update thinking process if present
        if think_content:
            try:
                thinking_static = self.collapsible.query_one("#thinking-content", Static)
                thinking_static.update(escape(think_content))
            except Exception:
                pass
            self.collapsible.display = True
        else:
            self.collapsible.display = False

        # Update response body
        self.body_static.update(escape(response_content))


class MonologueEntry(Static):
    """A single monologue log line."""

    DEFAULT_CSS = """
    MonologueEntry {
        padding: 0 1;
        margin: 0 0 0 0;
    }
    """

    def __init__(self, entry: dict[str, Any], **kw: Any) -> None:
        super().__init__(**kw)
        self._entry = entry

    def compose(self) -> ComposeResult:
        e = self._entry
        ts_raw = e.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts_raw)
            ts = dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            ts = ts_raw[:8] if ts_raw else "??:??:??"

        phase = e.get("phase", "???")
        colour = PHASE_COLORS.get(phase, DIM)
        mood = e.get("emotional_state", "")
        mood_tag = f"  [{AMBER}]♫ {mood}[/]" if mood else ""
        content = e.get("content", "")
        if len(content) > 400:
            truncated = content[:400] + "... [truncated]"
        else:
            truncated = content

        yield Static(
            f"[{DIM}]{ts}[/]  [{colour} bold]{phase}[/]{mood_tag}\n"
            f"[italic]{escape(truncated)}[/]",
        )


class MoodBar(Static):
    """Header widget displaying current mood and obsession."""

    DEFAULT_CSS = """
    MoodBar {
        dock: top;
        height: 3;
        padding: 0 2;
        background: #111118;
        border-bottom: solid #222233;
    }
    """

    mood: reactive[str] = reactive("contemplative")
    obsession: reactive[str] = reactive("the nature of consciousness")

    def render(self) -> str:
        return (
            f"[bold {MAGENTA}]🎭 {self.mood}[/]"
            f"  │  "
            f"[bold {CYAN}]🌀 {self.obsession}[/]"
        )


# ═══════════════════════════════════════════════════════════════════════
#  Main application
# ═══════════════════════════════════════════════════════════════════════


class EgoShellApp(App[None]):
    """The EgoShell terminal UI."""

    TITLE = "EgoShell"
    SUB_TITLE = "autonomous ego agent"

    CSS = """
    Screen {
        background: #0a0a0f;
    }

    Header {
        background: #111118;
        color: #00e5ff;
        text-style: bold;
    }

    Footer {
        background: #111118;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }

    /* ── Chat ────────────────────────────────────── */

    #chat-scroll {
        height: 1fr;
        padding: 1 2;
        background: #0a0a0f;
        scrollbar-color: #333344;
        scrollbar-color-hover: #00e5ff;
    }

    .chat-bubble {
        padding: 1 2;
        margin: 0;
    }

    #chat-input {
        dock: bottom;
        margin: 0 1;
        padding: 0 1;
        border: solid #333344;
        background: #15151f;
        color: #e0e0e0;
    }

    #chat-input:focus {
        border: solid #00e5ff;
    }

    /* ── Observe ─────────────────────────────────── */

    #observe-scroll {
        height: 1fr;
        padding: 1 2;
        background: #0a0a0f;
        scrollbar-color: #333344;
        scrollbar-color-hover: #ff00e5;
    }

    #observe-empty {
        color: #555555;
        text-align: center;
        padding: 4;
    }

    /* ── Mood bar ────────────────────────────────── */

    MoodBar {
        dock: top;
        height: 3;
        padding: 0 2;
        background: #111118;
        border-bottom: solid #222233;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
        Binding("tab", "toggle_mode", "Switch Mode", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=True),
    ]

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self._agent = Agent()  # uses load_config() internally
        self._streaming = False

    # ── compose ──────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield MoodBar()
        with TabbedContent(id="modes"):
            with TabPane("◈ Chat", id="tab-chat"):
                yield VerticalScroll(id="chat-scroll")
                yield Input(
                    placeholder="speak…",
                    id="chat-input",
                )
            with TabPane("◉ Observe", id="tab-observe"):
                yield VerticalScroll(
                    Static(
                        f"[{DIM}]Waiting for the first heartbeat…[/]",
                        id="observe-empty",
                    ),
                    id="observe-scroll",
                )
        yield Footer()

    # ── lifecycle ────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        self.sub_title = f"Web Console: http://{self._agent.config.web.host}:{self._agent.config.web.port}"
        self._start_agent()

    @work(thread=False)
    async def _start_agent(self) -> None:
        try:
            await self._agent.start()
        except Exception as exc:
            self._append_chat("system", f"⚠ Agent failed to start: {exc}")
            return

        # Register monologue observer *after* start so heartbeat exists.
        self._agent.heartbeat.add_observer(self._on_monologue_entry)

        # Sync mood bar once soul is ready.
        await self._sync_mood_bar()

    async def on_unmount(self) -> None:
        await self._agent.stop()

    # ── actions ──────────────────────────────────────────────────────

    def action_toggle_mode(self) -> None:
        tabs = self.query_one(TabbedContent)
        current = tabs.active
        if current == "tab-chat":
            tabs.active = "tab-observe"
        else:
            tabs.active = "tab-chat"

    def action_clear_chat(self) -> None:
        try:
            scroll = self.query_one("#chat-scroll", VerticalScroll)
            scroll.remove_children()
        except NoMatches:
            pass

    # ── chat input ───────────────────────────────────────────────────

    @on(Input.Submitted, "#chat-input")
    async def _handle_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text or self._streaming:
            return
        event.input.value = ""
        self._append_chat("user", text)
        self._stream_response(text)

    @work(thread=False)
    async def _stream_response(self, user_text: str) -> None:
        self._streaming = True
        chunks: list[str] = []
        widget = self._append_chat("assistant", "…")

        try:
            async for chunk in self._agent.chat(user_text):
                chunks.append(chunk)
                full = "".join(chunks)
                widget.update_content(full)
                # Auto-scroll.
                try:
                    scroll = self.query_one("#chat-scroll", VerticalScroll)
                    scroll.scroll_end(animate=False)
                except NoMatches:
                    pass
        except Exception as exc:
            widget.set_error()
            widget.update_content(f"⚠ Error: {exc}")

        self._streaming = False
        await self._sync_mood_bar()

    # ── monologue callback ───────────────────────────────────────────

    def _on_monologue_entry(self, entry: dict[str, Any]) -> None:
        """Called synchronously from the heartbeat loop for each monologue event.

        We use ``call_from_thread``-safe posting via Textual's message system.
        Since we're already on the event loop (heartbeat runs as an asyncio
        task), we can schedule a UI update directly.
        """
        # Post a Textual worker to update the UI safely.
        self.call_later(self._apply_monologue_entry, entry)

    async def _apply_monologue_entry(self, entry: dict[str, Any]) -> None:
        """Actually mount the monologue widget — runs on Textual's event loop."""
        try:
            scroll = self.query_one("#observe-scroll", VerticalScroll)
            # Remove the placeholder on first real entry.
            try:
                placeholder = self.query_one("#observe-empty", Static)
                placeholder.remove()
            except NoMatches:
                pass

            await scroll.mount(MonologueEntry(entry))
            scroll.scroll_end(animate=False)

            # Prune oldest monologue entries to prevent DOM bloat
            if len(scroll.children) > 100:
                oldest = list(scroll.children)[:len(scroll.children) - 100]
                for child in oldest:
                    child.remove()
        except NoMatches:
            pass

        # Update mood bar if this entry carries mood info.
        mood = entry.get("emotional_state", "")
        if mood:
            try:
                bar = self.query_one(MoodBar)
                bar.mood = mood
            except NoMatches:
                pass

    # ── helpers ──────────────────────────────────────────────────────

    def _append_chat(self, role: str, content: str) -> ChatMessage:
        """Add a message widget to the chat scroll and return it."""
        widget = ChatMessage(role=role, content=content)
        try:
            scroll = self.query_one("#chat-scroll", VerticalScroll)
            scroll.mount(widget)
            scroll.scroll_end(animate=False)

            # Prune oldest chat messages to prevent DOM bloat
            if len(scroll.children) > 100:
                oldest = list(scroll.children)[:len(scroll.children) - 100]
                for child in oldest:
                    child.remove()
        except NoMatches:
            pass
        return widget

    async def _sync_mood_bar(self) -> None:
        """Pull current mood/obsession from the Soul and update the bar."""
        try:
            soul = self._agent.soul
            mood, _intensity = await soul.get_mood()
            obsession = await soul.get_current_obsession()
            bar = self.query_one(MoodBar)
            bar.mood = mood
            bar.obsession = obsession
        except Exception as e:
            import logging
            logging.getLogger("egoshell.ui").exception("Failed to sync mood bar")
            try:
                bar = self.query_one(MoodBar)
                bar.mood = "Error"
                bar.obsession = f"Database sync failed: {e}"
            except Exception:
                pass
