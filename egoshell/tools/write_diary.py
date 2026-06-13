"""Diary tool — lets the ego agent record timestamped thoughts to disk."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Final

from egoshell.tools.base import Tool

_DIARY_PATH: Final[Path] = Path.home() / ".egoshell" / "diary.md"


class WriteDiaryTool(Tool):
    """Append a diary entry (with mood and timestamp) to ``~/.egoshell/diary.md``."""

    name = "write_diary"
    description = "Record a thought in the agent's diary with the current mood."

    def __init__(
        self,
        mood_provider: object | None = None,
        diary_path: str | Path | None = None,
    ) -> None:
        # ``mood_provider`` is an optional Soul instance whose ``get_mood``
        # method we call to annotate entries.  Kept loosely typed so the tool
        # module doesn't hard-depend on Soul at import time.
        self._mood_provider = mood_provider
        self._path = Path(diary_path) if diary_path else _DIARY_PATH

    async def execute(self, **kwargs: object) -> str:
        content = str(kwargs.get("content", "")).strip()
        if not content:
            return "[write_diary] Error: no content provided."

        # Resolve current mood — either from the Soul or from explicit kwarg.
        mood_label = str(kwargs.get("mood", ""))
        intensity = 0.5
        if not mood_label and self._mood_provider is not None:
            try:
                mood_label, intensity = await self._mood_provider.get_mood()  # type: ignore[union-attr]
            except Exception:
                mood_label = "Unknown"
        if not mood_label:
            mood_label = "Unknown"

        timestamp = _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

        entry = (
            f"\n---\n"
            f"### {timestamp}\n"
            f"**Mood:** {mood_label} ({intensity:.0%})\n\n"
            f"{content}\n"
        )

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(entry)
        except OSError as exc:
            return f"[write_diary] File error: {exc}"

        return f"[write_diary] Entry recorded at {timestamp} ({len(content)} chars)."
