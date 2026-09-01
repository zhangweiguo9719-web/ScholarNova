"""Provider-neutral records passed between feature and inference pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RetrievalChunk:
    """A traceable text unit that can compete in one retrieval ranking."""

    chunk_id: str
    document_id: str
    source: str
    title: str
    content: str
    position: int = 0
    feature_version: str = "unknown"
    content_hash: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def search_text(self) -> str:
        metadata_text = " ".join(
            str(value)
            for value in self.metadata.values()
            if value not in (None, "", [], {})
        )
        return " ".join((self.title, self.title, metadata_text, self.content)).strip()
