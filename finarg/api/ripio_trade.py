"""Ripio Trade API client."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from urllib.parse import urlparse

from finarg.api.base import BaseAPIClient

_client: RipioTradeClient | None = None


def get_trade_client() -> RipioTradeClient:
    """Get or create the singleton Ripio Trade client."""
    global _client
    if _client is None:
        api_key = os.getenv("RIPIO_TRADE_API_KEY", "")
        api_secret = os.getenv("RIPIO_TRADE_API_SECRET", "")
        if not api_key or not api_secret:
            raise RuntimeError("Ripio Trade API keys not configured. Run `finarg init`.")
        _client = RipioTradeClient(api_key, api_secret)
    return _client


class RipioTradeClient(BaseAPIClient):
    """Client for the Ripio Trade API.

    Authentication uses HMAC-SHA256 signatures per Ripio's spec:
    https://apidocs.ripio.com/static/api/authentication
    """

    BASE_URL = "https://api.ripio.com"

    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(base_url=self.BASE_URL)
        self._api_key = api_key
        self._api_secret = api_secret

    # ------------------------------------------------------------------
    # Auth — matches Ripio's official Python example exactly
    # ------------------------------------------------------------------

    def _build_auth_headers(
        self,
        method: str,
        path: str,
        body: str | None,
    ) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))

        # For GET: strip query params from path when signing
        sign_path = urlparse(path).path.split("?")[0] if "?" in path else path

        # Build message: timestamp + METHOD + path + body
        message = f"{timestamp}{method.upper()}{sign_path}{body or ''}"

        # HMAC-SHA256 → raw bytes → base64
        signature = base64.b64encode(
            hmac.new(
                self._api_secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).digest()
        ).decode()

        return {
            "Content-Type": "application/json",
            "Authorization": self._api_key,
            "Timestamp": timestamp,
            "Signature": signature,
        }

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    async def get_ticker(self, pair: str) -> dict:
        """Get ticker data for a specific trading pair."""
        return await self.get(f"/trade/tickers/{pair}")

    async def get_tickers(self) -> list[dict]:
        """Get ticker data for all trading pairs."""
        return await self.get("/trade/tickers")  # type: ignore[return-value]

    async def get_pairs(self) -> list[dict]:
        """Get all available trading pairs."""
        return await self.get("/trade/pairs")  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Authenticated endpoints
    # ------------------------------------------------------------------

    async def get_balances(self) -> list[dict]:
        """Get wallet balances for the authenticated user."""
        return await self.get("/trade/balances")  # type: ignore[return-value]

    async def get_deposit_address(self, currency: str) -> dict:
        """Get deposit address for a given currency."""
        return await self.get("/trade/wallets", params={"currency": currency})

    async def create_withdrawal(
        self,
        currency: str,
        address: str,
        amount: str,
        network: str | None = None,
    ) -> dict:
        """Create a crypto withdrawal."""
        payload: dict = {
            "currency": currency,
            "address": address,
            "amount": amount,
        }
        if network is not None:
            payload["network"] = network
        return await self.post("/trade/withdrawals", json=payload)

    async def estimate_withdrawal_fee(self, currency: str, amount: str) -> dict:
        """Estimate the fee for a withdrawal."""
        return await self.get(
            "/trade/withdrawals/estimate-fee",
            params={"currency": currency, "amount": amount},
        )
