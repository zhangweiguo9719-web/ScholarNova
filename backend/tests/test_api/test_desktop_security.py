"""Desktop IPC is private even when another site bypasses the UI proxy."""
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import DesktopSessionMiddleware


@pytest.mark.parametrize("provided,expected", [(None, 403), ("wrong", 403), ("test-session", 200)])
async def test_private_backend_requires_session(monkeypatch, provided, expected):
    monkeypatch.setenv("SCHOLARNOVA_DESKTOP_TOKEN", "test-session")
    app = FastAPI()
    app.add_middleware(DesktopSessionMiddleware)

    @app.get("/api/private")
    def private():
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app), base_url="http://localhost") as client:
        headers = {"x-scholarnova-session": provided} if provided else {}
        response = await client.get("/api/private", headers=headers)
        assert response.status_code == expected


async def test_unconfigured_desktop_fails_closed(monkeypatch):
    monkeypatch.delenv("SCHOLARNOVA_DESKTOP_TOKEN", raising=False)
    app = FastAPI()
    app.add_middleware(DesktopSessionMiddleware)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://localhost") as client:
        assert (await client.get("/api/private")).status_code == 403
