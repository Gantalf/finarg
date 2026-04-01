"""Base API client with rate limiting, retries, and auth hooks."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


class FinargAPIError(Exception):
    """Raised when an API request returns a non-2xx status code."""

    def __init__(self, status_code: int, message: str, response_body: Any = None) -> None:
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")


def _is_retryable(exc: BaseException) -> bool:
    """Return True for errors that should trigger a retry."""
    if isinstance(exc, FinargAPIError):
        return exc.status_code in {429, 500, 502, 503}
    if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout)):
        return True
    return False


class BaseAPIClient:
    """Async HTTP client with rate limiting, retries, and pluggable auth.

    Subclasses override ``_build_auth_headers`` to inject credentials.
    """

    def __init__(
        self,
        base_url: str,
        rate_limit: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._rate_limit = rate_limit
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(1)
        self._last_request_time: float = 0.0
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # Auth hook
    # ------------------------------------------------------------------

    def _build_auth_headers(
        self,
        method: str,
        path: str,
        body: str | None,
    ) -> dict[str, str]:
        """Return auth headers for the request.  Override in subclasses."""
        return {}

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Send an HTTP request with rate limiting, auth, and retries."""

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )
        async def _do_request() -> dict:
            async with self._semaphore:
                # Rate limiting
                now = time.monotonic()
                elapsed = now - self._last_request_time
                if elapsed < self._rate_limit:
                    await asyncio.sleep(self._rate_limit - elapsed)
                self._last_request_time = time.monotonic()

            # Build auth headers
            body: str | None = None
            if "json" in kwargs:
                import json as _json

                body = _json.dumps(kwargs["json"], separators=(",", ":"))
            elif "content" in kwargs:
                body = kwargs["content"] if isinstance(kwargs["content"], str) else None

            auth_headers = self._build_auth_headers(method.upper(), path, body)
            headers = {**kwargs.pop("headers", {}), **auth_headers}

            response = await self._client.request(
                method.upper(),
                path,
                headers=headers,
                **kwargs,
            )

            if not (200 <= response.status_code < 300):
                try:
                    resp_body = response.json()
                except Exception:
                    resp_body = response.text
                raise FinargAPIError(
                    status_code=response.status_code,
                    message=response.reason_phrase or "Request failed",
                    response_body=resp_body,
                )

            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

        return await _do_request()

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    async def get(self, path: str, **kwargs: Any) -> dict:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> dict:
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> dict:
        return await self._request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> dict:
        return await self._request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def __aenter__(self) -> BaseAPIClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
