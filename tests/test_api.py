import pytest
import httpx
from httpx import AsyncClient

from oauth_tester.app import create_app


@pytest.mark.asyncio
async def test_health_endpoint():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "oauth-tester"


@pytest.mark.asyncio
async def test_index_page():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
        assert resp.status_code == 200
