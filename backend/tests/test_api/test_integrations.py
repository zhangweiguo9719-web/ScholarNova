"""API tests for user-controlled research application integrations."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.paper import PaperEntity
from app.services.integrations.zotero import ZoteroAccessDeniedError, ZoteroStatus


@pytest.mark.asyncio
async def test_zotero_status_and_collections(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.integrations.ZoteroLocalClient.status",
        AsyncMock(return_value=ZoteroStatus(True, "server-1", "7.0")),
    )
    monkeypatch.setattr(
        "app.api.v1.integrations.ZoteroLocalClient.collections",
        AsyncMock(
            return_value=[
                {
                    "key": "ABC123",
                    "name": "AI Research",
                    "parent_collection": None,
                    "version": 4,
                }
            ]
        ),
    )

    status_response = await client.get("/api/v1/integrations/zotero/status")
    collection_response = await client.get("/api/v1/integrations/zotero/collections")

    assert status_response.status_code == 200
    assert status_response.json()["mode"] == "local_read_only"
    assert collection_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_zotero_status_reports_disabled_local_api(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.integrations.ZoteroLocalClient.status",
        AsyncMock(side_effect=ZoteroAccessDeniedError("Local API is not enabled")),
    )

    response = await client.get("/api/v1/integrations/zotero/status")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "zotero_api_disabled"


@pytest.mark.asyncio
async def test_zotero_import_is_idempotent(client, db_session, monkeypatch) -> None:
    item = {
        "key": "ITEM1234",
        "version": 7,
        "data": {
            "itemType": "journalArticle",
            "title": "Evidence-grounded Research Assistants",
            "abstractNote": "A test abstract.",
            "creators": [
                {"firstName": "Ada", "lastName": "Lovelace", "creatorType": "author"}
            ],
            "date": "2025-03-01",
            "publicationTitle": "Journal of Research Tools",
            "DOI": "https://doi.org/10.1000/Test.1",
            "url": "https://example.org/paper",
            "tags": [{"tag": "research agent"}],
            "collections": ["ABC123"],
        },
    }
    monkeypatch.setattr(
        "app.api.v1.integrations.ZoteroLocalClient.items",
        AsyncMock(return_value=[item]),
    )

    first = await client.post(
        "/api/v1/integrations/zotero/import",
        json={"collection_key": "ABC123", "limit": 50},
    )
    second = await client.post(
        "/api/v1/integrations/zotero/import",
        json={"collection_key": "ABC123", "limit": 50},
    )

    assert first.status_code == 200
    assert first.json()["created"] == 1
    assert first.json()["read_only"] is True
    assert second.json()["created"] == 0
    assert second.json()["updated"] == 1

    papers = (await db_session.execute(select(PaperEntity))).scalars().all()
    assert len(papers) == 1
    assert papers[0].doi == "10.1000/test.1"
    assert papers[0].author_names == ["Ada Lovelace"]
    assert papers[0].source == "zotero"
    assert papers[0].extra_metadata["zotero"]["key"] == "ITEM1234"
