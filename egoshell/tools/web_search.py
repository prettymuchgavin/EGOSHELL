"""Web search tool using DuckDuckGo's HTML endpoint (no API key needed)."""

from __future__ import annotations

import re
from html import unescape
from typing import Final

import aiohttp

from egoshell.tools.base import Tool

_DDG_URL: Final[str] = "https://html.duckduckgo.com/html/"
_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_MAX_RESULTS: Final[int] = 5


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    return unescape(re.sub(r"<[^>]+>", "", text)).strip()


class WebSearchTool(Tool):
    """Search the web via DuckDuckGo and return the top results."""

    name = "web_search"
    description = "Search the web using DuckDuckGo and return the top 5 results."

    async def execute(self, **kwargs: object) -> str:
        query = str(kwargs.get("query", ""))
        if not query:
            return "[web_search] Error: no query provided."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    _DDG_URL,
                    params={"q": query},
                    headers={"User-Agent": _USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return f"[web_search] HTTP {resp.status} from DuckDuckGo."
                    body = await resp.text()
        except aiohttp.ClientError as exc:
            return f"[web_search] Network error: {exc}"
        except TimeoutError:
            return "[web_search] Request timed out."

        results = self._parse_results(body)
        if not results:
            return f"[web_search] No results found for: {query}"

        lines: list[str] = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            if r["snippet"]:
                lines.append(f"   {r['snippet']}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _parse_results(html_body: str) -> list[dict[str, str]]:
        """Extract title + snippet pairs from DuckDuckGo HTML."""
        results: list[dict[str, str]] = []

        # Each result lives in a div with class "result results_links ..."
        result_blocks = re.findall(
            r'<div[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*</div>',
            html_body,
            re.DOTALL,
        )

        for block in result_blocks[:_MAX_RESULTS]:
            title_match = re.search(
                r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL
            )
            snippet_match = re.search(
                r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                block,
                re.DOTALL,
            )
            if title_match:
                results.append(
                    {
                        "title": _strip_tags(title_match.group(1)),
                        "snippet": (
                            _strip_tags(snippet_match.group(1))
                            if snippet_match
                            else ""
                        ),
                    }
                )
        return results
