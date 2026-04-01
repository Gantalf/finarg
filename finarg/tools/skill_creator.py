"""Skill management tools: create, list, and delete user-defined skills.

These tools are registered at import time so they are available as soon as the
``finarg.tools`` package is imported.
"""

from __future__ import annotations

import ast
import json
import keyword
import logging
from pathlib import Path

from finarg.constants import SKILLS_DIR
from finarg.tools.registry import registry

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_skills_dir() -> Path:
    """Create the skills directory if it doesn't exist and return its path."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    return SKILLS_DIR


def _validate_skill_name(name: str) -> str | None:
    """Return an error message if *name* is not a valid Python identifier."""
    if not name.isidentifier():
        return f"'{name}' is not a valid Python identifier"
    if keyword.iskeyword(name):
        return f"'{name}' is a reserved Python keyword"
    return None


def _validate_syntax(code: str) -> str | None:
    """Return an error message if *code* is not syntactically valid Python."""
    try:
        compile(code, "<skill>", "exec")
    except SyntaxError as exc:
        return f"Syntax error at line {exc.lineno}: {exc.msg}"
    return None


def _extract_docstring(path: Path) -> str:
    """Return the module docstring of a .py file, or a fallback."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstring = ast.get_docstring(tree)
        return docstring or "(no description)"
    except Exception:
        return "(unreadable)"


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def _create_skill(args: dict) -> str:  # noqa: C901
    """Create a new skill file and hot-load it into the registry."""
    name: str = args.get("name", "")
    description: str = args.get("description", "")
    code: str = args.get("code", "")
    force: bool = args.get("force", False)

    # Validate name
    err = _validate_skill_name(name)
    if err:
        return json.dumps({"error": err})

    # Validate syntax
    err = _validate_syntax(code)
    if err:
        return json.dumps({"error": err})

    skills_dir = _ensure_skills_dir()
    path = skills_dir / f"{name}.py"

    if path.exists() and not force:
        return json.dumps({
            "error": f"Skill '{name}' already exists. Pass force=true to overwrite.",
        })

    # Prepend a docstring if the code doesn't already have one
    final_code = code
    try:
        tree = ast.parse(code)
        if ast.get_docstring(tree) is None and description:
            final_code = f'"""{description}"""\n\n{code}'
    except Exception:
        pass  # syntax was already validated; this is best-effort

    path.write_text(final_code, encoding="utf-8")

    # If overwriting, unregister any existing tool with a matching skill source
    if force:
        for entry in list(registry.list_tools()):
            if entry.source == "skill" and entry.name == name:
                registry.unregister(name)

    # Hot-load
    registry.load_skill_file(path)

    return json.dumps({
        "ok": True,
        "message": f"Skill '{name}' created and loaded from {path}",
    })


async def _list_skills(args: dict) -> str:
    """List all user-defined skill files."""
    skills_dir = _ensure_skills_dir()
    skills: list[dict[str, str]] = []
    for path in sorted(skills_dir.glob("*.py")):
        skills.append({
            "name": path.stem,
            "file": str(path),
            "description": _extract_docstring(path),
        })
    return json.dumps({"skills": skills, "count": len(skills)})


async def _delete_skill(args: dict) -> str:
    """Delete a skill file and unregister its tool."""
    name: str = args.get("name", "")

    err = _validate_skill_name(name)
    if err:
        return json.dumps({"error": err})

    skills_dir = _ensure_skills_dir()
    path = skills_dir / f"{name}.py"

    if not path.exists():
        return json.dumps({"error": f"Skill '{name}' not found"})

    path.unlink()
    registry.unregister(name)

    return json.dumps({"ok": True, "message": f"Skill '{name}' deleted"})


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

registry.register(
    name="create_skill",
    toolset="skills",
    description=(
        "Create a new user-defined skill. Writes a Python file to the skills "
        "directory and hot-loads it into the tool registry."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Skill name (must be a valid Python identifier)",
            },
            "description": {
                "type": "string",
                "description": "Short human-readable description of the skill",
            },
            "code": {
                "type": "string",
                "description": "Python source code for the skill",
            },
            "force": {
                "type": "boolean",
                "description": "Overwrite if the skill already exists",
                "default": False,
            },
        },
        "required": ["name", "description", "code"],
    },
    handler=_create_skill,
    emoji="\U0001f9e0",
)

registry.register(
    name="list_skills",
    toolset="skills",
    description="List all user-defined skills with their descriptions.",
    parameters={"type": "object", "properties": {}},
    handler=_list_skills,
    emoji="\U0001f4cb",
)

registry.register(
    name="delete_skill",
    toolset="skills",
    description="Delete a user-defined skill by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the skill to delete",
            },
        },
        "required": ["name"],
    },
    handler=_delete_skill,
    emoji="\U0001f5d1",
)
