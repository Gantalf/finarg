"""Skill Manager Tool -- Agent-Managed Skill Creation & Editing.

Allows the agent to create, update, and delete skills, turning successful
approaches into reusable procedural knowledge.  New skills are created in
``~/.finarg/skills/``.  Existing skills can be modified or deleted wherever
they live.

Actions:
  create      -- Create a new skill (SKILL.md + directory structure)
  edit        -- Replace the SKILL.md content of a skill (full rewrite)
  patch       -- Targeted find-and-replace within SKILL.md
  delete      -- Remove a skill entirely
  write_file  -- Add/overwrite a supporting file (reference, template, script, asset)
  remove_file -- Remove a supporting file from a skill

Directory layout::

    ~/.finarg/skills/
    ├── my-skill/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── templates/
    │   ├── scripts/
    │   └── assets/
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

from finarg.constants import SKILLS_DIR
from finarg.tools.registry import registry

log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024

VALID_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# Subdirectories allowed for write_file / remove_file
ALLOWED_SUBDIRS = {"references", "templates", "scripts", "assets"}


# ── Validation helpers ───────────────────────────────────────────────────────

def _validate_name(name: str) -> str | None:
    """Validate a skill name.  Returns an error message or ``None`` if valid."""
    if not name:
        return "Skill name is required."
    if len(name) > MAX_NAME_LENGTH:
        return f"Skill name exceeds {MAX_NAME_LENGTH} characters."
    if not VALID_NAME_RE.match(name):
        return (
            f"Invalid skill name '{name}'. Use lowercase letters, numbers, "
            f"hyphens, dots, and underscores. Must start with a letter or digit."
        )
    return None


def _validate_frontmatter(content: str) -> str | None:
    """Validate that SKILL.md content has proper YAML frontmatter.

    Returns an error message or ``None`` if valid.
    """
    if not content or not content.strip():
        return "Content cannot be empty."

    if not content.startswith("---"):
        return "SKILL.md must start with YAML frontmatter (---). See existing skills for format."

    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return "SKILL.md frontmatter is not closed. Ensure you have a closing '---' line."

    yaml_content = content[3 : end_match.start() + 3]

    try:
        parsed = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        return f"YAML frontmatter parse error: {exc}"

    if not isinstance(parsed, dict):
        return "Frontmatter must be a YAML mapping (key: value pairs)."

    if "name" not in parsed:
        return "Frontmatter must include 'name' field."
    if "description" not in parsed:
        return "Frontmatter must include 'description' field."
    if len(str(parsed["description"])) > MAX_DESCRIPTION_LENGTH:
        return f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters."

    body = content[end_match.end() + 3 :].strip()
    if not body:
        return "SKILL.md must have content after the frontmatter (instructions, procedures, etc.)."

    return None


def _resolve_skill_dir(name: str) -> Path:
    """Return the canonical directory path for a skill."""
    return SKILLS_DIR / name


def _find_skill(name: str) -> dict[str, Any] | None:
    """Find a skill by name under ``SKILLS_DIR``.

    Returns ``{"name": ..., "path": Path, "description": ...}`` or ``None``.
    """
    if not SKILLS_DIR.exists():
        return None
    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        if skill_md.parent.name == name:
            # Parse description from frontmatter
            description = ""
            try:
                text = skill_md.read_text(encoding="utf-8")
                if text.startswith("---"):
                    end = re.search(r"\n---\s*\n", text[3:])
                    if end:
                        parsed = yaml.safe_load(text[3 : end.start() + 3])
                        if isinstance(parsed, dict):
                            description = str(parsed.get("description", ""))
            except Exception:
                pass
            return {
                "name": name,
                "path": skill_md.parent,
                "description": description,
            }
    return None


def _validate_file_path(file_path: str) -> str | None:
    """Validate a supporting-file path for write_file / remove_file."""
    if not file_path:
        return "file_path is required."

    normalized = Path(file_path)

    if ".." in normalized.parts:
        return "Path traversal ('..') is not allowed."

    if not normalized.parts or normalized.parts[0] not in ALLOWED_SUBDIRS:
        allowed = ", ".join(sorted(ALLOWED_SUBDIRS))
        return f"File must be under one of: {allowed}. Got: '{file_path}'"

    if len(normalized.parts) < 2:
        return f"Provide a file path, not just a directory. Example: '{normalized.parts[0]}/myfile.md'"

    return None


# ── Action implementations ───────────────────────────────────────────────────

def _action_create(name: str, content: str) -> dict[str, Any]:
    err = _validate_name(name)
    if err:
        return {"success": False, "error": err}

    err = _validate_frontmatter(content)
    if err:
        return {"success": False, "error": err}

    existing = _find_skill(name)
    if existing:
        return {
            "success": False,
            "error": f"A skill named '{name}' already exists at {existing['path']}.",
        }

    skill_dir = _resolve_skill_dir(name)
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "message": f"Skill '{name}' created.",
        "path": str(skill_dir),
        "hint": (
            "To add reference files, templates, or scripts, use "
            f"skill_manage(action='write_file', name='{name}', "
            "file_path='references/example.md', file_content='...')"
        ),
    }


def _action_edit(name: str, content: str) -> dict[str, Any]:
    err = _validate_frontmatter(content)
    if err:
        return {"success": False, "error": err}

    existing = _find_skill(name)
    if not existing:
        return {
            "success": False,
            "error": f"Skill '{name}' not found. Use skills_list to see available skills.",
        }

    skill_md = existing["path"] / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "message": f"Skill '{name}' updated.",
        "path": str(existing["path"]),
    }


def _action_patch(
    name: str,
    old_string: str,
    new_string: str,
) -> dict[str, Any]:
    if not old_string:
        return {"success": False, "error": "old_string is required for 'patch'."}
    if new_string is None:
        return {
            "success": False,
            "error": "new_string is required for 'patch'. Use empty string to delete matched text.",
        }

    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}

    target = existing["path"] / "SKILL.md"
    if not target.exists():
        return {"success": False, "error": f"SKILL.md not found for skill '{name}'."}

    content = target.read_text(encoding="utf-8")

    count = content.count(old_string)
    if count == 0:
        preview = content[:500] + ("..." if len(content) > 500 else "")
        return {
            "success": False,
            "error": "old_string not found in SKILL.md.",
            "file_preview": preview,
        }

    if count > 1:
        return {
            "success": False,
            "error": (
                f"old_string matched {count} times. Provide more surrounding "
                "context to make the match unique."
            ),
            "match_count": count,
        }

    new_content = content.replace(old_string, new_string, 1)

    err = _validate_frontmatter(new_content)
    if err:
        return {"success": False, "error": f"Patch would break SKILL.md structure: {err}"}

    target.write_text(new_content, encoding="utf-8")

    return {
        "success": True,
        "message": f"Patched SKILL.md in skill '{name}' (1 replacement).",
    }


def _action_delete(name: str) -> dict[str, Any]:
    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}

    shutil.rmtree(existing["path"])

    return {"success": True, "message": f"Skill '{name}' deleted."}


def _action_write_file(
    name: str,
    file_path: str,
    file_content: str,
) -> dict[str, Any]:
    err = _validate_file_path(file_path)
    if err:
        return {"success": False, "error": err}

    if file_content is None:
        return {"success": False, "error": "file_content is required."}

    existing = _find_skill(name)
    if not existing:
        return {
            "success": False,
            "error": f"Skill '{name}' not found. Create it first with action='create'.",
        }

    target = existing["path"] / file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(file_content, encoding="utf-8")

    return {
        "success": True,
        "message": f"File '{file_path}' written to skill '{name}'.",
        "path": str(target),
    }


def _action_remove_file(name: str, file_path: str) -> dict[str, Any]:
    err = _validate_file_path(file_path)
    if err:
        return {"success": False, "error": err}

    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}

    target = existing["path"] / file_path
    if not target.exists():
        available: list[str] = []
        for subdir in ALLOWED_SUBDIRS:
            d = existing["path"] / subdir
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        available.append(str(f.relative_to(existing["path"])))
        return {
            "success": False,
            "error": f"File '{file_path}' not found in skill '{name}'.",
            "available_files": available or None,
        }

    target.unlink()

    # Clean up empty parent subdirectory
    parent = target.parent
    skill_dir = existing["path"]
    if parent != skill_dir and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()

    return {
        "success": True,
        "message": f"File '{file_path}' removed from skill '{name}'.",
    }


# ── Main dispatcher ──────────────────────────────────────────────────────────

async def skill_manage(args: dict[str, Any]) -> str:
    """Manage user-created skills.  Dispatches to the appropriate action."""
    action = args.get("action", "")
    name = args.get("name", "")

    if action == "create":
        content = args.get("content")
        if not content:
            return json.dumps(
                {"success": False, "error": "content is required for 'create'. Provide the full SKILL.md text (frontmatter + body)."},
                ensure_ascii=False,
            )
        result = _action_create(name, content)

    elif action == "edit":
        content = args.get("content")
        if not content:
            return json.dumps(
                {"success": False, "error": "content is required for 'edit'. Provide the full updated SKILL.md text."},
                ensure_ascii=False,
            )
        result = _action_edit(name, content)

    elif action == "patch":
        old_string = args.get("old_string")
        new_string = args.get("new_string")
        if not old_string:
            return json.dumps(
                {"success": False, "error": "old_string is required for 'patch'."},
                ensure_ascii=False,
            )
        if new_string is None:
            return json.dumps(
                {"success": False, "error": "new_string is required for 'patch'. Use empty string to delete matched text."},
                ensure_ascii=False,
            )
        result = _action_patch(name, old_string, new_string)

    elif action == "delete":
        result = _action_delete(name)

    elif action == "write_file":
        file_path = args.get("file_path")
        file_content = args.get("file_content")
        if not file_path:
            return json.dumps(
                {"success": False, "error": "file_path is required for 'write_file'. Example: 'references/api-guide.md'"},
                ensure_ascii=False,
            )
        if file_content is None:
            return json.dumps(
                {"success": False, "error": "file_content is required for 'write_file'."},
                ensure_ascii=False,
            )
        result = _action_write_file(name, file_path, file_content)

    elif action == "remove_file":
        file_path = args.get("file_path")
        if not file_path:
            return json.dumps(
                {"success": False, "error": "file_path is required for 'remove_file'."},
                ensure_ascii=False,
            )
        result = _action_remove_file(name, file_path)

    else:
        result = {
            "success": False,
            "error": f"Unknown action '{action}'. Use: create, edit, patch, delete, write_file, remove_file",
        }

    return json.dumps(result, ensure_ascii=False)


# ── Tool registration ────────────────────────────────────────────────────────

def register_skill_manager_tools() -> None:
    """Register the ``skill_manage`` tool in the ``skills`` toolset."""
    registry.register(
        name="skill_manage",
        toolset="skills",
        description=(
            "Manage skills (create, update, delete). Skills are your procedural "
            "memory -- reusable approaches for recurring task types. "
            "New skills go to ~/.finarg/skills/; existing skills can be modified wherever they live.\n\n"
            "Actions: create (full SKILL.md), "
            "patch (old_string/new_string -- preferred for fixes), "
            "edit (full SKILL.md rewrite -- major overhauls only), "
            "delete, write_file, remove_file.\n\n"
            "Create when: complex task succeeded, errors overcome, "
            "user-corrected approach worked, non-trivial workflow discovered, "
            "or user asks you to remember a procedure.\n"
            "Update when: instructions stale/wrong, missing steps or pitfalls "
            "found during use. Patch immediately after encountering issues.\n\n"
            "Good skills: trigger conditions, numbered steps with exact commands, "
            "pitfalls section, verification steps. Use skill_view() to see format examples."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "edit", "patch", "delete", "write_file", "remove_file"],
                    "description": "The action to perform.",
                },
                "name": {
                    "type": "string",
                    "description": (
                        "Skill name (lowercase, hyphens/underscores, max 64 chars). "
                        "Must match an existing skill for patch/edit/delete/write_file/remove_file."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Full SKILL.md content (YAML frontmatter + markdown body). "
                        "Required for 'create' and 'edit'."
                    ),
                },
                "old_string": {
                    "type": "string",
                    "description": (
                        "Text to find in SKILL.md (required for 'patch'). "
                        "Must be unique -- include enough context."
                    ),
                },
                "new_string": {
                    "type": "string",
                    "description": (
                        "Replacement text (required for 'patch'). "
                        "Can be empty string to delete matched text."
                    ),
                },
                "file_path": {
                    "type": "string",
                    "description": (
                        "Path to a supporting file within the skill directory. "
                        "Required for 'write_file'/'remove_file'. "
                        "Must be under references/, templates/, scripts/, or assets/."
                    ),
                },
                "file_content": {
                    "type": "string",
                    "description": "Content for the file. Required for 'write_file'.",
                },
            },
            "required": ["action", "name"],
        },
        handler=skill_manage,
        emoji="\U0001f9e0",  # 🧠
    )
