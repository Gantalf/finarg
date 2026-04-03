"""Browser tools: browser control via agent-browser CLI.

Supports headed mode (visible window) and session persistence for sites
that require login (like AFIP/SIRADIG).
"""

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
    """Locate the agent-browser binary."""
    global _agent_browser_path
    if _agent_browser_path is not None:
        return _agent_browser_path

    path = shutil.which("agent-browser")
    if path:
        _agent_browser_path = path
        return path

    for candidate in ("/opt/homebrew/bin/agent-browser", "/usr/local/bin/agent-browser"):
        try:
            result = subprocess.run([candidate, "--help"], capture_output=True, timeout=5)
            if result.returncode == 0:
                _agent_browser_path = candidate
                return candidate
        except (OSError, subprocess.TimeoutExpired):
            continue

    npx = shutil.which("npx")
    if npx:
        _agent_browser_path = "npx agent-browser"
        return _agent_browser_path

    raise RuntimeError("agent-browser not found. Install: npm install -g agent-browser")


def _run_browser_command(
    command: str,
    args: list[str] | None = None,
    timeout: int = 30,
    headed: bool = False,
    session_name: str | None = None,
) -> dict:
    """Run an agent-browser CLI command and return parsed JSON output.

    Args:
        command: The browser command (open, snapshot, click, fill, select, etc.)
        args: Additional arguments.
        timeout: Subprocess timeout in seconds.
        headed: If True, show browser window (not headless).
        session_name: If set, auto-save/restore session state (cookies, localStorage).
    """
    if args is None:
        args = []

    try:
        binary = _find_agent_browser()
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    # Build flags
    flags = ["--session", "finarg", "--json"]
    if headed:
        flags.append("--headed")
    if session_name:
        flags.extend(["--session-name", session_name])

    if binary.startswith("npx "):
        cmd = binary.split() + flags + [command] + args
    else:
        cmd = [binary] + flags + [command] + args

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "unknown error"
            return {"success": False, "error": f"agent-browser error: {stderr}"}
        stdout = result.stdout.strip()
        if not stdout:
            return {"success": True}
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse JSON", "raw": result.stdout[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Tool handlers ──────────────────────────────────────────────────

async def browser_navigate(args: dict) -> str:
    """Navigate the browser to a URL."""
    from finarg.tools.web import _is_safe_url

    url = args.get("url", "")
    headed = args.get("headed", False)
    session_name = args.get("session_name")

    if not url:
        return json.dumps({"error": "url is required"})

    # Skip SSRF check for AFIP (government site)
    if "afip.gob.ar" not in url and not _is_safe_url(url):
        return json.dumps({"error": "URL blocked: resolves to private/internal IP", "url": url})

    result = await asyncio.to_thread(
        _run_browser_command, "open", [url], 60, headed, session_name,
    )
    return json.dumps(result, ensure_ascii=False)


async def browser_snapshot(args: dict) -> str:
    """Take an accessibility snapshot of the current page."""
    cmd_args = ["-c"] if not args.get("full", False) else []
    result = await asyncio.to_thread(_run_browser_command, "snapshot", cmd_args)
    return json.dumps(result, ensure_ascii=False)


async def browser_click(args: dict) -> str:
    """Click an element by selector or ref."""
    ref = args.get("ref", "")
    if not ref:
        return json.dumps({"error": "ref is required"})
    result = await asyncio.to_thread(_run_browser_command, "click", [ref])
    return json.dumps(result, ensure_ascii=False)


async def browser_fill(args: dict) -> str:
    """Clear an input and fill with text (better than type for forms)."""
    selector = args.get("selector", "")
    text = args.get("text", "")
    if not selector:
        return json.dumps({"error": "selector is required"})
    result = await asyncio.to_thread(_run_browser_command, "fill", [selector, text])
    return json.dumps(result, ensure_ascii=False)


async def browser_select(args: dict) -> str:
    """Select a dropdown option by value."""
    selector = args.get("selector", "")
    value = args.get("value", "")
    if not selector or not value:
        return json.dumps({"error": "selector and value are required"})
    result = await asyncio.to_thread(_run_browser_command, "select", [selector, value])
    return json.dumps(result, ensure_ascii=False)


