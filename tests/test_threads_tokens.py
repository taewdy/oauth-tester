import pytest
import respx
from httpx import Response

from oauth_tester.clients.threads_tokens import ThreadsTokenService, ThreadsTokenError


@pytest.mark.asyncio
@respx.mock
async def test_exchange_success(monkeypatch):
    # Provide a client secret via constructor to avoid env coupling
    service = ThreadsTokenService(client_secret="secret")
    route = respx.get("https://graph.threads.net/access_token").mock(
        return_value=Response(200, json={
            "access_token": "LL-123",
            "token_type": "bearer",
            "expires_in": 5000,
        })
    )

    token = await service.exchange_long_lived("SL-abc")
    assert route.called
    assert token.access_token == "LL-123"
    assert token.token_type == "bearer"
    assert token.expires_in == 5000


@pytest.mark.asyncio
@respx.mock
async def test_exchange_error_raises():
    service = ThreadsTokenService(client_secret="secret")
    respx.get("https://graph.threads.net/access_token").mock(
        return_value=Response(400, json={"error": {"message": "Bad token"}})
    )

    with pytest.raises(ThreadsTokenError) as ei:
        await service.exchange_long_lived("SL-bad")
    assert "exchange" in str(ei.value).lower()


@pytest.mark.asyncio
@respx.mock
async def test_refresh_success():
    service = ThreadsTokenService()
    respx.get("https://graph.threads.net/refresh_access_token").mock(
        return_value=Response(200, json={
            "access_token": "LL-456",
            "token_type": "bearer",
            "expires_in": 6000,
        })
    )

    token = await service.refresh_long_lived("LL-old")
    assert token.access_token == "LL-456"
    assert token.expires_in == 6000

