"""Persistent cache records used by the retrieval pipeline."""

from __future__ import annotations

import hashlib
from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves this at runtime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RetrievalEmbedding(Base):
    """Provider/model-scoped embedding cached by normalized input hash."""

    __tablename__ = "retrieval_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "model",
            "input_hash",
            name="uq_retrieval_embedding_input",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    @classmethod
    def build_id(cls, provider: str, model: str, input_hash: str) -> str:
        payload = f"{provider}\0{model}\0{input_hash}".encode()
        return hashlib.sha256(payload).hexdigest()

    def as_vector(self) -> list[float]:
        return [float(value) for value in self.vector]

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "dimensions": self.dimensions,
            "input_hash": self.input_hash,
        }