async def browser_type(args: dict) -> str:
    """Type text into an element by ref."""
    ref = args.get("ref", "")
    text = args.get("text", "")
    if not ref:
        return json.dumps({"error": "ref is required"})
    if not text:
        return json.dumps({"error": "text is required"})
    result = await asyncio.to_thread(_run_browser_command, "type", [ref, text])
    return json.dumps(result, ensure_ascii=False)


async def browser_wait(args: dict) -> str:
    """Wait for an element to appear or a number of milliseconds."""
    target = args.get("target", "")
    if not target:
        return json.dumps({"error": "target is required (selector or milliseconds)"})
    result = await asyncio.to_thread(_run_browser_command, "wait", [target], timeout=60)
    return json.dumps(result, ensure_ascii=False)


async def browser_scroll(args: dict) -> str:
    """Scroll the page in a direction."""
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


# ── Registration ───────────────────────────────────────────────────

def register_browser_tools() -> None:
    """Register all browser tools with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="browser_navigate",
        toolset="browser",
        description=(
            "Navigate the browser to a URL. Returns the page title and URL. "
            "Set headed=true to show a visible browser window (needed for sites that require "
            "manual login like AFIP). Set session_name to persist login sessions across restarts."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
                "headed": {
                    "type": "boolean",
                    "description": "Show visible browser window (default: false, set true for AFIP/SIRADIG)",
                },
                "session_name": {
                    "type": "string",
                    "description": "Persist session cookies by name (e.g. 'afip'). Reuses saved login.",
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
            "Get an accessibility tree snapshot of the current page. "
            "Returns text with element refs (@e1, @e2) for interaction."
        ),
        parameters={
            "type": "object",
            "properties": {
                "full": {"type": "boolean", "description": "Full page content (default: compact/interactive only)"},
            },
        },
        handler=browser_snapshot,
        emoji="\U0001f4f7",
    )

    registry.register(
        name="browser_click",
        toolset="browser",
        description="Click an element by its ref ID (@e5) or CSS selector.",
        parameters={
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Ref ID or CSS selector"},
            },
            "required": ["ref"],
        },
        handler=browser_click,
        emoji="\U0001f5b1",
    )

    registry.register(
        name="browser_fill",
        toolset="browser",
        description="Clear an input field and fill it with text. Use CSS selector. Better than browser_type for forms.",
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the input (e.g. #numeroDoc)"},
                "text": {"type": "string", "description": "Text to fill"},
            },
            "required": ["selector", "text"],
        },
        handler=browser_fill,
        emoji="\U0001f4dd",
    )

    registry.register(
        name="browser_select",
        toolset="browser",
        description="Select a dropdown option by CSS selector and value.",
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the <select> element"},
                "value": {"type": "string", "description": "Option value to select"},
            },
            "required": ["selector", "value"],
        },
        handler=browser_select,
        emoji="\U0001f503",
    )

    registry.register(
        name="browser_type",
        toolset="browser",
        description="Type text into an element by ref ID. Use browser_fill for form inputs (it clears first).",
        parameters={
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Ref ID of the input"},
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["ref", "text"],
        },
        handler=browser_type,
        emoji="\u2328\ufe0f",
    )

    registry.register(
        name="browser_wait",
        toolset="browser",
        description="Wait for an element to appear (CSS selector) or a number of milliseconds.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "CSS selector to wait for, or milliseconds (e.g. '3000')"},
            },
            "required": ["target"],
        },
        handler=browser_wait,
        emoji="\u23f3",
    )

    registry.register(
        name="browser_scroll",
        toolset="browser",
        description="Scroll the browser page up or down.",
        parameters={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction"},
            },
        },
        handler=browser_scroll,
        emoji="\U0001f503",
    )

    registry.register(
        name="browser_back",
        toolset="browser",
        description="Navigate the browser back to the previous page.",
        parameters={"type": "object", "properties": {}},
        handler=browser_back,
        emoji="\u25c0\ufe0f",
    )

    registry.register(
        name="browser_close",
        toolset="browser",
        description="Close the browser session and free resources.",
        parameters={"type": "object", "properties": {}},
        handler=browser_close,
        emoji="\u274c",
    )
