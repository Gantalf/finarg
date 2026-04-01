"""Finarg TUI application root."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App

from finarg.tui.screens.main import MainScreen

if TYPE_CHECKING:
    from finarg.agent.loop import FinargAgent

THEME_PATH = Path(__file__).parent / "tui" / "themes" / "dark.tcss"


class FinargApp(App):
    """The Finarg terminal application."""

    TITLE = "Finarg"
    SUB_TITLE = "AI Financial Agent"
    CSS_PATH = THEME_PATH
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+p", "command_palette", "Commands"),
    ]

    def __init__(self, agent: FinargAgent | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._agent = agent

    def on_mount(self) -> None:
        self.push_screen(MainScreen(agent=self._agent))
