"""Read-only skill tools: list and view.

Provides progressive disclosure for skills stored under ``~/.finarg/skills/``.

- ``skills_list`` returns lightweight metadata (name + description) for every
  installed skill (tier 1).
- ``skill_view`` loads the full SKILL.md content or a specific supporting file
  (tier 2-3).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

from finarg.constants import SKILLS_DIR
from finarg.tools.registry import registry

log = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from a SKILL.md string.

    Returns the parsed dict (may be empty on failure).
    """
    if not text.startswith("---"):
        return {}
    end = re.search(r"\n---\s*\n", text[3:])
    if not end:
        return {}
    try:
        parsed = yaml.safe_load(text[3 : end.start() + 3])
        return parsed if isinstance(parsed, dict) else {}
    except yaml.YAMLError:
        return {}


def _find_all_skills() -> list[dict[str, Any]]:
    """Scan ``SKILLS_DIR`` for every skill and return minimal metadata."""
    results: list[dict[str, Any]] = []
    if not SKILLS_DIR.exists():
        return results

    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        skill_dir = skill_md.parent
        name = skill_dir.name

        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue

        fm = _parse_frontmatter(text)
        entry: dict[str, Any] = {
            "name": fm.get("name", name),
            "description": str(fm.get("description", "")),
            "path": str(skill_dir),
        }

        # Check prerequisites (env_vars)
        prereqs = fm.get("prerequisites", {})
        if isinstance(prereqs, dict):
            env_vars = prereqs.get("env_vars", [])
            if env_vars:
                missing = [v for v in env_vars if not os.getenv(v)]
                if missing:
                    entry["missing_env_vars"] = missing

        results.append(entry)

    results.sort(key=lambda s: s["name"])
    return results


# ── Tool handlers ────────────────────────────────────────────────────────────

async def skills_list(args: dict[str, Any]) -> str:
    """List all available skills with minimal metadata."""
    try:
        if not SKILLS_DIR.exists():
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            return json.dumps(
                {
                    "success": True,
                    "skills": [],
                    "message": "No skills found. Skills directory created at ~/.finarg/skills/",
                },
                ensure_ascii=False,
            )

        all_skills = _find_all_skills()

        if not all_skills:
            return json.dumps(
                {
                    "success": True,
                    "skills": [],
                    "message": "No skills found in ~/.finarg/skills/.",
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "success": True,
                "skills": all_skills,
                "count": len(all_skills),
                "hint": "Use skill_view(name) to see full content and linked files.",
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        return json.dumps(
            {"success": False, "error": str(exc)},
            ensure_ascii=False,
        )


async def skill_view(args: dict[str, Any]) -> str:
    """View the full content of a skill's SKILL.md or a supporting file."""
    name: str = args.get("name", "")
    file_path: str | None = args.get("file_path")

    if not name:
        return json.dumps(
            {"success": False, "error": "name is required."},
            ensure_ascii=False,
        )

    try:
        if not SKILLS_DIR.exists():
            return json.dumps(
                {"success": False, "error": "Skills directory does not exist yet."},
                ensure_ascii=False,
            )

        # Search for the skill by directory name
        skill_dir: Path | None = None
        for found_md in SKILLS_DIR.rglob("SKILL.md"):
            if found_md.parent.name == name:
                skill_dir = found_md.parent
                break

        # Also try a direct path
        if skill_dir is None:
            direct = SKILLS_DIR / name
            if direct.is_dir() and (direct / "SKILL.md").exists():
                skill_dir = direct

        if skill_dir is None:
            available = [s["name"] for s in _find_all_skills()[:20]]
            return json.dumps(
                {
                    "success": False,
                    "error": f"Skill '{name}' not found.",
                    "available_skills": available,
                    "hint": "Use skills_list to see all available skills.",
                },
                ensure_ascii=False,
            )

        # Determine which file to read
        if file_path:
            target = skill_dir / file_path
        else:
            target = skill_dir / "SKILL.md"

        if not target.exists():
            # List available files for the user
            available_files: list[str] = ["SKILL.md"]
            for subdir in ("references", "templates", "scripts", "assets"):
                d = skill_dir / subdir
                if d.exists():
                    for f in d.rglob("*"):
                        if f.is_file():
                            available_files.append(str(f.relative_to(skill_dir)))
            return json.dumps(
                {
                    "success": False,
                    "error": f"File '{file_path}' not found in skill '{name}'.",
                    "available_files": available_files,
                },
                ensure_ascii=False,
            )

        content = target.read_text(encoding="utf-8")

        result: dict[str, Any] = {
            "success": True,
            "name": name,
            "content": content,
            "path": str(target),
        }

        # If reading the main SKILL.md, list supporting files
        if not file_path:
            supporting: list[str] = []
            for subdir in ("references", "templates", "scripts", "assets"):
                d = skill_dir / subdir
                if d.exists():
                    for f in d.rglob("*"):
                        if f.is_file():
                            supporting.append(str(f.relative_to(skill_dir)))
            if supporting:
                result["supporting_files"] = supporting

        return json.dumps(result, ensure_ascii=False)

    except Exception as exc:
        return json.dumps(
            {"success": False, "error": str(exc)},
            ensure_ascii=False,
        )


# ── Tool registration ────────────────────────────────────────────────────────

def register_skills_tools() -> None:
    """Register ``skills_list`` and ``skill_view`` in the ``skills`` toolset."""
    registry.register(
        name="skills_list",
        toolset="skills",
        description=(
            "List all available skills with name and description. "
            "Returns lightweight metadata for progressive disclosure. "
            "Use skill_view(name) to load full content."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=skills_list,
        emoji="\U0001f4da",  # 📚
    )

    registry.register(
        name="skill_view",
        toolset="skills",
        description=(
            "View the full content of a skill's SKILL.md or a specific "
            "supporting file (references, templates, scripts, assets). "
            "Use skills_list first to discover available skills."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the skill to view.",
                },
                "file_path": {
                    "type": "string",
                    "description": (
                        "Optional path to a supporting file within the skill "
                        "(e.g., 'references/api.md'). Omit to read SKILL.md."
                    ),
                },
            },
            "required": ["name"],
        },
        handler=skill_view,
        emoji="\U0001f4d6",  # 📖
    )
