"""Transfer tools: crypto withdrawals."""

from __future__ import annotations

import json


async def withdraw_crypto(args: dict) -> str:
    """Execute a crypto withdrawal. The agent MUST confirm with the user before calling this."""
    from finarg.api.ripio_trade import get_trade_client

    currency = args.get("currency", "").upper()
    address = args.get("address", "")
    amount = args.get("amount", "")
    network = args.get("network")

    if not all([currency, address, amount]):
        return json.dumps({"error": "currency, address, and amount are all required"})

    client = get_trade_client()

    # First estimate the fee
    fee_info = await client.estimate_withdrawal_fee(currency, amount)

    # Execute the withdrawal
    result = await client.create_withdrawal(
        currency=currency,
        address=address,
        amount=amount,
        network=network,
    )

    result["fee_estimate"] = fee_info
    return json.dumps(result, ensure_ascii=False)


def register_transfer_tools() -> None:
    """Register transfer tools with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="withdraw_crypto",
        toolset="transfer",
        description=(
            "Send cryptocurrency to an external wallet address. "
            "IMPORTANT: Always show the user a summary (currency, amount, address, estimated fee) "
            "and get explicit confirmation before calling this tool."
        ),
        parameters={
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "description": "Cryptocurrency to send (e.g. BTC, ETH, USDC)",
                },
                "address": {
                    "type": "string",
                    "description": "Destination wallet address",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount to send (as string to preserve precision)",
                },
                "network": {
                    "type": "string",
                    "description": "Network to use (e.g. ethereum, polygon). Optional.",
                },
            },
            "required": ["currency", "address", "amount"],
        },
        handler=withdraw_crypto,
        emoji="\U0001f4e4",
    )
