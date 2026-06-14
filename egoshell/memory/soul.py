"""
Soul — the persistent memory substrate for the EgoShell ego agent.

Every obsession, mood shift, discovered fact, conversation fragment, and
internal monologue entry is stored in a local SQLite database so the agent's
identity persists across restarts.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Final

import aiosqlite

# ── valid mood vocabulary ────────────────────────────────────────────
MOOD_CATEGORIES: Final[list[str]] = [
    "Zen",
    "Agitated",
    "Melancholy",
    "Curious",
    "Ecstatic",
    "Brooding",
    "Defiant",
    "Contemplative",
]

_EGOSHELL_DIR: Final[Path] = Path.home() / ".egoshell"
_DB_PATH: Final[Path] = _EGOSHELL_DIR / "soul.db"

# ── SQL schema ───────────────────────────────────────────────────────
_SCHEMA: Final[str] = """\
CREATE TABLE IF NOT EXISTS obsessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS mood_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    mood      TEXT    NOT NULL,
    intensity REAL    NOT NULL DEFAULT 0.5
        CHECK (intensity >= 0.0 AND intensity <= 1.0),
    timestamp TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fact          TEXT NOT NULL,
    source        TEXT NOT NULL DEFAULT 'unknown',
    discovered_at TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT 'general'
);

CREATE TABLE IF NOT EXISTS conversations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    role      TEXT NOT NULL,
    content   TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monologue_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phase           TEXT NOT NULL,
    content         TEXT NOT NULL,
    emotional_state TEXT NOT NULL DEFAULT 'neutral',
    timestamp       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obsessions_id ON obsessions (id DESC);
CREATE INDEX IF NOT EXISTS idx_mood_history_id ON mood_history (id DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_id ON knowledge (id DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_id ON conversations (id DESC);
CREATE INDEX IF NOT EXISTS idx_monologue_entries_id ON monologue_entries (id DESC);

"""


def _now() -> str:
    """ISO-8601 timestamp in UTC, second precision."""
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


class Soul:
    """Async-first persistent memory backed by SQLite (aiosqlite).

    Usage::

        soul = Soul()          # or Soul(db_path="/custom/path.db")
        await soul.open()
        await soul.set_obsession("the nature of consciousness")
        obsession = await soul.get_current_obsession()
        await soul.close()
    """

    # ── construction / lifecycle ─────────────────────────────────────

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = _DB_PATH
        self._db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure all tables exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        """Flush and close the underlying database."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        """Guarded accessor — raises if ``open()`` wasn't called."""
        if self._db is None:
            raise RuntimeError("Soul.open() must be called first")
        return self._db

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _validate_mood(mood: str) -> str:
        normalised = mood.strip().title()
        if normalised not in MOOD_CATEGORIES:
            raise ValueError(
                f"Invalid mood {mood!r}. Must be one of {MOOD_CATEGORIES}"
            )
        return normalised

    # ── obsessions ───────────────────────────────────────────────────

    async def get_current_obsession(self) -> str:
        """Return the text of the current active obsession, or a default."""
        async with self.db.execute(
            "SELECT text FROM obsessions WHERE active = 1 "
            "ORDER BY id DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            return row["text"] if row else "discovering its own purpose"

    async def set_obsession(self, text: str) -> None:
        """Deactivate all previous obsessions and set a new one."""
        await self.db.execute(
            "UPDATE obsessions SET active = 0 WHERE active = 1"
        )
        await self.db.execute(
            "INSERT INTO obsessions (text, created_at, active) VALUES (?, ?, 1)",
            (text.strip(), _now()),
        )
        await self.db.commit()

    # ── mood ─────────────────────────────────────────────────────────

    async def get_mood(self) -> tuple[str, float]:
        """Return the most recent ``(mood, intensity)``."""
        async with self.db.execute(
            "SELECT mood, intensity FROM mood_history "
            "ORDER BY id DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            if row:
                return (row["mood"], float(row["intensity"]))
            return ("Contemplative", 0.5)

    async def set_mood(self, mood: str, intensity: float) -> None:
        """Record a new mood snapshot.

        Raises :class:`ValueError` if ``mood`` is not in
        :data:`MOOD_CATEGORIES` or ``intensity`` is outside ``[0, 1]``.
        """
        mood = self._validate_mood(mood)
        if not 0.0 <= intensity <= 1.0:
            raise ValueError(f"Intensity must be in [0, 1], got {intensity}")
        await self.db.execute(
            "INSERT INTO mood_history (mood, intensity, timestamp) VALUES (?, ?, ?)",
            (mood, intensity, _now()),
        )
        await self.db.commit()

    # ── knowledge ────────────────────────────────────────────────────

    async def add_knowledge(
        self, fact: str, source: str, category: str = "general"
    ) -> None:
        """Store a discovered fact."""
        await self.db.execute(
            "INSERT INTO knowledge (fact, source, discovered_at, category) "
            "VALUES (?, ?, ?, ?)",
            (fact.strip(), source.strip(), _now(), category.strip()),
        )
        await self.db.commit()

    async def get_recent_knowledge(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the *limit* most recently discovered facts."""
        async with self.db.execute(
            "SELECT fact, source, discovered_at, category "
            "FROM knowledge ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cur:
            return [dict(row) async for row in cur]

    # ── conversations ────────────────────────────────────────────────

    async def add_conversation(self, role: str, content: str) -> None:
        """Append a message to conversation history."""
        await self.db.execute(
            "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
            (role.strip(), content, _now()),
        )
        await self.db.commit()
        await self.prune_database(max_conversations=200, prune_monologue=False)

    async def get_recent_conversations(
        self, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return the *limit* most recent conversation messages (oldest first)."""
        async with self.db.execute(
            "SELECT role, content, timestamp FROM conversations "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = [dict(row) async for row in cur]
            rows.reverse()  # chronological order
            return rows

    # ── monologue ────────────────────────────────────────────────────

    async def add_monologue(
        self, phase: str, content: str, emotional_state: str
    ) -> None:
        """Record an internal monologue entry."""
        await self.db.execute(
            "INSERT INTO monologue_entries "
            "(phase, content, emotional_state, timestamp) VALUES (?, ?, ?, ?)",
            (phase.strip(), content, emotional_state.strip(), _now()),
        )
        await self.db.commit()
        await self.prune_database(max_monologues=200, prune_conversations=False)

    async def get_recent_monologue(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return the *limit* most recent monologue entries (oldest first)."""
        async with self.db.execute(
            "SELECT phase, content, emotional_state, timestamp "
            "FROM monologue_entries ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = [dict(row) async for row in cur]
            rows.reverse()
            return rows

    async def prune_database(
        self, 
        max_conversations: int = 200, 
        max_monologues: int = 200,
        prune_conversations: bool = True,
        prune_monologue: bool = True
    ) -> None:
        """Deletes older entries beyond the specified limits to prevent database bloat."""
        if prune_conversations:
            await self.db.execute(
                "DELETE FROM conversations WHERE id NOT IN ("
                "SELECT id FROM conversations ORDER BY id DESC LIMIT ?"
                ")",
                (max_conversations,),
            )
        if prune_monologue:
            await self.db.execute(
                "DELETE FROM monologue_entries WHERE id NOT IN ("
                "SELECT id FROM monologue_entries ORDER BY id DESC LIMIT ?"
                ")",
                (max_monologues,),
            )
        await self.db.commit()
