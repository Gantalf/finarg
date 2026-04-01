"""Wallet tools: balance and deposit address queries."""

from __future__ import annotations

import json


async def get_balances(args: dict) -> str:
    """Fetch all wallet balances from Ripio Trade."""
    from finarg.api.ripio_trade import get_trade_client

    client = get_trade_client()
    balances = await client.get_balances()
    # Filter out zero balances for cleaner output
    non_zero = [b for b in balances if float(b.get("available", 0)) > 0]
    if not non_zero:
        return json.dumps({"message": "No balances found. Your wallet is empty."})
    return json.dumps(non_zero, ensure_ascii=False)


async def get_deposit_address(args: dict) -> str:
    """Get deposit address for a specific cryptocurrency."""
    from finarg.api.ripio_trade import get_trade_client

    currency = args.get("currency", "").upper()
    if not currency:
        return json.dumps({"error": "currency is required"})

    client = get_trade_client()
    wallets = await client.get_deposit_address(currency)
    return json.dumps(wallets, ensure_ascii=False)


def register_wallet_tools() -> None:
    """Register wallet tools with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="get_balances",
        toolset="wallet",
        description="Get all cryptocurrency balances in your wallet. Returns coin, available balance, and locked balance for each asset with non-zero balance.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=get_balances,
        emoji="\U0001f4b0",
    )

    registry.register(
        name="get_deposit_address",
        toolset="wallet",
        description="Get the deposit address for a specific cryptocurrency to receive funds.",
        parameters={
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "description": "Cryptocurrency symbol (e.g. BTC, ETH, USDC)",
                },
            },
            "required": ["currency"],
        },
        handler=get_deposit_address,
        emoji="\U0001f4e5",
    )
