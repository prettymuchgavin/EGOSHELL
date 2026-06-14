"""Web search tool using DuckDuckGo's HTML endpoint (no API key needed)."""

from __future__ import annotations

import urllib.parse
from html.parser import HTMLParser
from typing import Final, Any

import aiohttp

from egoshell.tools.base import Tool

_DDG_URL: Final[str] = "https://html.duckduckgo.com/html/"
_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_MAX_RESULTS: Final[int] = 5


class DDGHTMLParser(HTMLParser):
    """HTML parser to extract search result titles, snippets, and clean URLs."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self.current_result: dict[str, str] | None = None
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs if v is not None}
        cls = attrs_dict.get("class", "")
        classes = cls.split()

        # Each result block is typically container inside "result"
        if tag == "div" and "result" in classes:
            self.current_result = {"title": "", "snippet": "", "url": ""}
            self.results.append(self.current_result)

        if self.current_result is not None:
            if tag == "a" and "result__a" in cls:
                self.in_title = True
                if "href" in attrs_dict:
                    url = attrs_dict["href"]
                    # Unquote and clean DuckDuckGo redirect URLs if present
                    if "uddg=" in url:
                        try:
                            parsed = urllib.parse.urlparse(url)
                            queries = urllib.parse.parse_qs(parsed.query)
                            if "uddg" in queries:
                                url = queries["uddg"][0]
                        except Exception:
                            pass
                    if url.startswith("//"):
                        url = "https:" + url
                    self.current_result["url"] = url
            elif tag == "a" and "result__snippet" in cls:
                self.in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if self.in_title and tag == "a":
            self.in_title = False
        if self.in_snippet and tag == "a":
            self.in_snippet = False

    def handle_data(self, data: str) -> None:
        if self.current_result is not None:
            if self.in_title:
                self.current_result["title"] += data
            elif self.in_snippet:
                self.current_result["snippet"] += data


class WebSearchTool(Tool):
    """Search the web via DuckDuckGo and return the top results."""

    name = "web_search"
    description = "Search the web using DuckDuckGo and return the top 5 results."

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    @property
    def parameter_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to send to DuckDuckGo."
                }
            },
            "required": ["query"]
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    async def execute(self, **kwargs: object) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return "[web_search] Error: no query provided."

        try:
            session = await self._get_session()
            async with session.get(
                _DDG_URL,
                params={"q": query},
                headers={"User-Agent": _USER_AGENT},
            ) as resp:
                if resp.status != 200:
                    return f"[web_search] HTTP {resp.status} from DuckDuckGo."
                body = await resp.text()
        except aiohttp.ClientError as exc:
            return f"[web_search] Network error: {exc}"
        except TimeoutError:
            return "[web_search] Request timed out."

        parser = DDGHTMLParser()
        parser.feed(body)
        results = parser.results[:_MAX_RESULTS]

        if not results:
            return f"[web_search] No results found for: {query}"

        lines: list[str] = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            title = r["title"].strip()
            snippet = r["snippet"].strip()
            url = r["url"].strip()
            lines.append(f"{i}. {title}")
            if url:
                lines.append(f"   Link: {url}")
            if snippet:
                lines.append(f"   {snippet}")
            lines.append("")
        return "\n".join(lines).strip()

    async def close(self) -> None:
        """Close the shared ClientSession."""
        if self._session and not self._session.closed:
            await self._session.close()
