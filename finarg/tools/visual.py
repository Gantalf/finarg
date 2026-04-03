"""Visual analysis tool: read PDFs and images using the LLM's vision capabilities."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Module-level provider — set by cli.py at startup
_provider = None


def set_visual_provider(provider) -> None:
    """Set the LLM provider used for visual analysis. Called by cli.py."""
    global _provider
    _provider = provider


# Supported file types
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
PDF_TYPES = {".pdf"}
SUPPORTED_TYPES = IMAGE_TYPES | PDF_TYPES


def _detect_media_type(path: Path) -> str | None:
    """Detect MIME type from file extension."""
    ext = path.suffix.lower()
    if ext in PDF_TYPES:
        return "application/pdf"
    mime, _ = mimetypes.guess_type(str(path))
    if mime and mime.startswith("image/"):
        return mime
    # Fallback by extension
    type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return type_map.get(ext)


async def analyze_document(args: dict[str, Any]) -> str:
    """Read a PDF or image and analyze it visually using the LLM."""
    if _provider is None:
        return json.dumps({"error": "Visual provider not configured."})

    file_path = args.get("path", "")
    prompt = args.get("prompt", "Describe what you see in this document.")

    if not file_path:
        return json.dumps({"error": "path is required"})

    path = Path(file_path).expanduser()
    if not path.exists():
        return json.dumps({"error": f"File not found: {path}"})

    if path.suffix.lower() not in SUPPORTED_TYPES:
        return json.dumps({
            "error": f"Unsupported file type: {path.suffix}. Supported: {', '.join(sorted(SUPPORTED_TYPES))}",
        })

    media_type = _detect_media_type(path)
    if not media_type:
        return json.dumps({"error": f"Could not detect media type for {path}"})

    # Read and encode file
    try:
        raw_bytes = path.read_bytes()
        file_base64 = base64.b64encode(raw_bytes).decode()
    except Exception as e:
        return json.dumps({"error": f"Failed to read file: {e}"})

    # Call the LLM with visual content
    try:
        result = await _provider.analyze_visual(file_base64, media_type, prompt)
        return json.dumps({
            "path": str(path),
            "media_type": media_type,
            "analysis": result,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"LLM analysis failed: {e}"})


def register_visual_tools() -> None:
    """Register the analyze_document tool."""
    from finarg.tools.registry import registry

    registry.register(
        name="analyze_document",
        toolset="file",
        description=(
            "Read and analyze a PDF or image file visually using the LLM. "
            "The LLM sees the actual visual content of the file — use this for "
            "invoices, receipts, documents, screenshots, tickets, or any visual file. "
            "Provide a prompt describing what to extract or analyze."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the PDF or image file",
                },
                "prompt": {
                    "type": "string",
                    "description": "What to extract or analyze from the file (e.g. 'Extract CUIT, amount, date, invoice number')",
                },
            },
            "required": ["path", "prompt"],
        },
        handler=analyze_document,
        emoji="\U0001f441",
    )
