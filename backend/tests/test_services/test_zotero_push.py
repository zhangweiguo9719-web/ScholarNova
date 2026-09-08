"""Verify Connector save sessions never claim an unverified collection."""

from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.integrations.zotero import (
    ZoteroClientError,
    ZoteroLocalClient,
    ZoteroWriteUnverifiedError,
)


def saved_item(key="NEW123", collections=None):
    return {"key": key, "data": {"title": "Test paper", "collections": collections or []}}


def connector_selection(library_id=1, targets=None):
    return httpx.Response(200, json={
        "libraryID": library_id,
        "targets": targets or [
            {"id": "L1", "name": "My Library", "level": 0},
            {"id": "C7", "name": "Parent", "level": 1},
            {"id": "C8", "name": "Papers", "level": 2},
            {"id": "C9", "name": "Other", "level": 1},
            {"id": "C10", "name": "Papers", "level": 2},
        ],
    })


def target_client():
    client = ZoteroLocalClient()
    client._connector_post = AsyncMock(return_value=connector_selection())
    client.collections = AsyncMock(return_value=[
        {"key": "PARENT1", "name": "Parent", "parent_collection": None},
        {"key": "CHILD1", "name": "Papers", "parent_collection": "PARENT1"},
        {"key": "OTHER1", "name": "Other", "parent_collection": None},
        {"key": "CHILD2", "name": "Papers", "parent_collection": "OTHER1"},
    ])
    return client


@pytest.mark.asyncio
async def test_target_uses_full_path_not_leaf_name():
    client = target_client()
    assert await client._save_target("CHILD2") == "C10"
    assert await client._save_target("CHILD1") == "C8"
    assert await client._save_target(None) == "L1"


@pytest.mark.asyncio
async def test_ambiguous_collection_is_rejected_before_writing():
    client = target_client()
    client.collections.return_value.append(
        {"key": "DUPLICATE", "name": "Papers", "parent_collection": "PARENT1"},
    )
    with pytest.raises(ZoteroClientError, match="同路径同名"):
        await client.create_paper(title="Test paper", collection_key="CHILD1")
    assert [call.args[0] for call in client._connector_post.await_args_list] == ["/getSelectedCollection"]


@pytest.mark.asyncio
async def test_group_library_selection_is_rejected_before_writing():
    client = target_client()
    client._connector_post.return_value = connector_selection(library_id=2)
    with pytest.raises(ZoteroClientError, match="不会写入群组"):
        await client.create_paper(title="Test paper")
    assert client._connector_post.await_count == 1


@pytest.mark.asyncio
async def test_invalid_collection_is_rejected_before_connector_call():
    client = target_client()
    with pytest.raises(ValueError, match="不合法"):
        await client.create_paper(title="Test paper", collection_key="../private")
    client._connector_post.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("collection_key,target", [("CHILD1", "C8"), (None, "L1")])
async def test_save_moves_exact_session_and_verifies_new_item(collection_key, target):
    client = ZoteroLocalClient()
    client._save_target = AsyncMock(return_value=target)
    client._connector_post = AsyncMock()
    existing = saved_item("OLD123", [collection_key] if collection_key else [])
    new = saved_item(collections=[collection_key] if collection_key else [])
    client.search_items = AsyncMock(side_effect=[[existing], [existing, new]])

    result = await client.create_paper(title="Test paper", collection_key=collection_key)

    save, move = client._connector_post.await_args_list
    assert save.args[0] == "/saveItems"
    assert save.args[2] == 201
    assert move.args[0] == "/updateSession"
    assert move.args[1]["sessionID"] == save.args[1]["sessionID"]
    assert move.args[1]["target"] == target
    assert "collections" not in save.args[1]["items"][0]
    assert result["item_key"] == "NEW123"
    assert result["collection_verified"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("after", [[saved_item("OLD123", ["CHILD1"])], [saved_item(collections=["WRONG"])], []])
async def test_old_item_or_wrong_target_never_reports_success(after):
    client = ZoteroLocalClient()
    client._save_target = AsyncMock(return_value="C8")
    client._connector_post = AsyncMock()
    client.search_items = AsyncMock(side_effect=[[saved_item("OLD123", ["CHILD1"])], after])
    with pytest.raises(ZoteroWriteUnverifiedError, match="避免重复"):
        await client.create_paper(title="Test paper", collection_key="CHILD1")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [ZoteroClientError("HTTP 500"), httpx.RemoteProtocolError("Disconnected")])
async def test_failed_session_move_reports_possible_partial_write(failure):
    client = ZoteroLocalClient()
    client._save_target = AsyncMock(return_value="C8")
    client.search_items = AsyncMock(return_value=[])
    client._connector_post = AsyncMock(side_effect=[None, failure])
    with pytest.raises(ZoteroWriteUnverifiedError, match="可能已经写入"):
        await client.create_paper(title="Test paper", collection_key="CHILD1")


@pytest.mark.asyncio
async def test_pdf_request_preserves_metadata_save_and_reports_warning():
    client = ZoteroLocalClient()
    client._save_target = AsyncMock(return_value="L1")
    client._connector_post = AsyncMock()
    client.search_items = AsyncMock(side_effect=[[], [saved_item()]])
    result = await client.create_paper(title="Test paper", pdf_path="paper.pdf")
    assert result["item_key"] == "NEW123"
    assert result["pdf_imported"] is False
    assert "PDF 未导入" in result["warnings"][0]
    assert client._connector_post.await_count == 2
