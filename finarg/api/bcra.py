"""BCRA (Banco Central de la Republica Argentina) public API client."""
from __future__ import annotations

from finarg.api.base import BaseAPIClient

_client: BCRAClient | None = None


def get_bcra_client() -> BCRAClient:
    """Get or create the singleton BCRA client."""
    global _client
    if _client is None:
        _client = BCRAClient()
    return _client


class BCRAClient(BaseAPIClient):
    """Client for the BCRA public statistics API.

    No authentication is required.
    """

    BASE_URL = "https://api.bcra.gob.ar"

    def __init__(self) -> None:
        super().__init__(base_url=self.BASE_URL)

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    async def get_exchange_rates(self) -> list[dict]:
        """Get exchange rates (oficial, blue, MEP, etc.)."""
        return await self.get(  # type: ignore[return-value]
            "/estadisticas/v3/monetarias/tipos-de-cambio",
        )

    async def get_principales_variables(self) -> list[dict]:
        """Get main economic variables published by the BCRA."""
        return await self.get(  # type: ignore[return-value]
            "/estadisticas/v2.0/principalesvariables",
        )
