"""Read-only client for Zotero's local Web API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

ZOTERO_LOCAL_API = "http://127.0.0.1:23119/api"
ZOTERO_API_VERSION = "3"
_COLLECTION_KEY = re.compile(r"^[A-Za-z0-9]+$")


class ZoteroUnavailableError(RuntimeError):
    """Raised when Zotero is not running or its local API is disabled."""


class ZoteroAccessDeniedError(RuntimeError):
    """Raised when Zotero is running but its local API is disabled."""


class ZoteroClientError(RuntimeError):
    """Raised when Zotero returns an invalid or unsuccessful response."""


@dataclass(slots=True)
class ZoteroStatus:
    connected: bool
    server_id: str | None = None
    zotero_version: str | None = None


class ZoteroLocalClient:
    """A deliberately small, read-only wrapper around the fixed localhost API."""

    def __init__(self, timeout: float = 4.0) -> None:
        self.timeout = timeout

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                base_url=ZOTERO_LOCAL_API,
                timeout=self.timeout,
                trust_env=False,
                headers={"Zotero-API-Version": ZOTERO_API_VERSION},
            ) as client:
                response = await client.get(path, params=params)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise ZoteroUnavailableError(
                "未检测到 Zotero。请先启动 Zotero，并在设置 → 高级中启用本地 API。"
            ) from exc

        if response.status_code in {401, 403}:
            raise ZoteroAccessDeniedError(
                "Zotero 已运行，但拒绝了本地 API 访问。请检查 Zotero 的本地 API 设置。"
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ZoteroClientError(
                f"Zotero 本地 API 返回 HTTP {response.status_code}"
            ) from exc
        return response

    async def _post(
        self,
        path: str,
        payload: list[dict[str, Any]],
        *,
        api_key: str | None = None,
    ) -> httpx.Response:
        headers = {"Zotero-API-Version": ZOTERO_API_VERSION}
        if api_key:
            headers["Zotero-API-Key"] = api_key
        try:
            async with httpx.AsyncClient(
                base_url=ZOTERO_LOCAL_API,
                timeout=10.0,
                trust_env=False,
                headers=headers,
            ) as client:
                response = await client.post(path, json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise ZoteroUnavailableError(
                "未检测到 Zotero。请先启动 Zotero，并在设置 → 高级中启用本地 API。"
            ) from exc
        if response.status_code in {401, 403}:
            raise ZoteroAccessDeniedError(
                "Zotero 拒绝了写入请求。请在 Zotero 设置 → 高级 → 允许其他应用程序"
                "与 Zotero 通信（并开启写入），或提供本地 API 密钥。"
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ZoteroClientError(
                f"Zotero 本地 API 返回 HTTP {response.status_code}: "
                f"{response.text[:160]}"
            ) from exc
        return response

    async def status(self) -> ZoteroStatus:
        response = await self._get(
            "/users/0/items/top",
            params={"limit": 1, "format": "json"},
        )
        try:
            response.json()
        except ValueError as exc:
            raise ZoteroClientError("Zotero 本地 API 返回了无效数据") from exc
        return ZoteroStatus(
            connected=True,
            server_id=response.headers.get("Zotero-Server-ID"),
            zotero_version=(
                response.headers.get("Zotero-Version")
                or response.headers.get("X-Zotero-Version")
            ),
        )

    async def collections(self) -> list[dict[str, Any]]:
        response = await self._get(
            "/users/0/collections",
            params={
                "limit": 100,
                "sort": "title",
                "direction": "asc",
                "format": "json",
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ZoteroClientError("Zotero 文献库返回了无效数据") from exc
        if not isinstance(payload, list):
            raise ZoteroClientError("Zotero 文献库数据格式不正确")

        collections: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            key = str(item.get("key") or data.get("key") or "").strip()
            name = str(data.get("name") or "").strip()
            if key and name:
                collections.append(
                    {
                        "key": key,
                        "name": name,
                        "parent_collection": data.get("parentCollection") or None,
                        "version": item.get("version") or data.get("version"),
                    }
                )
        return collections

    async def items(
        self,
        *,
        collection_key: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if collection_key and not _COLLECTION_KEY.fullmatch(collection_key):
            raise ValueError("Zotero 文件夹标识不合法")
        safe_limit = min(max(limit, 1), 100)
        path = "/users/0/items/top"
        if collection_key:
            path = f"/users/0/collections/{collection_key}/items/top"

        response = await self._get(
            path,
            params={
                "limit": safe_limit,
                "sort": "dateModified",
                "direction": "desc",
                "format": "json",
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ZoteroClientError("Zotero 文献数据无法解析") from exc
        if not isinstance(payload, list):
            raise ZoteroClientError("Zotero 文献数据格式不正确")

        excluded = {"attachment", "note", "annotation"}
        return [
            item
            for item in payload
            if isinstance(item, dict)
            and isinstance(item.get("data"), dict)
            and item["data"].get("itemType") not in excluded
        ]

    async def search_items(
        self,
        query: str,
        *,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        """Search top-level bibliographic items in the live local library."""
        clean_query = query.strip()
        if not clean_query:
            return []
        response = await self._get(
            "/users/0/items/top",
            params={
                "q": clean_query[:300],
                "qmode": "everything",
                "limit": min(max(limit, 1), 20),
                "sort": "dateModified",
                "direction": "desc",
                "format": "json",
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ZoteroClientError("Zotero 搜索结果无法解析") from exc
        if not isinstance(payload, list):
            raise ZoteroClientError("Zotero 搜索结果格式不正确")
        excluded = {"attachment", "note", "annotation"}
        return [
            item
            for item in payload
            if isinstance(item, dict)
            and isinstance(item.get("data"), dict)
            and item["data"].get("itemType") not in excluded
        ]


    async def create_paper(
        self,
        *,
        title: str,
        creators: list[dict[str, Any]] | None = None,
        year: str | None = None,
        venue: str | None = None,
        doi: str | None = None,
        url: str | None = None,
        abstract: str | None = None,
        collection_key: str | None = None,
        pdf_path: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a journalArticle item (and optionally link a local PDF) in Zotero.

        Returns the created Zotero item key and attachment key.
        """
        clean_title = (title or "").strip()
        if not clean_title:
            raise ValueError("标题不能为空")

        item: dict[str, Any] = {
            "itemType": "journalArticle",
            "title": clean_title[:500],
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": (c.get("firstName") or "").strip()[:100],
                    "lastName": (c.get("lastName") or "").strip()[:100],
                }
                for c in (creators or [])
                if (c.get("firstName") or "").strip() or (c.get("lastName") or "").strip()
            ],
            "tags": [],
        }
        if year:
            item["date"] = str(year).strip()[:16]
        if venue:
            item["publicationTitle"] = venue.strip()[:255]
        if doi:
            item["DOI"] = doi.strip()[:255]
        if url:
            item["url"] = url.strip()[:1000]
        if abstract:
            item["abstractNote"] = abstract.strip()[:5000]
        if collection_key and _COLLECTION_KEY.fullmatch(collection_key):
            item["collections"] = [collection_key]

        response = await self._post("/users/0/items", [item], api_key=api_key)
        created = response.json()
        parent_key = ""
        if isinstance(created, list) and created and isinstance(created[0], dict):
            parent_key = str(created[0].get("successful", {}).get("0", {}).get("key", "") or "")

        attachment_key = ""
        if parent_key and pdf_path:
            attachment = [
                {
                    "itemType": "attachment",
                    "parentItem": parent_key,
                    "linkMode": "linked_file",
                    "path": str(pdf_path),
                    "title": f"{clean_title[:200]}.pdf",
                    "contentType": "application/pdf",
                }
            ]
            try:
                att_response = await self._post(
                    "/users/0/items", attachment, api_key=api_key
                )
                att_created = att_response.json()
                if isinstance(att_created, list) and att_created and isinstance(
                    att_created[0], dict
                ):
                    attachment_key = str(
                        att_created[0].get("successful", {}).get("0", {}).get("key", "") or ""
                    )
            except ZoteroClientError:
                # 附件失败不回滚条目，返回时说明
                pass

        return {
            "item_key": parent_key,
            "attachment_key": attachment_key,
            "collection_key": collection_key,
        }
