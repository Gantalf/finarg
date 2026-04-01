"""Central tool registry for Finarg.

Every tool module calls ``registry.register()`` at import time so the agent
loop can later retrieve OpenAI-compatible function definitions and dispatch
calls by name.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

log = logging.getLogger(__name__)


@dataclass(slots=True)
class ToolEntry:
    """Metadata + handler for a single registered tool."""

    name: str
    toolset: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[str]]
    emoji: str = "\U0001f527"
    source: str = "builtin"  # "builtin" | "skill"
    check_fn: Callable[[], bool] | None = None  # availability check


class ToolRegistry:
    """Singleton registry that holds every available tool.

    Tools self-register at import time via :meth:`register`.  The agent loop
    calls :meth:`get_definitions` to build the ``tools`` payload and
    :meth:`dispatch` to execute a chosen tool.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolEntry] = {}
        self._skill_modules: dict[str, str] = {}  # name -> module_name

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        toolset: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[[dict[str, Any]], Awaitable[str]],
        emoji: str = "\U0001f527",
        *,
        source: str = "builtin",
        check_fn: Callable[[], bool] | None = None,
    ) -> None:
        """Register a tool.  Skips silently on duplicate names."""
        if name in self._tools:
            log.debug("Tool '%s' already registered, skipping", name)
            return
        self._tools[name] = ToolEntry(
            name=name,
            toolset=toolset,
            description=description,
            parameters=parameters,
            handler=handler,
            emoji=emoji,
            source=source,
            check_fn=check_fn,
        )
        log.debug("Registered tool %s (toolset=%s, source=%s)", name, toolset, source)

    def unregister(self, name: str) -> None:
        """Remove a tool by name.  No-op if not found."""
        self._tools.pop(name, None)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, name: str, args: dict[str, Any]) -> str:
        """Look up *name* and call its handler, returning a JSON string.

        On any exception the error is caught and a JSON error payload is
        returned so the agent can reason about the failure.
        """
        entry = self._tools.get(name)
        if entry is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = await entry.handler(args)
            return result if isinstance(result, str) else json.dumps(result)
        except Exception:
            tb = traceback.format_exc()
            log.exception("Tool %s raised an exception", name)
            return json.dumps({"error": f"Tool '{name}' failed", "traceback": tb})

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    def get_definitions(
        self, enabled_toolsets: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return OpenAI function-calling style definitions.

        If *enabled_toolsets* is provided only tools whose ``toolset`` is in
        the list are included.
        """
        defs: list[dict[str, Any]] = []
        for entry in self._tools.values():
            if enabled_toolsets is not None and entry.toolset not in enabled_toolsets:
                continue
            # Skip tools whose check_fn returns False
            if entry.check_fn is not None:
                try:
                    if not entry.check_fn():
                        continue
                except Exception:
                    continue
            defs.append(
                {
                    "type": "function",
                    "function": {
                        "name": entry.name,
                        "description": entry.description,
                        "parameters": entry.parameters,
                    },
                }
            )
        return defs

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_tools(self) -> list[ToolEntry]:
        """Return all registered tools."""
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    # ------------------------------------------------------------------
    # Skill loading
    # ------------------------------------------------------------------

    def load_skill_file(self, path: Path) -> None:
        """Import a single skill ``.py`` file, registering any tools it
        declares via ``registry.register()``.

        Tools registered during import are tagged with ``source="skill"``.
        """
        module_name = f"finarg_skill_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            log.warning("Cannot load skill file: %s", path)
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception:
            log.exception("Failed to load skill %s", path)
            sys.modules.pop(module_name, None)
            return
        self._skill_modules[path.stem] = module_name
        log.info("Loaded skill file: %s", path)

    def load_skills_dir(self, skills_dir: Path) -> None:
        """Import every ``.py`` file in *skills_dir*."""
        if not skills_dir.is_dir():
            log.debug("Skills directory does not exist: %s", skills_dir)
            return
        for path in sorted(skills_dir.glob("*.py")):
            self.load_skill_file(path)

    def reload_skills(self, skills_dir: Path) -> None:
        """Unregister all skill-sourced tools and re-import."""
        # Remove previously loaded skill tools
        skill_names = [
            name for name, entry in self._tools.items() if entry.source == "skill"
        ]
        for name in skill_names:
            self.unregister(name)

        # Remove cached modules
        for module_name in self._skill_modules.values():
            sys.modules.pop(module_name, None)
        self._skill_modules.clear()

        self.load_skills_dir(skills_dir)


# Module-level singleton
registry = ToolRegistry()
