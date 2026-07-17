import asyncio

import pytest

from app.schemas.query import DataSource, SubQuery
from app.services.search.retriever import Retriever


class DelayedSource:
    def __init__(self, name: str, delay: float):
        self.name = name
        self.delay = delay
        self.last_error = None

    async def search(self, query: str, max_results: int):
        await asyncio.sleep(self.delay)
        return []


@pytest.mark.asyncio
async def test_progress_callback_reports_actual_source_and_query():
    reported = []
    retriever = Retriever(
        sources={
            DataSource.CROSSREF: DelayedSource("crossref", 0.02),
            DataSource.OPENALEX: DelayedSource("openalex", 0.01),
        },
        timeout=1,
    )
    sub_queries = [
        SubQuery(query="first query", source=DataSource.CROSSREF, rationale="test"),
        SubQuery(query="second query", source=DataSource.OPENALEX, rationale="test"),
    ]

    result = await retriever.retrieve(
        sub_queries,
        progress_callback=lambda status: _record(reported, status),
    )

    assert len(result.source_statuses) == 2
    assert [status.source for status in reported] == ["openalex", "crossref"]
    assert {status.query for status in reported} == {"first query", "second query"}


async def _record(reported, status):
    reported.append(status)
