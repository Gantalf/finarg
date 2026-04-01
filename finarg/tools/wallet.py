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


async def get_wallet_balances(args: dict) -> str:
    """Fetch balances from Ripio Wallet (the app, not the trading account)."""
    from finarg.api.ripio_trade import get_trade_client

    client = get_trade_client()
    balances = await client.get_ripio_wallet_balances()
    if not balances:
        return json.dumps({"message": "Ripio Wallet is empty."})
    return json.dumps(balances, ensure_ascii=False)


async def wallet_transfer(args: dict) -> str:
    """Transfer funds between Ripio Wallet and Ripio Trade."""
    from finarg.api.ripio_trade import get_trade_client

    currency = args.get("currency", "").upper()
    amount = args.get("amount", "")
    direction = args.get("direction", "")

    if not all([currency, amount, direction]):
        return json.dumps({"error": "currency, amount, and direction are all required"})

    if direction not in ("FROM_WALLET", "TO_WALLET"):
        return json.dumps({"error": "direction must be FROM_WALLET or TO_WALLET"})

    client = get_trade_client()
    result = await client.wallet_transfer(currency, amount, direction)
    return json.dumps(result, ensure_ascii=False)


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

    registry.register(
        name="get_wallet_balances",
        toolset="wallet",
        description=(
            "Get balances from your Ripio Wallet (the app). "
            "This is different from get_balances which shows Trading account balances. "
            "Returns currency_code and amount for each asset."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=get_wallet_balances,
        emoji="\U0001f4f1",
    )

    registry.register(
        name="wallet_transfer",
        toolset="wallet",
        description=(
            "Transfer funds between Ripio Wallet (app) and Ripio Trade (exchange). "
            "Use direction FROM_WALLET to move funds from Wallet to Trade (to start trading). "
            "Use direction TO_WALLET to move funds from Trade back to Wallet. "
            "IMPORTANT: Always confirm with the user before executing."
        ),
        parameters={
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "description": "Currency to transfer (e.g. BTC, USDC, ETH)",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount to transfer (string for precision)",
                },
                "direction": {
                    "type": "string",
                    "enum": ["FROM_WALLET", "TO_WALLET"],
                    "description": "FROM_WALLET = Wallet→Trade, TO_WALLET = Trade→Wallet",
                },
            },
            "required": ["currency", "amount", "direction"],
        },
        handler=wallet_transfer,
        emoji="\U0001f500",
    )
