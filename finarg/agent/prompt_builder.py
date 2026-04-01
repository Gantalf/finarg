"""System prompt assembly — follows Hermes agent/prompt_builder.py patterns."""

from __future__ import annotations

import datetime
import logging
import time
from pathlib import Path

import yaml

from finarg.constants import SKILLS_DIR, SOUL_FILE

log = logging.getLogger(__name__)


def build_system_prompt(
    soul_path: Path | None = None,
    tools_summary: str = "",
    memory: str = "",
) -> str:
    """Build the full system prompt from SOUL.md, skills, context, and memory."""
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

    # Skills index
    skills_prompt = build_skills_prompt()
    if skills_prompt:
        parts.append(skills_prompt)

    # Context files (discover .finarg.md, AGENTS.md in cwd)
    context = _load_context_files()
    if context:
        parts.append(context)

    # Memory
    if memory:
        parts.append(f"## Memory\n{memory}")

    return "\n\n".join(parts)


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
                skills.append({
                    "name": frontmatter.get("name", skill_md.parent.name),
                    "description": frontmatter.get("description", ""),
                })
        except Exception:
            log.debug("Failed to parse skill: %s", skill_md, exc_info=True)

    if not skills:
        return ""

    lines = ["## Available skills", "Use `skill_view` to load full instructions for any skill.", ""]
    for s in skills:
        lines.append(f"- **{s['name']}**: {s['description']}")

    return "\n".join(lines)


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
                    # Cap at 20000 chars like Hermes
                    if len(content) > 20000:
                        content = content[:20000] + "\n\n[... truncated]"
                    context_parts.append(f"## Context from {filename}\n{content}")
            except Exception:
                log.debug("Failed to load context file: %s", path, exc_info=True)

    return "\n\n".join(context_parts)
