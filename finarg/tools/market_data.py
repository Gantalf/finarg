"""Market data tools: crypto prices and Argentine exchange rates."""

from __future__ import annotations

import json


async def get_ticker(args: dict) -> str:
    """Get current price/stats for a trading pair."""
    from finarg.api.ripio_trade import get_trade_client

    pair = args.get("pair", "").upper()
    client = get_trade_client()

    if pair:
        ticker = await client.get_ticker(pair)
        return json.dumps(ticker, ensure_ascii=False)
    else:
        tickers = await client.get_tickers()
        return json.dumps(tickers, ensure_ascii=False)


async def get_dolar_rates(args: dict) -> str:
    """Get current Argentine dollar exchange rates (oficial, blue, MEP)."""
    from finarg.api.bcra import get_bcra_client

    client = get_bcra_client()
    try:
        rates = await client.get_exchange_rates()
        return json.dumps(rates, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch BCRA rates: {e}"})


async def get_currencies(args: dict) -> str:
    """List available currencies with networks, withdrawal limits, and deposit/withdraw status."""
    from finarg.api.ripio_trade import get_trade_client

    currency_code = args.get("currency_code", "").upper() or None
    client = get_trade_client()
    currencies = await client.get_currencies(currency_code)

    # Simplify output for the agent
    simplified = []
    for c in currencies:
        entry = {
            "code": c.get("code"),
            "name": c.get("name"),
            "can_deposit": c.get("can_deposit"),
            "can_withdraw": c.get("can_withdraw"),
            "min_withdraw": c.get("min_withdraw_amount"),
            "precision": c.get("precision"),
        }
        networks = c.get("networks", [])
        if networks:
            entry["networks"] = [
                {
                    "code": n.get("code"),
                    "memo_deposit": n.get("memo", {}).get("deposit", False),
                    "memo_withdraw": n.get("memo", {}).get("withdrawal", False),
                    "tag_deposit": n.get("tag", {}).get("deposit", False),
                    "tag_withdraw": n.get("tag", {}).get("withdrawal", False),
                }
                for n in networks
            ]
        simplified.append(entry)

    return json.dumps(simplified, ensure_ascii=False)


def register_market_data_tools() -> None:
    """Register market data tools with the global registry."""
    from finarg.tools.registry import registry

    registry.register(
        name="get_ticker",
        toolset="market_data",
        description=(
            "Get current price and 24h stats for a crypto trading pair on Ripio. "
            "If no pair is specified, returns all available tickers."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pair": {
                    "type": "string",
                    "description": "Trading pair (e.g. BTC_USDT, ETH_ARS). Leave empty for all.",
                },
            },
            "required": [],
        },
        handler=get_ticker,
        emoji="\U0001f4c8",
    )

    registry.register(
        name="get_dolar_rates",
        toolset="market_data",
        description=(
            "Get current Argentine dollar exchange rates from BCRA. "
            "Returns official rate, blue dollar, and MEP/CCL rates."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=get_dolar_rates,
        emoji="\U0001f4b5",
    )

    registry.register(
        name="get_currencies",
        toolset="market_data",
        description=(
            "List available cryptocurrencies with their supported networks, "
            "deposit/withdraw status, minimum withdrawal amounts, and memo/tag requirements. "
            "Use this before a withdrawal to know which networks are available and their requirements. "
            "Optionally filter by currency_code."
        ),
        parameters={
            "type": "object",
            "properties": {
                "currency_code": {
                    "type": "string",
                    "description": "Filter by currency (e.g. BTC, USDC). Leave empty for all.",
                },
            },
            "required": [],
        },
        handler=get_currencies,
        emoji="\U0001f4b1",
    )
