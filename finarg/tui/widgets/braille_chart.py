"""Braille sparkline chart widget for price history."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

# Braille dot patterns for sparkline rendering.
# Each braille character is a 2x4 grid of dots (U+2800-U+28FF).
# We use the bottom row of dots for a simple sparkline.
BARS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


class BrailleChart(Static):
    """Sparkline chart using Unicode block characters."""

    data: reactive[list[float]] = reactive(list, always_update=True)

    def __init__(self, title: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self.add_class("braille-chart")

    def render(self) -> str:
        values = self.data
        if not values or len(values) < 2:
            return f"{self._title}\n{'.' * 40}"

        lo = min(values)
        hi = max(values)
        span = hi - lo if hi != lo else 1.0

        # Map each value to a bar character
        chars = []
        for v in values:
            idx = int((v - lo) / span * (len(BARS) - 1))
            chars.append(BARS[idx])

        sparkline = "".join(chars)

        # Color indicator: green if last > first, red if down
        change = values[-1] - values[0]
        direction = "\u25b2" if change >= 0 else "\u25bc"
        pct = (change / values[0] * 100) if values[0] else 0

        header = f"{self._title}  {direction} {pct:+.1f}%"
        return f"{header}\n{sparkline}"

    def update_data(self, new_data: list[float]) -> None:
        """Set new chart data points."""
        self.data = list(new_data)
