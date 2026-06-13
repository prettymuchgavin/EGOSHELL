"""Tool registry — manages available tools for the ego agent."""

from __future__ import annotations

from typing import Iterator

from egoshell.tools.base import Tool
from egoshell.tools.web_search import WebSearchTool
from egoshell.tools.write_diary import WriteDiaryTool


class ToolRegistry:
    """A thin container that stores :class:`Tool` instances by name.

    Instantiate with ``ToolRegistry.default()`` to pre-register the
    built-in ``web_search`` and ``write_diary`` tools, or create an empty
    registry with ``ToolRegistry()`` and register tools manually.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    # ── factory ──────────────────────────────────────────────────────

    @classmethod
    def default(cls, *, mood_provider: object | None = None) -> "ToolRegistry":
        """Create a registry pre-loaded with the built-in tools.

        Parameters
        ----------
        mood_provider:
            Optional Soul (or duck-typed equivalent) passed to
            :class:`WriteDiaryTool` for mood annotation.
        """
        registry = cls()
        registry.register(WebSearchTool())
        registry.register(WriteDiaryTool(mood_provider=mood_provider))
        return registry

    # ── public API ───────────────────────────────────────────────────

    def register(self, tool: Tool) -> None:
        """Register a tool.  Overwrites any existing tool with the same name."""
        if not isinstance(tool, Tool):
            raise TypeError(
                f"Expected a Tool instance, got {type(tool).__name__}"
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Look up a tool by name, returning ``None`` if not found."""
        return self._tools.get(name)

    # Keep backward compat with code that used `get_tool`.
    get_tool = get

    def __getitem__(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"No tool registered with name {name!r}") from None

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)

    def list_tools(self) -> list[dict[str, str]]:
        """Return a serialisable list of ``{"name": …, "description": …}``."""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def __repr__(self) -> str:
        names = ", ".join(self._tools)
        return f"<ToolRegistry tools=[{names}]>"
