"""Web tools: search and read webpages."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import socket
from urllib.parse import urlparse

log = logging.getLogger(__name__)


def _is_safe_url(url: str) -> bool:
    """Return True if the URL's resolved IP is not in a private/internal range.

    Blocks: 10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x, 0.0.0.0,
    and metadata.google.internal.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False

        # Block known metadata hostnames
        if hostname.lower() in ("metadata.google.internal",):
            return False

        # Resolve DNS and check all IPs
        addrinfos = socket.getaddrinfo(hostname, None)
        for family, _type, _proto, _canonname, sockaddr in addrinfos:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False

        return True
    except Exception:
        return False


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
    """Fetch a URL and convert HTML to clean markdown."""
    import html2text
    import httpx

    url = args.get("url", "")
    if not url:
        return json.dumps({"error": "url is required"})

    if not _is_safe_url(url):
        return json.dumps({"error": "URL blocked: resolves to private/internal IP", "url": url})

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

            # Convert HTML to markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0  # no wrapping
            text = h.handle(html).strip()

            # Truncate to avoid blowing up context
            max_chars = int(args.get("max_chars", 12000))
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
            "Fetch and read the content of a webpage as clean markdown. "
            "Use this after web_search to read full articles, documentation, or any URL."
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
                    "description": "Max characters to return (default 12000)",
                },
            },
            "required": ["url"],
        },
        handler=read_webpage,
        emoji="\U0001f4c4",
    )
