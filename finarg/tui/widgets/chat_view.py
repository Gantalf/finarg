"""Chat view widget for agent conversation."""

from __future__ import annotations

from rich.markdown import Markdown
from rich.text import Text
from textual.widgets import RichLog


class ChatView(RichLog):
    """Scrolling log that displays the agent conversation with rich formatting."""

    def __init__(self, **kwargs) -> None:
        super().__init__(markup=True, wrap=True, highlight=True, **kwargs)
        self.id = "chat-log"

    def on_mount(self) -> None:
        self.write(
            Text.from_markup(
                "[bold #e94560]\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
                "\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
                "\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557[/]\n"
                "[bold #e94560]\u2551[/]  [bold #00ff88]FINARG[/] "
                "[#8892b0]Financial AI Agent[/]   [bold #e94560]\u2551[/]\n"
                "[bold #e94560]\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
                "\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
                "\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d[/]\n"
                "[#8892b0]Type a message to chat with your agent.[/]\n"
            )
        )

    def add_user_message(self, text: str) -> None:
        """Display a user message."""
        self.write(Text.from_markup(f"\n[bold #4fc3f7]\u25b6 You:[/] {text}"))

    def add_agent_message(self, text: str) -> None:
        """Display an agent response (supports markdown)."""
        self.write(Text(""))
        self.write(Markdown(text))

    def add_tool_call(self, tool_name: str, emoji: str = "\U0001f527") -> None:
        """Display a tool call indicator."""
        self.write(
            Text.from_markup(f"  [italic #ffa726]{emoji} Calling {tool_name}...[/]")
        )

    def add_tool_result(self, tool_name: str, success: bool = True) -> None:
        """Display tool result status."""
        icon = "\u2713" if success else "\u2717"
        color = "#00ff88" if success else "#ff4444"
        self.write(
            Text.from_markup(f"  [{color}]{icon} {tool_name} done[/]")
        )

    def add_error(self, message: str) -> None:
        """Display an error message."""
        self.write(Text.from_markup(f"\n[bold #ff4444]\u26a0 Error:[/] {message}"))

    def stream_start(self) -> None:
        """Start streaming a new agent response."""
        self.write(Text(""))

    def stream_append(self, text: str) -> None:
        """Append text to the current streaming response."""
        # RichLog doesn't support appending to last line natively,
        # so we use write for each chunk. For a smoother experience,
        # a custom widget could be used.
        self.write(Text(text), shrink=True)
