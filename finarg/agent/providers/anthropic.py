"""Anthropic Claude provider."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from anthropic import AsyncAnthropic

from finarg.agent.providers.base import LLMProvider, LLMResponse, ToolCall
from finarg.constants import DEFAULT_MODEL

log = logging.getLogger(__name__)


def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI function-calling format to Anthropic tool format.

    OpenAI style::

        {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}

    Anthropic style::

        {"name": ..., "description": ..., "input_schema": ...}
    """
    converted: list[dict[str, Any]] = []
    for tool in tools:
        func = tool.get("function", tool)
        converted.append(
            {
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return converted


def _convert_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure messages conform to the Anthropic API format.

    Anthropic requires ``role`` in {``user``, ``assistant``} and tool results
    to be sent as ``user`` messages with ``tool_result`` content blocks.
    """
    converted: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "user")

        if role == "tool":
            # Anthropic expects tool results as user messages with content blocks
            converted.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg.get("content", ""),
                        }
                    ],
                }
            )
        elif role == "assistant" and "tool_calls" in msg:
            # Rebuild assistant message with tool_use content blocks
            content_blocks: list[dict[str, Any]] = []
            text = msg.get("content")
            if text:
                content_blocks.append({"type": "text", "text": text})
            for tc in msg["tool_calls"]:
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": tc["function"]["arguments"]
                        if isinstance(tc["function"]["arguments"], dict)
                        else json.loads(tc["function"]["arguments"]),
                    }
                )
            converted.append({"role": "assistant", "content": content_blocks})
        else:
            # Plain user or assistant text message
            converted.append({"role": role, "content": msg.get("content", "")})

    return converted


class AnthropicProvider:
    """LLM provider backed by the Anthropic Messages API.

    Implements the :class:`LLMProvider` protocol.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    # -----------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        anthropic_tools = _convert_tools(tools) if tools else []
        anthropic_messages = _convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        if stream:
            return await self._stream_chat(kwargs, stream_callback)
        return await self._blocking_chat(kwargs)

    # -----------------------------------------------------------------

    async def _blocking_chat(self, kwargs: dict[str, Any]) -> LLMResponse:
        response = await self._client.messages.create(**kwargs)
        return self._parse_response(response)

    async def _stream_chat(
        self,
        kwargs: dict[str, Any],
        callback: Optional[Callable[[str], None]],
    ) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        input_tokens = 0
        output_tokens = 0

        # Track in-progress tool_use blocks
        current_tool_id: Optional[str] = None
        current_tool_name: Optional[str] = None
        current_tool_json: list[str] = []

        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "message_start":
                    usage = getattr(event.message, "usage", None)
                    if usage:
                        input_tokens = getattr(usage, "input_tokens", 0)

                elif event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        current_tool_id = block.id
                        current_tool_name = block.name
                        current_tool_json = []

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        text_parts.append(delta.text)
                        if callback:
                            callback(delta.text)
                    elif delta.type == "input_json_delta":
                        current_tool_json.append(delta.partial_json)

                elif event.type == "content_block_stop":
                    if current_tool_id is not None:
                        raw_json = "".join(current_tool_json)
                        arguments = json.loads(raw_json) if raw_json else {}
                        tool_calls.append(
                            ToolCall(
                                id=current_tool_id,
                                name=current_tool_name or "",
                                arguments=arguments,
                            )
                        )
                        current_tool_id = None
                        current_tool_name = None
                        current_tool_json = []

                elif event.type == "message_delta":
                    usage = getattr(event, "usage", None)
                    if usage:
                        output_tokens = getattr(usage, "output_tokens", 0)

        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # -----------------------------------------------------------------

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else json.loads(block.input),
                    )
                )

        usage = response.usage
        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
        )

    # -----------------------------------------------------------------

    async def analyze_visual(
        self,
        file_base64: str,
        media_type: str,
        prompt: str,
    ) -> str:
        """Analyze a visual file (PDF or image) using Claude."""
        if media_type == "application/pdf":
            content_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": file_base64,
                },
            }
        else:
            content_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": file_base64,
                },
            }

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return response.content[0].text
