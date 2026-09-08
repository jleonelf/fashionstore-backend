import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
import app  # Inicializa alias de módulo para ejecuciones aisladas
from backend.app.main import app

@pytest.fixture
async def cliente_http() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # auto-login como admin para tests que requieren RBAC
        try:
            resp = await client.post("/api/v1/sesion", json={"correo_electronico": "admin@fashionstore.com", "contrasenia": "admin123456"})
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                if token:
                    client.headers["Authorization"] = f"Bearer {token}"
        except Exception:
            pass
        yield client
