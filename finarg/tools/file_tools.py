"""File tools: read, write, patch, and search files."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger(__name__)

# Paths that file tools should refuse to write to.
_SENSITIVE_PATH_PREFIXES = ("/etc/", "/boot/", "/usr/lib/")


def _check_sensitive_path(filepath: str) -> str | None:
    """Return an error message if the path targets a sensitive system location."""
    try:
        resolved = os.path.realpath(os.path.expanduser(filepath))
    except (OSError, ValueError):
        resolved = filepath
    for prefix in _SENSITIVE_PATH_PREFIXES:
        if resolved.startswith(prefix):
            return (
                f"Refusing to write to sensitive system path: {filepath}. "
                "Use a terminal tool with sudo if you need to modify system files."
            )
    return None


def _is_binary(path: str, sample_size: int = 8192) -> bool:
    """Return True if *path* appears to be a binary file."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" in chunk
    except Exception:
        return False


# Directories to skip when walking for search.
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox"}


# ------------------------------------------------------------------
# Tool handlers
# ------------------------------------------------------------------


async def read_file(args: dict) -> str:
    """Read a text file with line numbers and pagination."""
    path = args.get("path", "")
    offset = max(int(args.get("offset", 1)), 1)
    limit = min(int(args.get("limit", 500)), 2000)

    if not path:
        return json.dumps({"error": "path is required"})

    expanded = os.path.expanduser(path)

    if not os.path.exists(expanded):
        return json.dumps({"error": f"File not found: {path}"})

    if not os.access(expanded, os.R_OK):
        return json.dumps({"error": f"Permission denied: {path}"})

    if _is_binary(expanded):
        return json.dumps({"error": f"Cannot read binary file: {path}"})

    def _read() -> str:
        with open(expanded, "r", errors="replace") as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)
        start = offset - 1  # convert 1-indexed to 0-indexed
        end = min(start + limit, total_lines)
        selected = all_lines[start:end]

        numbered: list[str] = []
        for i, line in enumerate(selected, start=offset):
            numbered.append(f"{i:>6}\t{line.rstrip()}")

        content = "\n".join(numbered)

        return json.dumps(
            {
                "path": path,
                "content": content,
                "total_lines": total_lines,
                "showing": f"lines {offset}-{min(offset + len(selected) - 1, total_lines)}",
            },
            ensure_ascii=False,
        )

    return await asyncio.to_thread(_read)


