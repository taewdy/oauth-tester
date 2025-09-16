import os
import pytest
import httpx
from httpx import AsyncClient

from oauth_tester.app import create_app
from oauth_tester.settings.config import get_settings


@pytest.mark.asyncio
async def test_exchange_requires_short_token(monkeypatch):
    # Ensure provider is threads
    os.environ["OAUTH_TESTER__OAUTH__PROVIDER_NAME"] = "threads"
    # Ensure settings reload for this test
    get_settings.cache_clear()  # type: ignore[attr-defined]

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        # No session short token set
        resp = await ac.post("/auth/long-token/exchange")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_refresh_requires_long_token():
    os.environ["OAUTH_TESTER__OAUTH__PROVIDER_NAME"] = "threads"
    get_settings.cache_clear()  # type: ignore[attr-defined]

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        resp = await ac.post("/auth/long-token/refresh")
        assert resp.status_code == 400

