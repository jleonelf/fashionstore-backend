import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

@pytest.fixture
async def cliente_http() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
