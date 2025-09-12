import pytest
import httpx
from httpx import AsyncClient

from oauth_tester.app import create_app


@pytest.mark.asyncio
async def test_logout_redirect():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        resp = await ac.get("/auth/logout")
        assert resp.status_code in (302, 307, 303)
        assert resp.headers.get("location") == "/"
