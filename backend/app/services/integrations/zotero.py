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
