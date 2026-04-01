"""Base protocol and data types for LLM providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Callable, Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        stream: bool = False,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse: ...
