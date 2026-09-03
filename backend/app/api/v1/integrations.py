"""User-controlled integrations with external research applications."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.database import get_db
from app.models.paper import PaperEntity
from app.services.integrations.zotero import (
    ZoteroAccessDeniedError,
    ZoteroClientError,
    ZoteroLocalClient,
    ZoteroUnavailableError,
)

router = APIRouter()


class ZoteroImportRequest(BaseModel):
    collection_key: str | None = Field(default=None, max_length=32)
    limit: int = Field(default=50, ge=1, le=100)


class ZoteroPushRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    creators: list[dict[str, str]] = Field(default_factory=list)
    year: str | None = Field(default=None, max_length=16)
    venue: str | None = Field(default=None, max_length=255)
    doi: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=1000)
    abstract: str | None = Field(default=None, max_length=5000)
    collection_key: str | None = Field(default=None, max_length=32)
    pdf_path: str | None = Field(default=None, max_length=1024)
    api_key: str | None = Field(default=None, max_length=128)


def _normalise_doi(value: Any) -> str | None:
    doi = str(value or "").strip().casefold()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi or None


def _year(value: Any) -> int | None:
    match = re.search(r"\b(18|19|20|21)\d{2}\b", str(value or ""))
    return int(match.group(0)) if match else None


def _authors(creators: Any) -> list[dict[str, str]]:
    if not isinstance(creators, list):
        return []
    result: list[dict[str, str]] = []
    for creator in creators:
        if not isinstance(creator, dict):
            continue
        name = str(creator.get("name") or "").strip()
        if not name:
            name = " ".join(
                part
                for part in (
                    str(creator.get("firstName") or "").strip(),
                    str(creator.get("lastName") or "").strip(),
                )
                if part
            )
        if name:
            result.append({"name": name})
    return result


def _tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        str(tag.get("tag")).strip()
        for tag in value
        if isinstance(tag, dict) and str(tag.get("tag") or "").strip()
    ]


def _zotero_metadata(item: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return {
        "zotero": {
            "key": item.get("key") or data.get("key"),
            "version": item.get("version") or data.get("version"),
            "item_type": data.get("itemType"),
            "collections": data.get("collections") or [],
            "date_modified": data.get("dateModified"),
            "library": "local",
        }
    }


def _venue(data: dict[str, Any]) -> str | None:
    for field in (
        "publicationTitle",
        "conferenceName",
        "proceedingsTitle",
        "bookTitle",
        "journalAbbreviation",
    ):
        value = str(data.get(field) or "").strip()
        if value:
            return value
    return None


def _raise_zotero_error(exc: Exception) -> None:
    if isinstance(exc, ZoteroAccessDeniedError):
        raise HTTPException(
            status_code=503,
            detail={"code": "zotero_api_disabled", "message": str(exc)},
        ) from exc
    if isinstance(exc, ZoteroUnavailableError):
        raise HTTPException(
            status_code=503,
            detail={"code": "zotero_unavailable", "message": str(exc)},
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, ZoteroClientError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    raise exc


@router.get("/zotero/status")
async def zotero_status() -> dict[str, Any]:
    """Check the fixed localhost endpoint without accepting arbitrary URLs."""
    try:
        status = await ZoteroLocalClient().status()
        return {
            "connected": status.connected,
            "server_id": status.server_id,
            "zotero_version": status.zotero_version,
            "mode": "local_read_write",
        }
    except Exception as exc:
        _raise_zotero_error(exc)
        raise


@router.get("/zotero/collections")
async def zotero_collections() -> dict[str, Any]:
    try:
        items = await ZoteroLocalClient().collections()
        return {"items": items, "total": len(items)}
    except Exception as exc:
        _raise_zotero_error(exc)
        raise


@router.post("/zotero/push")
async def push_to_zotero(request: ZoteroPushRequest) -> dict[str, Any]:
    """Push the current paper (and its local PDF) into the user's Zotero library.

    Requires Zotero running with local API enabled; writes may require an
    API key (Settings → Advanced → create one for ScholarNova).
    """
    from app.services.integrations.zotero import ZoteroLocalClient

    creators = []
    for creator in request.creators:
        if not isinstance(creator, dict):
            continue
        creators.append(
            {
                "firstName": str(creator.get("firstName") or "").strip(),
                "lastName": str(creator.get("lastName") or "").strip(),
            }
        )
    try:
        result = await ZoteroLocalClient().create_paper(
            title=request.title,
            creators=creators,
            year=request.year,
            venue=request.venue,
            doi=request.doi,
            url=request.url,
            abstract=request.abstract,
            collection_key=request.collection_key,
            pdf_path=request.pdf_path,
            api_key=request.api_key or None,
        )
    except Exception as exc:
        _raise_zotero_error(exc)
        raise
    if not result.get("item_key"):
        raise HTTPException(
            status_code=502,
            detail={"code": "zotero_write_failed", "message": "Zotero 未返回创建成功的条目"},
        )
    return {"success": True, **result}


@router.post("/zotero/import")
async def import_from_zotero(
    request: ZoteroImportRequest,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    """Import bibliographic metadata into ScholarNova; Zotero remains untouched."""
    try:
        items = await ZoteroLocalClient().items(
            collection_key=request.collection_key,
            limit=request.limit,
        )
    except Exception as exc:
        _raise_zotero_error(exc)
        raise

    created = 0
    updated = 0
    skipped = 0
    paper_ids: list[str] = []

    for item in items:
        data = item["data"]
        title = str(data.get("title") or "").strip()
        zotero_key = str(item.get("key") or data.get("key") or "").strip()
        if not title or not zotero_key:
            skipped += 1
            continue

        external_id = f"zotero:{zotero_key}"
        doi = _normalise_doi(data.get("DOI"))
        conditions = [PaperEntity.external_id == external_id]
        if doi:
            conditions.extend(
                [
                    func.lower(PaperEntity.doi) == doi,
                    func.lower(PaperEntity.canonical_doi) == doi,
                ]
            )
        existing = (
            await db.execute(select(PaperEntity).where(or_(*conditions)).limit(1))
        ).scalar_one_or_none()
        metadata = _zotero_metadata(item, data)
        tags = _tags(data.get("tags"))

        if existing:
            current_metadata = dict(existing.extra_metadata or {})
            current_metadata.update(metadata)
            existing.extra_metadata = current_metadata
            existing.abstract = existing.abstract or str(data.get("abstractNote") or "").strip() or None
            existing.authors = existing.authors or _authors(data.get("creators"))
            existing.year = existing.year or _year(data.get("date"))
            existing.venue = existing.venue or _venue(data)
            existing.url = existing.url or str(data.get("url") or "").strip() or None
            existing.volume = existing.volume or str(data.get("volume") or "").strip() or None
            existing.issue = existing.issue or str(data.get("issue") or "").strip() or None
            existing.pages = existing.pages or str(data.get("pages") or "").strip() or None
            existing.keywords = existing.keywords or tags
            updated += 1
            paper_ids.append(str(existing.id))
            continue

        paper = PaperEntity(
            external_id=external_id,
            canonical_doi=doi,
            title=title,
            abstract=str(data.get("abstractNote") or "").strip() or None,
            authors=_authors(data.get("creators")),
            year=_year(data.get("date")),
            venue=_venue(data),
            doi=doi,
            url=str(data.get("url") or "").strip() or None,
            source="zotero",
            citation_count=0,
            is_open_access=False,
            keywords=tags,
            volume=str(data.get("volume") or "").strip() or None,
            issue=str(data.get("issue") or "").strip() or None,
            pages=str(data.get("pages") or "").strip() or None,
            extra_metadata=metadata,
        )
        db.add(paper)
        await db.flush()
        created += 1
        paper_ids.append(str(paper.id))

    return {
        "success": True,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total": len(items),
        "paper_ids": paper_ids,
        "read_only": True,
    }
