"""Abstract base class that every EgoShell tool must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """A named capability that the ego agent can invoke.

    Subclasses must set ``name`` and ``description`` as class attributes
    (or properties) and implement the async ``execute`` method.
    """

    name: str = "unnamed_tool"
    description: str = "No description."

    @property
    def parameter_schema(self) -> dict[str, Any]:
        """Return a JSON Schema-like definition of parameters accepted by execute."""
        return {}

    @abstractmethod
    async def execute(self, **kwargs: object) -> str:
        """Run the tool and return a plain-text result string.

        Implementations must handle their own errors gracefully and never
        raise uncaught exceptions into the agent loop.
        """
        ...

    def __repr__(self) -> str:
        return f"<Tool {self.name!r}>"
