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
