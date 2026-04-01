"""Browser tools: headless browser control via agent-browser CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess

log = logging.getLogger(__name__)

# Cached path to the agent-browser binary
_agent_browser_path: str | None = None


def _find_agent_browser() -> str:
    """Locate the agent-browser binary.

    Search order: PATH, /opt/homebrew/bin, /usr/local/bin, npx fallback.
    Raises RuntimeError if not found.
    """
    global _agent_browser_path
    if _agent_browser_path is not None:
        return _agent_browser_path

    # Direct binary lookup
    path = shutil.which("agent-browser")
    if path:
        _agent_browser_path = path
        return path

    for candidate in ("/opt/homebrew/bin/agent-browser", "/usr/local/bin/agent-browser"):
        try:
            result = subprocess.run(
                [candidate, "--help"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                _agent_browser_path = candidate
                return candidate
        except (OSError, subprocess.TimeoutExpired):
            continue

    # npx fallback
    npx = shutil.which("npx")
    if npx:
        _agent_browser_path = "npx agent-browser"
        return _agent_browser_path

    raise RuntimeError(
        "agent-browser not found. Install it via npm: npm install -g agent-browser"
    )


def _run_browser_command(command: str, args: list[str] | None = None, timeout: int = 30) -> dict:
    """Run an agent-browser CLI command and return parsed JSON output.

    Args:
        command: The browser command (open, snapshot, click, type, scroll, back, close).
        args: Additional arguments for the command.
        timeout: Subprocess timeout in seconds.

    Returns:
        Parsed JSON dict from agent-browser stdout, or an error dict.
    """
    if args is None:
        args = []

    try:
        binary = _find_agent_browser()
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    # Build the command list
    if binary.startswith("npx "):
        # npx fallback: split into ["npx", "agent-browser", ...]
        cmd = binary.split() + ["--session", "finarg", "--json", command] + args
    else:
        cmd = [binary, "--session", "finarg", "--json", command] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "unknown error"
            return {"success": False, "error": f"agent-browser exited with code {result.returncode}: {stderr}"}

        stdout = result.stdout.strip()
        if not stdout:
            return {"success": True}

        return json.loads(stdout)

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"agent-browser timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse agent-browser JSON output", "raw": result.stdout[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def browser_navigate(args: dict) -> str:
    """Navigate the browser to a URL."""
    from finarg.tools.web import _is_safe_url

    url = args.get("url", "")
    if not url:
        return json.dumps({"error": "url is required"})

    if not _is_safe_url(url):
        return json.dumps({"error": "URL blocked: resolves to private/internal IP", "url": url})

    result = await asyncio.to_thread(_run_browser_command, "open", [url])
    return json.dumps(result, ensure_ascii=False)


async def browser_snapshot(args: dict) -> str:
    """Take an accessibility snapshot of the current page."""
    cmd_args = ["-c"] if not args.get("full", False) else []
    result = await asyncio.to_thread(_run_browser_command, "snapshot", cmd_args)
    return json.dumps(result, ensure_ascii=False)


async def browser_click(args: dict) -> str:
    """Click an element by its accessibility ref."""
    ref = args.get("ref", "")
    if not ref:
        return json.dumps({"error": "ref is required"})

    result = await asyncio.to_thread(_run_browser_command, "click", [ref])
    return json.dumps(result, ensure_ascii=False)


async def browser_type(args: dict) -> str:
    """Type text into an element by its accessibility ref."""
    ref = args.get("ref", "")
    text = args.get("text", "")
    if not ref:
        return json.dumps({"error": "ref is required"})
    if not text:
        return json.dumps({"error": "text is required"})

    result = await asyncio.to_thread(_run_browser_command, "type", [ref, text])
    return json.dumps(result, ensure_ascii=False)


async def browser_scroll(args: dict) -> str:
    """Scroll the page in a direction (up/down)."""
    direction = args.get("direction", "down")
    result = await asyncio.to_thread(_run_browser_command, "scroll", [direction])
    return json.dumps(result, ensure_ascii=False)


async def browser_back(args: dict) -> str:
    """Navigate the browser back."""
    result = await asyncio.to_thread(_run_browser_command, "back")
    return json.dumps(result, ensure_ascii=False)


async def browser_close(args: dict) -> str:
    """Close the browser session."""
    result = await asyncio.to_thread(_run_browser_command, "close")
    return json.dumps(result, ensure_ascii=False)


def register_browser_tools() -> None:
    """Register all browser tools with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="browser_navigate",
        toolset="browser",
        description=(
            "Navigate the headless browser to a URL. Returns the page title and URL. "
            "Use this to interact with web pages that require JavaScript or dynamic content."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to navigate to",
                },
            },
            "required": ["url"],
        },
        handler=browser_navigate,
        emoji="\U0001f310",
    )

    registry.register(
        name="browser_snapshot",
        toolset="browser",
        description=(
            "Take an accessibility tree snapshot of the current browser page. "
            "Returns a text representation of the page content with ref IDs for interaction."
        ),
        parameters={
            "type": "object",
            "properties": {
                "full": {
                    "type": "boolean",
                    "description": "If true, return full page snapshot. Default is compact.",
                },
            },
        },
        handler=browser_snapshot,
        emoji="\U0001f4f7",
    )

    registry.register(
        name="browser_click",
        toolset="browser",
        description="Click an element on the page by its accessibility ref ID from a snapshot.",
        parameters={
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Accessibility ref ID of the element to click",
                },
            },
            "required": ["ref"],
        },
        handler=browser_click,
        emoji="\U0001f5b1",
    )

    registry.register(
        name="browser_type",
        toolset="browser",
        description="Type text into an input element identified by its accessibility ref ID.",
        parameters={
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Accessibility ref ID of the input element",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type into the element",
                },
            },
            "required": ["ref", "text"],
        },
        handler=browser_type,
        emoji="\u2328\ufe0f",
    )

    registry.register(
        name="browser_scroll",
        toolset="browser",
        description="Scroll the browser page up or down.",
        parameters={
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "Scroll direction (default: down)",
                },
            },
        },
        handler=browser_scroll,
        emoji="\U0001f503",
    )

    registry.register(
        name="browser_back",
        toolset="browser",
        description="Navigate the browser back to the previous page.",
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=browser_back,
        emoji="\u25c0\ufe0f",
    )

    registry.register(
        name="browser_close",
        toolset="browser",
        description="Close the browser session and free resources.",
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=browser_close,
        emoji="\u274c",
    )
