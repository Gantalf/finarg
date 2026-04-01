"""Terminal tool: execute shell commands locally."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess

log = logging.getLogger(__name__)

MAX_OUTPUT_CHARS = 50_000


async def terminal(args: dict) -> str:
    """Execute a shell command locally and return JSON with output and exit code."""
    command = args.get("command")
    if not command:
        return json.dumps({"error": "command is required", "exit_code": -1})

    timeout: int = args.get("timeout", 180)
    workdir: str | None = args.get("workdir")

    def _run() -> dict:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True,
                timeout=timeout,
                cwd=workdir,
            )
            output = (result.stdout or "") + (result.stderr or "")
            if len(output) > MAX_OUTPUT_CHARS:
                output = output[:MAX_OUTPUT_CHARS] + "\n\n[... truncated]"
            return {"output": output, "exit_code": result.returncode}
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "exit_code": -1}
        except Exception as exc:
            return {"error": str(exc), "exit_code": -1}

    result = await asyncio.to_thread(_run)
    return json.dumps(result, ensure_ascii=False)


TERMINAL_DESCRIPTION = (
    "Execute shell commands on the local machine. "
    "Filesystem persists between calls.\n\n"
    "Do NOT use cat/head/tail to read files \u2014 use read_file instead.\n"
    "Reserve terminal for: builds, installs, git, processes, scripts, "
    "network, package managers, and anything that needs a shell.\n\n"
    "Set a generous timeout for long builds (default 180s). "
    "Use 'workdir' for per-command working directory."
)


def register_terminal_tools() -> None:
    """Register the terminal tool with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="terminal",
        toolset="terminal",
        description=TERMINAL_DESCRIPTION,
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds before the command is killed (default 180)",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory for the command (optional)",
                },
            },
            "required": ["command"],
        },
        handler=terminal,
        emoji="\U0001f4bb",
    )
