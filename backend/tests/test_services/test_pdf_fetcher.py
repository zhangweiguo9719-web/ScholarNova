from pathlib import Path

import pytest

from app.services.pdf.fetcher import FetchResult, PDFFetcher


def test_unpaywall_requires_a_real_contact_email(tmp_path):
    fetcher = PDFFetcher(cache_dir=tmp_path, unpaywall_email="not-an-email")
    assert fetcher._valid_email(fetcher.unpaywall_email) is False
    assert fetcher._valid_email("researcher@example.org") is True


@pytest.mark.asyncio
async def test_fetch_tries_doi_resolvers_until_one_succeeds(tmp_path, monkeypatch):
    fetcher = PDFFetcher(cache_dir=tmp_path)
    calls: list[str] = []

    async def failed(source):
        calls.append(source)
        return FetchResult(False, source=source, error="not found")

    async def openalex(_doi, _key):
        return await failed("openalex")

    async def unpaywall(_doi, _key):
        return await failed("unpaywall")

    async def semantic(_doi, _key):
        calls.append("semantic_scholar")
        pdf_path = tmp_path / "resolved.pdf"
        pdf_path.write_bytes(b"%PDF-test")
        return FetchResult(True, pdf_path=pdf_path, source="semantic_scholar")

    async def should_not_run(_doi, _key):
        raise AssertionError("resolver should stop after success")

    monkeypatch.setattr(fetcher, "_fetch_from_openalex", openalex)
    monkeypatch.setattr(fetcher, "_fetch_from_unpaywall", unpaywall)
    monkeypatch.setattr(fetcher, "_fetch_from_semantic_scholar", semantic)
    monkeypatch.setattr(fetcher, "_fetch_from_crossref", should_not_run)

    result = await fetcher.fetch(doi="10.1000/test")

    assert result.success is True
    assert result.pdf_path == Path(tmp_path / "resolved.pdf")
    assert calls == ["openalex", "unpaywall", "semantic_scholar"]
