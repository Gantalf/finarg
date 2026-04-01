"""Balance table widget showing wallet holdings."""

from __future__ import annotations

from textual.widgets import DataTable


class BalanceTable(DataTable):
    """Rich table displaying wallet balances."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "balance-table"
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self) -> None:
        self.add_columns("Asset", "Balance", "USD Value")
        self.add_row("---", "Loading...", "---")

    def update_balances(self, balances: list[dict]) -> None:
        """Update table with balance data from Ripio API."""
        self.clear()
        if not balances:
            self.add_row("---", "No assets", "---")
            return

        for b in balances:
            symbol = b.get("currency", b.get("coin", "???"))
            available = b.get("available", "0")
            # USD value would come from ticker data; placeholder for now
            usd = b.get("usd_value", "---")
            self.add_row(symbol, available, usd)
