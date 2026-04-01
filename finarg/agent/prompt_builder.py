"""System prompt assembly."""

from __future__ import annotations

import datetime
import time
from pathlib import Path

from finarg.constants import SOUL_FILE


def build_system_prompt(
    soul_path: Path | None = None,
    tools_summary: str = "",
    memory: str = "",
) -> str:
    """Build the full system prompt from SOUL.md, context, and memory.

    Parameters
    ----------
    soul_path:
        Path to the SOUL.md file.  Defaults to the repo-bundled one.
    tools_summary:
        Human-readable list of available tools and their descriptions.
    memory:
        Optional persistent memory/context to inject.
    """
    soul_path = soul_path or SOUL_FILE
    parts: list[str] = []

    # Soul / personality
    if soul_path.exists():
        parts.append(soul_path.read_text(encoding="utf-8").strip())

    # Date / time context
    now = datetime.datetime.now()
    tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
    parts.append(
        f"## Current context\n"
        f"- Date: {now.strftime('%Y-%m-%d')}\n"
        f"- Time: {now.strftime('%H:%M')}\n"
        f"- Timezone: {tz_name}"
    )

    # Tools
    if tools_summary:
        parts.append(f"## Available tools\n{tools_summary}")

    # Memory
    if memory:
        parts.append(f"## Memory\n{memory}")

    return "\n\n".join(parts)
