"""Tests for local Zotero metadata retrieval."""

import pytest

from app.models.paper import PaperEntity
from app.services.sources.local_library import LocalLibrarySource


class ExistingSession:
    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        return False


@pytest.mark.asyncio
async def test_local_library_search_only_returns_matching_zotero_items(db_session) -> None:
    zotero_paper = PaperEntity(
        external_id="openalex:LOCAL001",
        title="Retrieval-Augmented Generation for Scientific Literature",
        abstract="A grounded assistant for research evidence.",
        authors=[{"name": "Researcher One"}],
        year=2025,
        venue="AI Research",
        doi="10.1000/local.1",
        canonical_doi="10.1000/local.1",
        source="openalex",
        keywords=["RAG", "evidence"],
        citation_count=0,
        is_open_access=False,
        extra_metadata={"zotero": {"key": "LOCAL001", "library": "local"}},
    )
    remote_paper = PaperEntity(
        external_id="openalex:REMOTE001",
        title="Retrieval-Augmented Generation for Scientific Literature",
        authors=[],
        source="openalex",
        citation_count=10,
        is_open_access=True,
    )
    db_session.add_all([zotero_paper, remote_paper])
    await db_session.flush()

    source = LocalLibrarySource(lambda: ExistingSession(db_session))
    papers = await source.search("scientific literature RAG", max_results=10)

    assert len(papers) == 1
    assert papers[0].id == zotero_paper.id
    assert papers[0].source == "zotero"
    assert papers[0].relevance_score and papers[0].relevance_score > 0