async def write_file(args: dict) -> str:
    """Write content to a file, creating parent directories as needed."""
    path = args.get("path", "")
    content = args.get("content", "")

    if not path:
        return json.dumps({"error": "path is required"})
    if content is None:
        return json.dumps({"error": "content is required"})

    sensitive_err = _check_sensitive_path(path)
    if sensitive_err:
        return json.dumps({"error": sensitive_err})

    expanded = os.path.expanduser(path)

    def _write() -> str:
        parent = os.path.dirname(expanded)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(expanded, "w") as f:
            bytes_written = f.write(content)

        return json.dumps(
            {
                "path": path,
                "bytes_written": bytes_written,
                "message": "File written successfully",
            },
            ensure_ascii=False,
        )

    try:
        return await asyncio.to_thread(_write)
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def patch_file(args: dict) -> str:
    """Find-and-replace edit in a file."""
    path = args.get("path", "")
    old_string = args.get("old_string")
    new_string = args.get("new_string")
    replace_all = bool(args.get("replace_all", False))

    if not path:
        return json.dumps({"error": "path is required"})
    if old_string is None or new_string is None:
        return json.dumps({"error": "old_string and new_string are required"})

    sensitive_err = _check_sensitive_path(path)
    if sensitive_err:
        return json.dumps({"error": sensitive_err})

    expanded = os.path.expanduser(path)

    if not os.path.exists(expanded):
        return json.dumps({"error": f"File not found: {path}"})

    def _patch() -> str:
        with open(expanded, "r", errors="replace") as f:
            content = f.read()

        count = content.count(old_string)
        if count == 0:
            # Provide a helpful snippet of the file for context.
            preview = content[:500]
            return json.dumps(
                {
                    "error": (
                        f"old_string not found in {path}. "
                        "Verify the exact text by reading the file first."
                    ),
                    "file_preview": preview,
                },
                ensure_ascii=False,
            )

        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = count
        else:
            if count > 1:
                return json.dumps(
                    {
                        "error": (
                            f"old_string found {count} times in {path}. "
                            "Provide more context to make it unique, or set replace_all=true."
                        ),
                    },
                    ensure_ascii=False,
                )
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1

        with open(expanded, "w") as f:
            f.write(new_content)

        return json.dumps(
            {
                "path": path,
                "replacements": replacements,
                "message": f"Replaced {replacements} occurrence(s)",
            },
            ensure_ascii=False,
        )

    try:
        return await asyncio.to_thread(_patch)
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def search_files(args: dict) -> str:
    """Regex search through file contents in a directory tree."""
    pattern = args.get("pattern", "")
    path = args.get("path", ".")
    file_glob = args.get("file_glob")
    limit = min(int(args.get("limit", 50)), 500)

    if not pattern:
        return json.dumps({"error": "pattern is required"})

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return json.dumps({"error": f"Invalid regex: {e}"})

    expanded = os.path.expanduser(path)

    def _search() -> str:
        matches: list[dict] = []
        total = 0

        for dirpath, dirnames, filenames in os.walk(expanded):
            # Prune skipped directories in-place.
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

            for fname in filenames:
                if file_glob and not _glob_match(fname, file_glob):
                    continue

                fpath = os.path.join(dirpath, fname)

                if _is_binary(fpath):
                    continue

                try:
                    with open(fpath, "r", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            if regex.search(line):
                                total += 1
                                if len(matches) < limit:
                                    rel = os.path.relpath(fpath, expanded)
                                    matches.append(
                                        {
                                            "file": rel,
                                            "line": lineno,
                                            "content": line.rstrip()[:300],
                                        }
                                    )
                except (OSError, UnicodeDecodeError):
                    continue

        return json.dumps(
            {
                "pattern": pattern,
                "matches": matches,
                "total": total,
                "truncated": total > limit,
            },
            ensure_ascii=False,
        )

    return await asyncio.to_thread(_search)


def _glob_match(filename: str, glob_pattern: str) -> bool:
    """Simple glob matching using fnmatch."""
    import fnmatch

    return fnmatch.fnmatch(filename, glob_pattern)


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------


def register_file_tools() -> None:
    """Register file tools with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="read_file",
        toolset="file",
        description=(
            "Read a text file with line numbers and pagination. "
            "Returns numbered lines in the format '  1\\tline content'. "
            "Use offset and limit for large files. Cannot read binary files."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (absolute, relative, or ~/path)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed, default: 1)",
                    "default": 1,
                    "minimum": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default: 500, max: 2000)",
                    "default": 500,
                    "maximum": 2000,
                },
            },
            "required": ["path"],
        },
        handler=read_file,
        emoji="\U0001f4d6",  # 📖
    )

    registry.register(
        name="write_file",
        toolset="file",
        description=(
            "Write content to a file, completely replacing existing content. "
            "Creates parent directories automatically. "
            "OVERWRITES the entire file -- use patch_file for targeted edits."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (created if missing, overwritten if exists)",
                },
                "content": {
                    "type": "string",
                    "description": "Complete content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        handler=write_file,
        emoji="\u270f\ufe0f",  # ✏️
    )

    registry.register(
        name="patch_file",
        toolset="file",
        description=(
            "Targeted find-and-replace edit in a file. "
            "Finds old_string and replaces it with new_string. "
            "Set replace_all=true to replace every occurrence; "
            "otherwise old_string must appear exactly once."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": (
                        "Text to find in the file. Must be unique unless replace_all=true. "
                        "Include enough surrounding context to ensure uniqueness."
                    ),
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement text (can be empty string to delete)",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences instead of requiring a unique match (default: false)",
                    "default": False,
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
        handler=patch_file,
        emoji="\U0001f527",  # 🔧
    )

    registry.register(
        name="search_files",
        toolset="file",
        description=(
            "Search file contents with a regex pattern. "
            "Walks the directory tree, skipping .git/, node_modules/, and binary files. "
            "Returns matching lines with file paths and line numbers."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for in file contents",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current working directory)",
                    "default": ".",
                },
                "file_glob": {
                    "type": "string",
                    "description": "Filter files by glob pattern (e.g. '*.py')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of matches to return (default: 50)",
                    "default": 50,
                },
            },
            "required": ["pattern"],
        },
        handler=search_files,
        emoji="\U0001f50d",  # 🔍
    )
