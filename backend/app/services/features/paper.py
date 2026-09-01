"""Versioned text features extracted from authorized paper PDFs."""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import PaperChunk, PaperEntity
from app.services.features.knowledge import split_knowledge_text
from app.services.pdf.parser import ParsedDocument

PAPER_FEATURE_VERSION = "pdf-parser-chunker-v1"
_WHITESPACE = re.compile(r"[ \t\r\f\v]+")


def _clean(text: object) -> str:
    lines = [
        _WHITESPACE.sub(" ", line).strip()
        for line in str(text or "").splitlines()
    ]
    return "\n".join(line for line in lines if line).strip()


def _table_text(table: dict) -> str:
    caption = _clean(table.get("caption"))
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    row_text = "\n".join(
        " | ".join(_clean(cell) for cell in row)
        for row in rows[:40]
        if isinstance(row, (list, tuple))
    )
    return "\n".join(part for part in (caption, row_text) if part)


def build_paper_chunks(
    paper: PaperEntity,
    parsed: ParsedDocument,
) -> list[PaperChunk]:
    """Convert parsed sections, tables, and captions into stable feature rows."""
    entries: list[tuple[str, str | None, int | None, str]] = []
    abstract = _clean(parsed.abstract)
    if abstract:
        entries.append(("abstract", "Abstract", None, abstract))

    for section in parsed.sections or []:
        heading = _clean(section.heading) or "Section"
        for content in split_knowledge_text(_clean(section.text)):
            entries.append(("section", heading, None, content))

    for table in parsed.tables or []:
        content = _table_text(table)
        if content:
            page = table.get("page") if isinstance(table.get("page"), int) else None
            entries.append(("table", _clean(table.get("caption")) or "Table", page, content))

    for figure in parsed.figures or []:
        caption = _clean(figure.get("caption"))
        if caption:
            number = _clean(figure.get("figure_number"))
            heading = f"Figure {number}" if number else "Figure"
            page = figure.get("page") if isinstance(figure.get("page"), int) else None
            entries.append(("figure", heading, page, caption))

    if not entries:
        for content in split_knowledge_text(_clean(parsed.full_text)):
            entries.append(("fulltext", "Full text", None, content))

    chunks: list[PaperChunk] = []
    for position, (kind, heading, page, content) in enumerate(entries):
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        identity = (
            f"{PAPER_FEATURE_VERSION}\0{paper.id}\0{kind}\0{position}\0{content_hash}"
        )
        chunks.append(
            PaperChunk(
                id=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                paper_id=paper.id,
                position=position,
                kind=kind,
                heading=heading,
                page=page,
                content=content,
                content_hash=content_hash,
                feature_version=PAPER_FEATURE_VERSION,
                char_count=len(content),
            )
        )
    return chunks


async def rebuild_paper_features(
    db: AsyncSession,
    paper: PaperEntity,
    parsed: ParsedDocument,
) -> list[PaperChunk]:
    """Atomically replace searchable features for one paper in the session."""
    await db.execute(delete(PaperChunk).where(PaperChunk.paper_id == paper.id))
    chunks = build_paper_chunks(paper, parsed)
    db.add_all(chunks)
    await db.flush()
    return chunks


async def ensure_paper_features(
    db: AsyncSession,
    paper: PaperEntity,
    parsed: ParsedDocument,
) -> list[PaperChunk]:
    """Keep stored PDF features synchronized with deterministic parser output."""
    expected = build_paper_chunks(paper, parsed)
    current = list((await db.execute(
        select(PaperChunk)
        .where(PaperChunk.paper_id == paper.id)
        .order_by(PaperChunk.position)
    )).scalars().all())
    is_current = (
        len(current) == len(expected)
        and all(old.id == new.id for old, new in zip(current, expected))
    )
    if is_current:
        return current
    return await rebuild_paper_features(db, paper, parsed)
