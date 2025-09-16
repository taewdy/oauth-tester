from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import httpx

from oauth_tester.settings import get_settings


class ThreadsTokenError(Exception):
    """Domain error for Threads token exchange/refresh failures."""

    def __init__(self, message: str, status_code: int | None = None, details: Dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class LongLivedToken:
    access_token: str
    token_type: str
    expires_in: int


class ThreadsTokenService:
    """Service for exchanging and refreshing Threads long-lived tokens.

    Responsibilities:
    - Exchange short-lived token for long-lived token via Threads Graph API
    - Refresh an existing long-lived token
    """

    def __init__(self, base_url: str | None = None, client_secret: str | None = None, timeout: float = 10.0):
        s = get_settings()
        self._base_url = base_url or str(s.oauth.threads_graph_base_url)
        self._client_secret = client_secret or (s.oauth.client_secret or "")
        self._timeout = timeout

    async def exchange_long_lived(self, short_lived_token: str) -> LongLivedToken:
        """Exchange short-lived token for long-lived token.

        GET {base}/access_token?grant_type=th_exchange_token&client_secret=...&access_token=...
        """
        if not short_lived_token:
            raise ThreadsTokenError("Missing short-lived access token")
        if not self._client_secret:
            raise ThreadsTokenError("Missing client secret for exchange")

        url = f"{self._base_url}/access_token"
        params = {
            "grant_type": "th_exchange_token",
            "client_secret": self._client_secret,
            "access_token": short_lived_token,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params=params)
        except Exception as e:
            raise ThreadsTokenError(f"Network error during token exchange: {e}") from e

        if resp.status_code >= 300:
            details = _safe_json(resp)
            raise ThreadsTokenError("Token exchange failed", status_code=resp.status_code, details=details)

        data = _safe_json(resp)
        return _parse_long_token(data)

    async def refresh_long_lived(self, long_lived_token: str) -> LongLivedToken:
        """Refresh long-lived token to extend validity by 60 days.

        GET {base}/refresh_access_token?grant_type=th_refresh_token&access_token=...
        """
        if not long_lived_token:
            raise ThreadsTokenError("Missing long-lived access token")

        url = f"{self._base_url}/refresh_access_token"
        params = {
            "grant_type": "th_refresh_token",
            "access_token": long_lived_token,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params=params)
        except Exception as e:
            raise ThreadsTokenError(f"Network error during token refresh: {e}") from e

        if resp.status_code >= 300:
            details = _safe_json(resp)
            raise ThreadsTokenError("Token refresh failed", status_code=resp.status_code, details=details)

        data = _safe_json(resp)
        return _parse_long_token(data)


def _safe_json(resp: httpx.Response) -> Dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {"text": resp.text}


def _parse_long_token(data: Dict[str, Any]) -> LongLivedToken:
    try:
        access_token = str(data["access_token"]).strip()
        token_type = str(data.get("token_type", "bearer"))
        expires_in = int(data.get("expires_in", 0))
        if not access_token:
            raise ValueError("empty access_token")
        return LongLivedToken(access_token=access_token, token_type=token_type, expires_in=expires_in)
    except Exception as e:
        raise ThreadsTokenError(f"Unexpected response format: {e}")

