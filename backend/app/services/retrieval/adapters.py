"""Adapters from current ScholarNova sources to the retrieval contract."""

from __future__ import annotations

import hashlib
from typing import Any

from app.models.knowledge import KnowledgeBase, KnowledgeChunk
from app.models.paper import PaperChunk, PaperEntity
from app.services.retrieval.contracts import RetrievalChunk


def from_knowledge(
    knowledge: KnowledgeBase,
    chunk: KnowledgeChunk,
) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk.id,
        document_id=f"knowledge:{knowledge.id}",
        source="knowledge",
        title=knowledge.source_paper_title or knowledge.title,
        content=chunk.content,
        position=chunk.position,
        feature_version=chunk.feature_version,
        content_hash=chunk.content_hash,
        metadata={
            "knowledge_id": knowledge.id,
            "category": knowledge.category,
            "doi": knowledge.source_paper_doi,
            "research_points": "；".join(knowledge.research_points or []),
            "tags": " ".join(knowledge.tags or []),
        },
    )


def _author_names(data: dict[str, Any]) -> str:
    names: list[str] = []
    for creator in data.get("creators") or []:
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
            names.append(name)
    return ", ".join(names[:8])


def from_zotero(item: dict[str, Any]) -> RetrievalChunk | None:
    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    item_id = str(item.get("key") or data.get("key") or "").strip()
    title = str(data.get("title") or "").strip()
    if not item_id or not title:
        return None
    content = str(data.get("abstractNote") or "").strip()
    fingerprint = hashlib.sha256(
        f"{item_id}\0{title}\0{content}".encode("utf-8")
    ).hexdigest()
    return RetrievalChunk(
        chunk_id=fingerprint,
        document_id=f"zotero:{item_id}",
        source="zotero",
        title=title,
        content=content,
        feature_version="zotero-local-v1",
        content_hash=fingerprint,
        metadata={
            "item_id": item_id,
            "authors": _author_names(data),
            "date": data.get("date") or "未知",
            "venue": data.get("publicationTitle") or data.get("conferenceName") or "未知",
            "doi": str(data.get("DOI") or "").strip() or None,
            "url": str(data.get("url") or "").strip() or None,
        },
    )


def from_paper(paper: PaperEntity, chunk: PaperChunk) -> RetrievalChunk:
    """Adapt a parsed PDF feature without losing section/page provenance."""
    return RetrievalChunk(
        chunk_id=chunk.id,
        document_id=f"paper:{paper.id}",
        source="paper",
        title=paper.title,
        content=chunk.content,
        position=chunk.position,
        feature_version=chunk.feature_version,
        content_hash=chunk.content_hash,
        metadata={
            "paper_id": paper.id,
            "kind": chunk.kind,
            "heading": chunk.heading,
            "page": chunk.page,
            "doi": paper.doi,
            "url": paper.url,
            "year": paper.year,
            "venue": paper.venue,
        },
    )
