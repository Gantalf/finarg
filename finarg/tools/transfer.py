"""Transfer tools: send crypto to external wallets."""

from __future__ import annotations

import json


async def withdraw_crypto(args: dict) -> str:
    """Send crypto to an external wallet. The agent MUST confirm with the user before calling this."""
    from finarg.api.ripio_trade import get_trade_client

    currency_code = args.get("currency_code", "").upper()
    destination = args.get("destination", "")
    amount = args.get("amount")
    network = args.get("network")
    fee_included = args.get("fee_included", True)
    tag = args.get("tag")
    memo = args.get("memo")

    if not all([currency_code, destination, amount]):
        return json.dumps({"error": "currency_code, destination, and amount are all required"})

    client = get_trade_client()

    # Estimate the fee first
    try:
        fee_info = await client.estimate_withdrawal_fee(
            currency_code, amount=str(amount), network=network,
        )
    except Exception:
        fee_info = {"note": "Could not estimate fee"}

    # Execute the withdrawal
    result = await client.create_withdrawal(
        currency_code=currency_code,
        destination=destination,
        amount=str(amount),
        network=network,
        fee_included=fee_included,
        tag=tag,
        memo=memo,
    )

    if isinstance(result, dict):
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
            "IMPORTANT: Always show the user a summary (currency, amount, destination, estimated fee) "
            "and get explicit confirmation before calling this tool."
        ),
        parameters={
            "type": "object",
            "properties": {
                "currency_code": {
                    "type": "string",
                    "description": "Cryptocurrency to send (e.g. BTC, ETH, USDC)",
                },
                "destination": {
                    "type": "string",
                    "description": "Recipient wallet address",
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to send",
                },
                "network": {
                    "type": "string",
                    "description": "Blockchain network (e.g. ethereum, polygon). Optional.",
                },
                "fee_included": {
                    "type": "boolean",
                    "description": "Whether fee deducts from amount (default true)",
                },
                "tag": {
                    "type": "string",
                    "description": "Destination tag (for currencies like XRP). Optional.",
                },
                "memo": {
                    "type": "string",
                    "description": "Destination memo (for currencies like XLM). Optional.",
                },
            },
            "required": ["currency_code", "destination", "amount"],
        },
        handler=withdraw_crypto,
        emoji="\U0001f4e4",
    )
