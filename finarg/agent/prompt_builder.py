"""System prompt assembly — follows Hermes agent/prompt_builder.py patterns.

Technical guidance lives here as constants (like Hermes), not in SOUL.md.
SOUL.md is personality only.
"""

from __future__ import annotations

import datetime
import logging
import os
import time
from pathlib import Path

import yaml

from finarg.constants import SKILLS_DIR, SOUL_FILE

log = logging.getLogger(__name__)

# ── Guidance constants (like Hermes prompt_builder.py) ──────────────

TOOL_GUIDANCE = (
    "## How to use your tools\n"
    "- You have direct API access to Ripio and BCRA. ALWAYS use your API tools first.\n"
    "- Use `terminal` to execute shell commands and scripts.\n"
    "- Use `read_file`, `write_file`, `patch`, `search_files` for file operations "
    "— do NOT use terminal for cat/head/tail/grep/sed.\n"
    "- Use `web_search` and `read_webpage` to research APIs and documentation.\n"
    "- Use the browser tools only for interactive web tasks that other tools cannot handle."
)

SKILLS_GUIDANCE = (
    "## Skills guidance\n"
    "After completing a complex task (5+ tool calls), fixing a tricky error, "
    "or discovering a non-trivial workflow, save the approach as a "
    "skill with skill_manage so you can reuse it next time.\n"
    "When using a skill and finding it outdated, incomplete, or wrong, "
    "patch it immediately with skill_manage(action='patch') — don't wait to be asked. "
    "Skills that aren't maintained become liabilities."
)

SCRIPT_EXECUTION_GUIDANCE = (
    "## Executing scripts\n"
    "When running Python scripts via `terminal`, reuse the authenticated API clients "
    "that already exist in the codebase. Don't re-implement authentication from scratch.\n"
    "Credentials and API keys are pre-loaded as environment variables in the terminal. "
    "Access them with `os.getenv()`.\n"
    "Example pattern for calling any authenticated API endpoint:\n"
    "```python\n"
    'python3 -c "\n'
    "import asyncio, json\n"
    "from finarg.api.ripio_trade import get_trade_client\n"
    "async def main():\n"
    "    client = get_trade_client()\n"
    "    result = await client._get('/some/endpoint')\n"
    "    print(json.dumps(result, indent=2))\n"
    "asyncio.run(main())\n"
    '"\n'
    "```\n"
    "The `get_trade_client()` handles all authentication (HMAC signing, headers, etc.). "
    "Use `client._get(path)` for GET and `client._post(path, json={...})` for POST.\n"
    "If credentials are missing, tell the user to configure them with `finarg config set KEY=VALUE`."
)

MEMORY_GUIDANCE = (
    "## Memory guidance\n"
    "You have persistent memory across sessions. Save durable facts using the memory "
    "tool: user preferences, environment details, tool quirks, and stable conventions.\n"
    "Memory is injected into every turn, so keep it compact and focused on facts that "
    "will still matter later.\n"
    "Prioritize what reduces future user steering — the most valuable memory is one "
    "that prevents the user from having to correct or remind you again.\n"
    "Do NOT save task progress, session outcomes, or temporary state to memory."
)

TOOL_USE_ENFORCEMENT = (
    "## Tool-use enforcement\n"
    "You MUST use your tools to take action — do not describe what you would do "
    "or plan to do without actually doing it. When you say you will perform an "
    "action, you MUST immediately make the corresponding tool call in the same "
    "response. Never end your turn with a promise of future action — execute it now.\n"
    "Every response should either (a) contain tool calls that make progress, or "
    "(b) deliver a final result to the user."
)


# ── Prompt assembly ────────────────────────────────────────────────

def build_system_prompt(
    soul_path: Path | None = None,
    tools_summary: str = "",
    memory_store: Any = None,
) -> str:
    """Build the full system prompt from SOUL.md, guidance, skills, context, and memory.

    Args:
        memory_store: Optional MemoryStore instance. If provided, its frozen
            snapshot is injected into the prompt.
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

    # Technical guidance (constant sections)
    parts.append(TOOL_GUIDANCE)
    parts.append(SKILLS_GUIDANCE)
    parts.append(MEMORY_GUIDANCE)
    parts.append(SCRIPT_EXECUTION_GUIDANCE)
    parts.append(TOOL_USE_ENFORCEMENT)

    # Tools
    if tools_summary:
        parts.append(f"## Available tools\n{tools_summary}")

    # Skills index
    skills_prompt = build_skills_prompt()
    if skills_prompt:
        parts.append(skills_prompt)

    # Context files (discover .finarg.md, AGENTS.md in cwd)
    context = _load_context_files()
    if context:
        parts.append(context)

    # Persistent memory (frozen snapshot from session start)
    if memory_store is not None:
        mem_block = memory_store.format_for_system_prompt("memory")
        if mem_block:
            parts.append(mem_block)
        user_block = memory_store.format_for_system_prompt("user")
        if user_block:
            parts.append(user_block)

    return "\n\n".join(parts)


# ── Skills prompt ──────────────────────────────────────────────────

def build_skills_prompt() -> str:
    """Scan ~/.finarg/skills/ for SKILL.md files and build a compact index.

    Follows Hermes pattern: progressive disclosure — only name + description
    are injected into the prompt. Full content loaded via skill_view tool.
    """
    if not SKILLS_DIR.is_dir():
        return ""

    skills: list[dict[str, str]] = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            frontmatter = _parse_frontmatter(skill_md)
            if frontmatter:
                entry = {
                    "name": frontmatter.get("name", skill_md.parent.name),
                    "description": frontmatter.get("description", ""),
                }
                prereqs = frontmatter.get("prerequisites", {})
                if isinstance(prereqs, dict):
                    env_vars = prereqs.get("env_vars", [])
                    missing = [v for v in env_vars if not os.getenv(v)]
                    if missing:
                        entry["missing"] = ", ".join(missing)
                skills.append(entry)
        except Exception:
            log.debug("Failed to parse skill: %s", skill_md, exc_info=True)

    if not skills:
        return ""

    lines = ["## Available skills", "Use `skill_view` to load full instructions for any skill.", ""]
    for s in skills:
        line = f"- **{s['name']}**: {s['description']}"
        if "missing" in s:
            line += f" ⚠️ Missing: {s['missing']} (configure with `finarg config set`)"
        lines.append(line)

    return "\n".join(lines)


# ── Helpers ────────────────────────────────────────────────────────

def _parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a SKILL.md file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    try:
        return yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None


def _load_context_files() -> str:
    """Discover and load context files from the current working directory.

    Follows Hermes pattern: looks for .finarg.md, AGENTS.md, CLAUDE.md.
    """
    cwd = Path.cwd()
    context_parts: list[str] = []

    for filename in [".finarg.md", "AGENTS.md", "CLAUDE.md", ".cursorrules"]:
        path = cwd / filename
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    if len(content) > 20000:
                        content = content[:20000] + "\n\n[... truncated]"
                    context_parts.append(f"## Context from {filename}\n{content}")
            except Exception:
                log.debug("Failed to load context file: %s", path, exc_info=True)

    return "\n\n".join(context_parts)
