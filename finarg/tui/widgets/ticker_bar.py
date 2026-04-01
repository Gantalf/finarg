"""Scrolling ticker bar showing crypto prices."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class TickerBar(Static):
    """Horizontal ticker showing live prices."""

    ticker_text: reactive[str] = reactive("FINARG v0.1.0  |  Loading prices...")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "ticker-bar"

    def render(self) -> str:
        return self.ticker_text

    def update_prices(self, prices: dict[str, str]) -> None:
        """Update ticker with new prices. prices = {"BTC": "$67,432", "ETH": "$3,521"}."""
        parts = ["FINARG v0.1.0"]
        for symbol, price in prices.items():
            parts.append(f"{symbol} {price}")
        self.ticker_text = "  \u2502  ".join(parts)
