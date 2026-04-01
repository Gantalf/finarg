"""Status bar widget showing connection status and rates."""

from __future__ import annotations

from datetime import datetime

from textual.reactive import reactive
from textual.widgets import Static


class StatusBar(Static):
    """Bottom status bar with connection indicators and quick info."""

    status_text: reactive[str] = reactive("")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "status-bar"
        self._ripio_ok = False
        self._dolar_rate = "---"

    def render(self) -> str:
        ripio = "\u25cf Connected" if self._ripio_ok else "\u25cb Disconnected"
        now = datetime.now().strftime("%H:%M")
        return f" Ripio {ripio}  \u2502  USD/ARS {self._dolar_rate}  \u2502  {now}"

    def set_ripio_status(self, connected: bool) -> None:
        self._ripio_ok = connected
        self.refresh()

    def set_dolar_rate(self, rate: str) -> None:
        self._dolar_rate = rate
        self.refresh()
