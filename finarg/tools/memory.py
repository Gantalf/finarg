"""Persistent memory tool — follows Hermes memory_tool.py pattern.

Two files:
- MEMORY.md: agent's personal notes (environment facts, project conventions, lessons)
- USER.md: what the agent knows about the user (name, preferences, style)

Entries are separated by ``\\n§\\n``. Each file has a char limit to keep
the system prompt compact.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

ENTRY_DELIMITER = "\n§\n"

# Default char limits (match Hermes)
DEFAULT_MEMORY_CHAR_LIMIT = 2200
DEFAULT_USER_CHAR_LIMIT = 1375


class MemoryStore:
    """Read/write persistent memory entries to MEMORY.md and USER.md.

    Follows Hermes MemoryStore pattern:
    - Entries separated by ``§`` delimiter
    - Char limits per target
    - Frozen snapshot for system prompt (never mutated mid-session)
    - Atomic file writes (temp file + os.replace)
    """

    def __init__(
        self,
        memory_dir: Path,
        memory_char_limit: int = DEFAULT_MEMORY_CHAR_LIMIT,
        user_char_limit: int = DEFAULT_USER_CHAR_LIMIT,
    ) -> None:
        self._memory_dir = memory_dir
        self._memory_char_limit = memory_char_limit
        self._user_char_limit = user_char_limit
        self._memory_entries: list[str] = []
        self._user_entries: list[str] = []
        # Frozen snapshot — set once at load_from_disk(), never mutated mid-session
        self._snapshot: dict[str, str] = {"memory": "", "user": ""}

    def load_from_disk(self) -> None:
        """Load entries from MEMORY.md and USER.md, capture system prompt snapshot."""
        self._memory_dir.mkdir(parents=True, exist_ok=True)

        self._memory_entries = self._read_file(self._memory_dir / "MEMORY.md")
        self._user_entries = self._read_file(self._memory_dir / "USER.md")

        # Deduplicate (preserve order, keep first)
        self._memory_entries = list(dict.fromkeys(self._memory_entries))
        self._user_entries = list(dict.fromkeys(self._user_entries))

        # Freeze snapshot for prompt injection
        self._snapshot = {
            "memory": self._render_block("memory", self._memory_entries),
            "user": self._render_block("user", self._user_entries),
        }

    # ── Public API ──────────────────────────────────────────────────

    def add(self, target: str, content: str) -> dict[str, Any]:
        """Append a new entry."""
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}

        entries = self._entries_for(target)
        limit = self._char_limit(target)

        # Reject duplicates
        if content in entries:
            return self._success("Entry already exists (no duplicate added).", target)

        # Check limit
        new_entries = entries + [content]
        new_total = len(ENTRY_DELIMITER.join(new_entries))
        if new_total > limit:
            current = self._char_count(target)
            return {
                "success": False,
                "error": (
                    f"Memory at {current:,}/{limit:,} chars. "
                    f"Adding this entry ({len(content)} chars) would exceed the limit. "
                    f"Replace or remove existing entries first."
                ),
                "current_entries": entries,
            }

        entries.append(content)
        self._set_entries(target, entries)
        self._save(target)
        return self._success("Entry added.", target)

    def replace(self, target: str, old_text: str, new_content: str) -> dict[str, Any]:
        """Find entry containing old_text, replace with new_content."""
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use 'remove' to delete."}

        entries = self._entries_for(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1:
            unique = set(e for _, e in matches)
            if len(unique) > 1:
                previews = [e[:80] for _, e in matches]
                return {"success": False, "error": f"Multiple entries matched. Be more specific.", "matches": previews}

        idx = matches[0][0]
        limit = self._char_limit(target)
        test = entries.copy()
        test[idx] = new_content
        if len(ENTRY_DELIMITER.join(test)) > limit:
            return {"success": False, "error": "Replacement would exceed char limit."}

        entries[idx] = new_content
        self._set_entries(target, entries)
        self._save(target)
        return self._success("Entry replaced.", target)

    def remove(self, target: str, old_text: str) -> dict[str, Any]:
        """Remove entry containing old_text."""
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        entries = self._entries_for(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1:
            unique = set(e for _, e in matches)
            if len(unique) > 1:
                previews = [e[:80] for _, e in matches]
                return {"success": False, "error": f"Multiple entries matched. Be more specific.", "matches": previews}

        entries.pop(matches[0][0])
        self._set_entries(target, entries)
        self._save(target)
        return self._success("Entry removed.", target)

    def format_for_system_prompt(self, target: str) -> str | None:
        """Return the frozen snapshot for system prompt injection.

        Returns the state captured at load_from_disk() time, NOT live state.
        Mid-session writes do not affect this (keeps prefix cache stable).
        """
        block = self._snapshot.get(target, "")
        return block if block else None

    # ── Internals ───────────────────────────────────────────────────

    def _entries_for(self, target: str) -> list[str]:
        return self._user_entries if target == "user" else self._memory_entries

    def _set_entries(self, target: str, entries: list[str]) -> None:
        if target == "user":
            self._user_entries = entries
        else:
            self._memory_entries = entries

    def _char_count(self, target: str) -> int:
        entries = self._entries_for(target)
        return len(ENTRY_DELIMITER.join(entries)) if entries else 0

    def _char_limit(self, target: str) -> int:
        return self._user_char_limit if target == "user" else self._memory_char_limit

    def _save(self, target: str) -> None:
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        path = self._memory_dir / ("USER.md" if target == "user" else "MEMORY.md")
        self._write_file(path, self._entries_for(target))

    def _success(self, message: str, target: str) -> dict[str, Any]:
        entries = self._entries_for(target)
        current = self._char_count(target)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        return {
            "success": True,
            "message": message,
            "target": target,
            "entries": entries,
            "usage": f"{pct}% — {current:,}/{limit:,} chars",
            "entry_count": len(entries),
        }

    def _render_block(self, target: str, entries: list[str]) -> str:
        if not entries:
            return ""
        limit = self._char_limit(target)
        content = ENTRY_DELIMITER.join(entries)
        current = len(content)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0

        if target == "user":
            header = f"USER PROFILE [{pct}% — {current:,}/{limit:,} chars]"
        else:
            header = f"MEMORY [{pct}% — {current:,}/{limit:,} chars]"

        sep = "═" * 46
        return f"{sep}\n{header}\n{sep}\n{content}"

    @staticmethod
    def _read_file(path: Path) -> list[str]:
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return []
        if not raw.strip():
            return []
        entries = [e.strip() for e in raw.split(ENTRY_DELIMITER)]
        return [e for e in entries if e]

    @staticmethod
    def _write_file(path: Path, entries: list[str]) -> None:
        """Atomic write: temp file + os.replace."""
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".mem_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(path))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


# ── Tool handler ────────────────────────────────────────────────────

# Module-level store — set by cli.py at startup
_store: MemoryStore | None = None


def set_memory_store(store: MemoryStore) -> None:
    """Set the global memory store. Called by cli.py at agent build time."""
    global _store
    _store = store


async def memory_tool(args: dict[str, Any]) -> str:
    """Dispatch memory actions: add, replace, remove."""
    if _store is None:
        return json.dumps({"success": False, "error": "Memory not available."})

    action = args.get("action", "")
    target = args.get("target", "memory")
    content = args.get("content")
    old_text = args.get("old_text")

    if target not in ("memory", "user"):
        return json.dumps({"success": False, "error": f"Invalid target '{target}'. Use 'memory' or 'user'."})

    if action == "add":
        if not content:
            return json.dumps({"success": False, "error": "content is required for 'add'."})
        result = _store.add(target, content)
    elif action == "replace":
        if not old_text or not content:
            return json.dumps({"success": False, "error": "old_text and content required for 'replace'."})
        result = _store.replace(target, old_text, content)
    elif action == "remove":
        if not old_text:
            return json.dumps({"success": False, "error": "old_text is required for 'remove'."})
        result = _store.remove(target, old_text)
    else:
        return json.dumps({"success": False, "error": f"Unknown action '{action}'. Use: add, replace, remove"})

    return json.dumps(result, ensure_ascii=False)


# ── Registration ────────────────────────────────────────────────────

def register_memory_tools() -> None:
    """Register the memory tool."""
    from finarg.tools.registry import registry

    registry.register(
        name="memory",
        toolset="memory",
        description=(
            "Save durable information to persistent memory that survives across sessions. "
            "Memory is injected into future turns, so keep it compact and focused.\n\n"
            "WHEN TO SAVE (do this proactively, don't wait to be asked):\n"
            "- User corrects you or says 'remember this'\n"
            "- User shares a preference, personal detail (name, role, timezone)\n"
            "- You discover something about the environment (API quirks, project structure)\n"
            "- You learn a stable fact useful in future sessions\n\n"
            "PRIORITY: User corrections > preferences > environment facts.\n"
            "Do NOT save: task progress, session outcomes, temporary state.\n\n"
            "TWO TARGETS:\n"
            "- 'user': who the user is (name, preferences, style)\n"
            "- 'memory': your notes (environment, conventions, lessons)\n\n"
            "ACTIONS: add, replace (old_text identifies entry), remove (old_text identifies entry)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "replace", "remove"],
                    "description": "The action to perform.",
                },
                "target": {
                    "type": "string",
                    "enum": ["memory", "user"],
                    "description": "Which store: 'memory' for notes, 'user' for user profile.",
                },
                "content": {
                    "type": "string",
                    "description": "Entry content. Required for 'add' and 'replace'.",
                },
                "old_text": {
                    "type": "string",
                    "description": "Substring identifying the entry to replace or remove.",
                },
            },
            "required": ["action", "target"],
        },
        handler=memory_tool,
        emoji="\U0001f9e0",
    )
