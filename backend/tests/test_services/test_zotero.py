"""Tests for the read-only Zotero local API client."""

from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.integrations.zotero import (
    ZoteroAccessDeniedError,
    ZoteroLocalClient,
)


def response(payload, headers=None) -> httpx.Response:
    return httpx.Response(
        200,
        json=payload,
        headers=headers or {},
        request=httpx.Request("GET", "http://127.0.0.1:23119/api/test"),
    )


@pytest.mark.asyncio
async def test_status_reads_server_identity() -> None:
    client = ZoteroLocalClient()
    client._get = AsyncMock(  # type: ignore[method-assign]
        return_value=response(
            [],
            {"Zotero-Server-ID": "local-library", "Zotero-Version": "7.0"},
        )
    )

    status = await client.status()

    assert status.connected is True
    assert status.server_id == "local-library"
    assert status.zotero_version == "7.0"


@pytest.mark.asyncio
async def test_collections_normalises_zotero_payload() -> None:
    client = ZoteroLocalClient()
    client._get = AsyncMock(  # type: ignore[method-assign]
        return_value=response(
            [
                {
                    "key": "ABC123",
                    "version": 2,
                    "data": {"name": "My Papers", "parentCollection": False},
                },
                {"key": "MISSING_NAME", "data": {}},
            ]
        )
    )

    collections = await client.collections()

    assert collections == [
        {
            "key": "ABC123",
            "name": "My Papers",
            "parent_collection": None,
            "version": 2,
        }
    ]


@pytest.mark.asyncio
async def test_items_excludes_children_and_rejects_unsafe_key() -> None:
    client = ZoteroLocalClient()
    client._get = AsyncMock(  # type: ignore[method-assign]
        return_value=response(
            [
                {"key": "PAPER1", "data": {"itemType": "journalArticle", "title": "A"}},
                {"key": "FILE1", "data": {"itemType": "attachment", "title": "PDF"}},
                {"key": "NOTE1", "data": {"itemType": "note"}},
            ]
        )
    )

    items = await client.items(collection_key="ABC123", limit=500)

    assert [item["key"] for item in items] == ["PAPER1"]
    called_path = client._get.await_args.args[0]  # type: ignore[attr-defined]
    called_params = client._get.await_args.kwargs["params"]  # type: ignore[attr-defined]
    assert called_path == "/users/0/collections/ABC123/items/top"
    assert called_params["limit"] == 100

    with pytest.raises(ValueError):
        await client.items(collection_key="../private")


@pytest.mark.asyncio
async def test_disabled_local_api_is_distinguished_from_missing_zotero(
    monkeypatch,
) -> None:
    async def disabled_response(*_args, **_kwargs):
        return httpx.Response(
            403,
            text="Local API is not enabled",
            request=httpx.Request("GET", "http://127.0.0.1:23119/api/test"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", disabled_response)

    with pytest.raises(ZoteroAccessDeniedError):
        await ZoteroLocalClient().status()
