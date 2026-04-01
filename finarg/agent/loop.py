"""Core agent conversation loop."""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from finarg.agent.prompt_builder import build_system_prompt
from finarg.agent.providers.base import LLMProvider, LLMResponse, ToolCall
from finarg.agent.session import SessionStore
from finarg.config.loader import FinargConfig
from finarg.tools.registry import ToolRegistry

log = logging.getLogger(__name__)


class FinargAgent:
    """Orchestrates the LLM <-> tool loop.

    The agent maintains a conversation with the model, dispatching tool calls
    through the :class:`ToolRegistry` until the model produces a final text
    response (no more tool calls).
    """

    def __init__(
        self,
        config: FinargConfig,
        provider: LLMProvider,
        registry: ToolRegistry,
        session_store: SessionStore,
        memory_store=None,
    ) -> None:
        self._config = config
        self._provider = provider
        self._registry = registry
        self._session_store = session_store
        self._memory_store = memory_store

    @property
    def config(self) -> FinargConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_conversation(
        self,
        user_message: str,
        session_id: str = "default",
        stream_callback: Optional[Callable[[str], None]] = None,
        tool_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> str:
        """Run a full conversation turn (possibly multiple LLM round-trips).

        Returns the final assistant text response.
        """
        # 1. Load or initialise session history
        messages = self._session_store.load_session(session_id) or []

        # 2. Append the new user message
        messages.append({"role": "user", "content": user_message})

        # 3. Build system prompt
        tools_summary = self._build_tools_summary()
        system = build_system_prompt(tools_summary=tools_summary, memory_store=self._memory_store)

        # 4. Get tool definitions for the provider
        tool_defs = self._registry.get_definitions()

        # 5. Agent loop
        max_turns = self._config.agent.max_turns
        for turn in range(max_turns):
            log.debug("Agent turn %d/%d", turn + 1, max_turns)

            response: LLMResponse = await self._provider.chat(
                messages=messages,
                tools=tool_defs,
                system=system,
                stream=stream_callback is not None,
                stream_callback=stream_callback,
            )

            # Build the assistant message for history
            assistant_msg = self._build_assistant_message(response)
            messages.append(assistant_msg)

            # No tool calls -> final response
            if not response.tool_calls:
                break

            # Dispatch each tool call
            for tc in response.tool_calls:
                log.info("Tool call: %s(%s)", tc.name, json.dumps(tc.arguments, ensure_ascii=False))
                entry = self._registry._tools.get(tc.name)
                emoji = entry.emoji if entry else "\U0001f527"
                if tool_callback:
                    tool_callback("call", tc.name, emoji)

                result = await self._registry.dispatch(tc.name, tc.arguments)
                log.debug("Tool result for %s: %s", tc.name, result[:200])

                is_error = '"error"' in result[:100]
                if tool_callback:
                    tool_callback("error" if is_error else "result", tc.name, emoji)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
        else:
            log.warning("Agent hit max turns (%d) without a final response", max_turns)

        # 6. Persist session
        self._session_store.save_session(session_id, messages)

        # 7. Return final text
        return response.content

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_tools_summary(self) -> str:
        """Create a human-readable tools summary for the system prompt."""
        entries = self._registry.list_tools()
        if not entries:
            return ""
        lines: list[str] = []
        for entry in entries:
            lines.append(f"- {entry.emoji} **{entry.name}**: {entry.description}")
        return "\n".join(lines)

    @staticmethod
    def _build_assistant_message(response: LLMResponse) -> dict:
        """Convert an LLMResponse into a message dict for history."""
        msg: dict = {"role": "assistant", "content": response.content or ""}

        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments,
                    },
                }
                for tc in response.tool_calls
            ]

        return msg
