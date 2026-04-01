"""Web tools: search and read webpages."""

from __future__ import annotations

import asyncio
import json
import logging

log = logging.getLogger(__name__)


async def web_search(args: dict) -> str:
    """Search the web via DuckDuckGo."""
    from ddgs import DDGS

    query = args.get("query", "")
    max_results = min(args.get("max_results", 5), 10)

    if not query:
        return json.dumps({"error": "query is required"})

    def _search() -> list[dict]:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results

    results = await asyncio.to_thread(_search)

    # Simplify output for the LLM
    simplified = []
    for r in results:
        simplified.append({
            "title": r.get("title", ""),
            "url": r.get("href", r.get("link", "")),
            "snippet": r.get("body", r.get("snippet", "")),
        })

    return json.dumps({"query": query, "results": simplified}, ensure_ascii=False)


async def read_webpage(args: dict) -> str:
    """Fetch and extract text content from a URL."""
    import httpx

    url = args.get("url", "")
    if not url:
        return json.dumps({"error": "url is required"})

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Finarg/0.1)",
            })
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")

            if "json" in content_type:
                return json.dumps({
                    "url": url,
                    "content_type": "json",
                    "content": response.json(),
                }, ensure_ascii=False)

            html = response.text

            # Simple HTML to text extraction
            text = _html_to_text(html)

            # Truncate to avoid blowing up context
            max_chars = int(args.get("max_chars", 8000))
            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n[... truncated]"

            return json.dumps({
                "url": url,
                "content_type": "text",
                "content": text,
            }, ensure_ascii=False)

    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}", "url": url})
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


def _html_to_text(html: str) -> str:
    """Best-effort HTML to plain text conversion without extra dependencies."""
    import re

    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert common block elements to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&nbsp;", " ").replace("&#39;", "'")

    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def register_web_tools() -> None:
    """Register web tools with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="web_search",
        toolset="web",
        description=(
            "Search the web using DuckDuckGo. Returns titles, URLs, and snippets. "
            "Use this to research crypto projects, check news, find exchange rates, "
            "or look up any information not available through other tools."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'bitcoin price prediction 2026')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (1-10, default 5)",
                },
            },
            "required": ["query"],
        },
        handler=web_search,
        emoji="\U0001f50d",
    )

    registry.register(
        name="read_webpage",
        toolset="web",
        description=(
            "Fetch and read the text content of a webpage. Use this after web_search "
            "to read full articles, documentation, or any URL."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch and read",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return (default 8000)",
                },
            },
            "required": ["url"],
        },
        handler=read_webpage,
        emoji="\U0001f4c4",
    )
