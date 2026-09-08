"""Campus-library detection preserves proxy policy and validates direct retries."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.api.v1 import network

LIBRARY_URL = "https://lib.lut.edu.cn/"


def response(status: int, url: str = LIBRARY_URL, **kwargs) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("GET", url), **kwargs)


@pytest.mark.asyncio
async def test_library_retries_directly_after_proxy_connection_failure(monkeypatch):
    monkeypatch.setattr(network, "validate_url", lambda _url: (True, None))
    proxied = AsyncMock()
    proxied.get.side_effect = httpx.ConnectError("proxy failed")
    direct = AsyncMock()
    direct.get.return_value = response(200)
    direct.__aenter__.return_value = direct
    # AsyncClient is a synchronous constructor returning an async context manager.
    factory = Mock(return_value=direct)
    monkeypatch.setattr(network.httpx, "AsyncClient", factory)

    name, ok, detail = await network._check_library_url(proxied, LIBRARY_URL)

    assert (name, ok) == ("library", True)
    assert detail["direct_retry"] is True
    assert detail["initial_error"] == "ConnectError"
    factory.assert_called_once_with(timeout=8, trust_env=False)
    direct.get.assert_awaited_once_with(LIBRARY_URL, follow_redirects=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 403, 429])
async def test_library_does_not_retry_success_or_http_denial(monkeypatch, status):
    monkeypatch.setattr(network, "validate_url", lambda _url: (True, None))
    client = AsyncMock()
    client.get.return_value = response(status)
    factory = AsyncMock()
    monkeypatch.setattr(network.httpx, "AsyncClient", factory)

    _, ok, detail = await network._check_library_url(client, LIBRARY_URL)

    assert ok is (status == 200)
    assert detail["status_code"] == status
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_library_rejects_unsafe_redirect_before_request(monkeypatch):
    private_url = "https://192.168.1.1/"
    monkeypatch.setattr(
        network, "validate_url",
        lambda url: (url != private_url, "private address" if url == private_url else None),
    )
    client = AsyncMock()
    client.get.return_value = response(302, headers={"location": private_url})
    factory = AsyncMock()
    monkeypatch.setattr(network.httpx, "AsyncClient", factory)

    _, ok, detail = await network._check_library_url(client, LIBRARY_URL)

    assert ok is False
    assert detail["error"] == "UnsafeURL"
    client.get.assert_awaited_once_with(LIBRARY_URL, follow_redirects=False)
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_direct_retry_also_rejects_unsafe_redirect(monkeypatch):
    private_url = "https://192.168.1.1/"
    monkeypatch.setattr(
        network, "validate_url",
        lambda url: (url != private_url, "private address" if url == private_url else None),
    )
    proxied = AsyncMock()
    proxied.get.side_effect = httpx.ConnectError("proxy failed")
    direct = AsyncMock()
    direct.get.return_value = response(302, headers={"location": private_url})
    direct.__aenter__.return_value = direct
    monkeypatch.setattr(network.httpx, "AsyncClient", Mock(return_value=direct))

    _, ok, detail = await network._check_library_url(proxied, LIBRARY_URL)

    assert ok is False
    assert detail["direct_retry"] is True
    assert detail["error"] == "UnsafeURL"
    direct.get.assert_awaited_once_with(LIBRARY_URL, follow_redirects=False)


@pytest.mark.asyncio
async def test_other_sources_keep_existing_proxy_behavior():
    client = AsyncMock()
    client.get.side_effect = httpx.ConnectError("proxy failed")

    name, ok, detail = await network._check_url(client, "crossref", "https://api.crossref.org/")

    assert (name, ok, detail["error"]) == ("crossref", False, "ConnectError")
    client.get.assert_awaited_once_with("https://api.crossref.org/")
