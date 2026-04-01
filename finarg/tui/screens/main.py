"""Main dashboard screen — portfolio left, chat right."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static
from textual.worker import Worker, WorkerState

from finarg.tui.widgets.balance_table import BalanceTable
from finarg.tui.widgets.braille_chart import BrailleChart
from finarg.tui.widgets.chat_view import ChatView
from finarg.tui.widgets.status_bar import StatusBar
from finarg.tui.widgets.ticker_bar import TickerBar

if TYPE_CHECKING:
    from finarg.agent.loop import FinargAgent


class MainScreen(Screen):
    """Two-column dashboard: sidebar (portfolio) + chat panel."""

    CSS_PATH = None  # loaded from app-level CSS
    BINDINGS = [
        ("ctrl+p", "command_palette", "Command Palette"),
        ("ctrl+l", "clear_chat", "Clear Chat"),
        ("escape", "focus_input", "Focus Input"),
    ]

    def __init__(self, agent: FinargAgent | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._agent = agent
        self._processing = False

    def compose(self) -> ComposeResult:
        yield TickerBar()
        with Horizontal(id="main-container"):
            with Vertical(id="sidebar"):
                yield Static(" PORTFOLIO ", classes="panel-header")
                yield BalanceTable()
                yield Static(" BTC 24H ", classes="panel-header")
                yield BrailleChart(title="BTC/USDT", id="btc-chart")
                yield Static(" ACTIVITY ", classes="panel-header")
                yield Static(
                    " No recent activity",
                    id="activity",
                )
            with Vertical(id="chat-panel"):
                yield ChatView()
                with Horizontal(id="chat-input"):
                    yield Input(placeholder="Ask Finarg anything...", id="user-input")
        yield StatusBar()

    def on_mount(self) -> None:
        self.query_one("#user-input", Input).focus()
        # Kick off initial data load
        self.set_timer(0.5, self._initial_load)

    async def _initial_load(self) -> None:
        """Load initial data after mount."""
        # These will fail gracefully if no API keys are configured
        chat = self.query_one(ChatView)
        status = self.query_one(StatusBar)

        if self._agent and self._agent.config.has_ripio():
            status.set_ripio_status(True)
        else:
            status.set_ripio_status(False)
            chat.add_agent_message(
                "*No Ripio API keys configured.* Run `finarg init` to set up. "
                "You can still chat and check dollar rates (BCRA is public)."
            )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user sending a message."""
        message = event.value.strip()
        if not message or self._processing:
            return

        input_widget = self.query_one("#user-input", Input)
        input_widget.value = ""

        chat = self.query_one(ChatView)
        chat.add_user_message(message)

        if not self._agent:
            chat.add_error("Agent not initialized. Run `finarg init` first.")
            return

        self._processing = True
        input_widget.placeholder = "Thinking..."

        # Run agent in a worker thread so the TUI stays responsive
        self.run_worker(
            self._run_agent(message),
            name="agent_worker",
            exclusive=True,
        )

    async def _run_agent(self, message: str) -> str:
        """Run the agent conversation (called in worker thread context)."""
        return await self._agent.run_conversation(
            user_message=message,
            tool_callback=self._on_tool_event,
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker completion."""
        if event.worker.name != "agent_worker":
            return

        chat = self.query_one(ChatView)
        input_widget = self.query_one("#user-input", Input)

        if event.state == WorkerState.SUCCESS:
            chat.add_agent_message(event.worker.result)
        elif event.state == WorkerState.ERROR:
            chat.add_error(str(event.worker.error))

        if event.state in (WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED):
            self._processing = False
            input_widget.placeholder = "Ask Finarg anything..."
            input_widget.focus()

    def _on_tool_event(self, event_type: str, tool_name: str, emoji: str = "\U0001f527") -> None:
        """Callback for tool call events from the agent."""
        chat = self.query_one(ChatView)
        if event_type == "call":
            chat.add_tool_call(tool_name, emoji)
        elif event_type == "result":
            chat.add_tool_result(tool_name)
        elif event_type == "error":
            chat.add_tool_result(tool_name, success=False)

    def action_clear_chat(self) -> None:
        chat = self.query_one(ChatView)
        chat.clear()
        chat.on_mount()  # re-render welcome banner

    def action_focus_input(self) -> None:
        self.query_one("#user-input", Input).focus()
