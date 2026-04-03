"""OpenAI-compatible provider (works with OpenAI and Moonshot/Kimi)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from openai import AsyncOpenAI

from finarg.agent.providers.base import LLMResponse, ToolCall

log = logging.getLogger(__name__)


def _pdf_to_image_blocks(file_base64: str) -> list[dict]:
    """Convert a base64 PDF to a list of image_url content blocks (one per page).

    Used for Kimi/Moonshot which doesn't support inline PDFs.
    """
    import base64
    import fitz  # pymupdf

    pdf_bytes = base64.b64decode(file_base64)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    blocks = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode()
        blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })

    doc.close()
    return blocks


class OpenAIProvider:
    """LLM provider using the OpenAI ChatCompletions API.

    Works with any OpenAI-compatible endpoint (OpenAI, Moonshot/Kimi, etc.).
    Implements the :class:`LLMProvider` protocol.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        # Build messages with system prompt
        full_messages: list[dict[str, Any]] = []
        if system:
            full_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg.get("role") == "tool":
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": msg.get("content", ""),
                })
            elif msg.get("role") == "assistant" and "tool_calls" in msg:
                tc_list = []
                for tc in msg["tool_calls"]:
                    args = tc["function"]["arguments"]
                    tc_list.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": args if isinstance(args, str) else json.dumps(args),
                        },
                    })
                full_messages.append({
                    "role": "assistant",
                    "content": msg.get("content") or None,
                    "tool_calls": tc_list,
                })
            else:
                full_messages.append({"role": msg["role"], "content": msg.get("content", "")})

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": full_messages,
        }
        if tools:
            kwargs["tools"] = tools

        if stream and stream_callback:
            return await self._stream_chat(kwargs, stream_callback)
        return await self._blocking_chat(kwargs)

    async def _blocking_chat(self, kwargs: dict[str, Any]) -> LLMResponse:
        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                ))

        usage = response.usage
        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    async def _stream_chat(
        self,
        kwargs: dict[str, Any],
        callback: Callable[[str], None],
    ) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls_map: dict[int, dict] = {}

        kwargs["stream"] = True
        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            if delta.content:
                text_parts.append(delta.content)
                callback(delta.content)

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc_delta.id:
                        tool_calls_map[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_map[idx]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_map[idx]["arguments"] += tc_delta.function.arguments

        tool_calls: list[ToolCall] = []
        for idx in sorted(tool_calls_map):
            tc = tool_calls_map[idx]
            tool_calls.append(ToolCall(
                id=tc["id"],
                name=tc["name"],
                arguments=json.loads(tc["arguments"]) if tc["arguments"] else {},
            ))

        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
        )

    async def analyze_visual(
        self,
        file_base64: str,
        media_type: str,
        prompt: str,
    ) -> str:
        """Analyze a visual file (PDF or image) using OpenAI or Kimi."""
        is_kimi = "moonshot" in str(getattr(self._client, '_base_url', ''))
        is_pdf = media_type == "application/pdf"

        if is_pdf and is_kimi:
            # Kimi doesn't support PDF inline — convert pages to images
            content_blocks = _pdf_to_image_blocks(file_base64)
            content_blocks.append({"type": "text", "text": prompt})
        elif is_pdf:
            # OpenAI supports PDF natively
            content_blocks = [
                {
                    "type": "file",
                    "file": {
                        "filename": "document.pdf",
                        "file_data": f"data:{media_type};base64,{file_base64}",
                    },
                },
                {"type": "text", "text": prompt},
            ]
        else:
            # Image — works for both OpenAI and Kimi
            content_blocks = [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{file_base64}"},
                },
                {"type": "text", "text": prompt},
            ]

        # Kimi vision requires kimi-k2.5 model (kimi-k2-thinking doesn't support images)
        vision_model = "kimi-k2.5" if is_kimi else self._model

        response = await self._client.chat.completions.create(
            model=vision_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content_blocks}],
        )
        return response.choices[0].message.content
