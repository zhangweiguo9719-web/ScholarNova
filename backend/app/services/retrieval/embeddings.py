"""Small, provider-neutral embeddings gateway for optional semantic retrieval."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from numbers import Number
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    input_tokens: int = 0


class EmbeddingGateway:
    """Call only a user-configured embeddings endpoint.

    Chat profiles are deliberately not consulted here. Supported protocols are
    OpenAI-compatible ``/embeddings`` and Ollama's local ``/api/embed``.
    """

    OPENAI_COMPATIBLE = {
        "openai",
        "zhipu",
        "qwen",
        "siliconflow",
        "custom",
    }

    def __init__(self, config: dict[str, Any]):
        self.provider = str(config.get("provider") or "").casefold()
        self.model = str(config.get("model") or "").strip()
        self.api_key = config.get("api_key")
        self.base_url = str(config.get("base_url") or "").rstrip("/")
        if not self.model:
            raise ValueError("Embedding 模型名称不能为空")

    async def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        cleaned = [str(text or "").strip()[:12000] for text in texts]
        if not cleaned or any(not text for text in cleaned):
            raise ValueError("Embedding 输入不能为空")
        if self.provider == "ollama":
            result = await self._embed_ollama(cleaned)
        elif self.provider in self.OPENAI_COMPATIBLE:
            result = await self._embed_openai(cleaned)
        else:
            raise ValueError(f"Embedding 暂不支持提供商：{self.provider or 'unknown'}")
        self._validate(result.vectors, len(cleaned))
        return result

    async def _embed_openai(self, texts: list[str]) -> EmbeddingBatch:
        import openai

        if not self.base_url:
            raise ValueError("Embedding API 地址不能为空")
        if self.provider != "custom" and not self.api_key:
            raise ValueError("Embedding API Key 尚未配置")
        client = openai.AsyncOpenAI(
            api_key=self.api_key or "local-not-required",
            base_url=self.base_url,
            max_retries=0,
            timeout=45.0,
        )
        try:
            response = await asyncio.wait_for(
                client.embeddings.create(model=self.model, input=texts),
                timeout=45.0,
            )
        finally:
            await client.close()
        ordered = sorted(response.data, key=lambda item: item.index)
        usage = getattr(response, "usage", None)
        tokens = (
            usage.get("prompt_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "prompt_tokens", 0)
        )
        return EmbeddingBatch(
            vectors=[[float(value) for value in item.embedding] for item in ordered],
            input_tokens=int(tokens) if isinstance(tokens, Number) else 0,
        )

    async def _embed_ollama(self, texts: list[str]) -> EmbeddingBatch:
        import httpx

        base_url = self.base_url or "http://localhost:11434"
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{base_url}/api/embed",
                json={"model": self.model, "input": texts, "truncate": True},
            )
            response.raise_for_status()
            data = response.json()
        tokens = data.get("prompt_eval_count", 0)
        return EmbeddingBatch(
            vectors=[[float(value) for value in vector] for vector in data.get("embeddings") or []],
            input_tokens=int(tokens) if isinstance(tokens, Number) else 0,
        )

    @staticmethod
    def _validate(vectors: list[list[float]], expected: int) -> None:
        if len(vectors) != expected:
            raise ValueError("Embedding 返回数量与输入数量不一致")
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1 or not dimensions or 0 in dimensions:
            raise ValueError("Embedding 返回了无效向量维度")
        if any(not math.isfinite(value) for vector in vectors for value in vector):
            raise ValueError("Embedding 返回了非有限数值")
