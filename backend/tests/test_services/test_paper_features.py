"""Tests for deterministic PDF feature extraction."""

from app.models.paper import PaperEntity
from app.services.features.paper import build_paper_chunks
from app.services.pdf.parser import DocumentSection, ParsedDocument


def test_paper_features_cover_sections_tables_and_figures() -> None:
    paper = PaperEntity(id="paper-1", title="Traceable RAG", source="test")
    parsed = ParsedDocument(
        title="Traceable RAG",
        abstract="A grounded retrieval system.",
        sections=[
            DocumentSection(
                heading="Methods",
                level=1,
                text="The system combines sparse retrieval with evidence checks.",
                paragraph_index=1,
            )
        ],
        tables=[{
            "page": 4,
            "caption": "Table 1. Retrieval results",
            "rows": [["Method", "F1"], ["BM25", "0.42"]],
        }],
        figures=[{
            "figure_number": "2",
            "caption": "Figure 2. Evidence pipeline architecture.",
        }],
        full_text="Fallback text",
    )

    first = build_paper_chunks(paper, parsed)
    second = build_paper_chunks(paper, parsed)

    assert {chunk.kind for chunk in first} == {
        "abstract", "section", "table", "figure",
    }
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    table = next(chunk for chunk in first if chunk.kind == "table")
    assert table.page == 4
    assert "BM25 | 0.42" in table.content


def test_paper_features_fall_back_to_full_text() -> None:
    paper = PaperEntity(id="paper-2", title="Fallback", source="test")
    parsed = ParsedDocument(
        title="Fallback",
        abstract="",
        full_text="完整正文内容。" * 200,
    )

    chunks = build_paper_chunks(paper, parsed)

    assert chunks
    assert all(chunk.kind == "fulltext" for chunk in chunks)
