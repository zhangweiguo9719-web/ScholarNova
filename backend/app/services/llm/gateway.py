"""
LLM 网关

统一封装多家 LLM 提供商的调用接口，支持:
- OpenAI（含兼容 API）
- Anthropic
- Ollama（本地模型）
"""

import asyncio
import json
import logging
from numbers import Number
from typing import Any, List, Optional
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)


class EmptyLLMResponseError(RuntimeError):
    """The provider returned a successful response without usable text."""


class LLMGateway:
    """
    LLM 统一调用网关

    支持按任务类型自动选择模型（多模型配置）。
    """

    def __init__(self, provider: Optional[str] = None, task: Optional[str] = None):
        """
        初始化 LLM 网关

        Args:
            provider: LLM 提供商名称
            task: 任务类型（analysis/query_planning/translation/vision/recommendation）
        """
        if task:
            from app.config import get_model_for_task
            profile = get_model_for_task(task)
            self.provider = profile["provider"]
            self._api_key = profile["api_key"]
            self._base_url = profile["base_url"]
            self._model_name = profile["model"]
        else:
            self.provider = provider or settings.DEFAULT_LLM_PROVIDER
            self._api_key = None
            self._base_url = None
            self._model_name = None
        self._client = None
        self._usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        }
        self.last_usage = dict(self._usage)

        # SenseNova 默认配置
        if self.provider == "sensenova" and not self._api_key:
            self._api_key = settings.SENSENOVA_API_KEY
            self._base_url = settings.SENSENOVA_API_BASE
            self._model_name = self._model_name or settings.SENSENOVA_DEFAULT_MODEL

    def configure(self, api_key: str = None, base_url: str = None, model_name: str = None):
        """运行时覆盖配置"""
        config_changed = False
        if api_key:
            config_changed = config_changed or api_key != self._api_key
            self._api_key = api_key
        if base_url:
            normalized_base_url = base_url.rstrip("/")
            config_changed = config_changed or normalized_base_url != self._base_url
            self._base_url = normalized_base_url
        if model_name:
            config_changed = config_changed or model_name != self._model_name
            self._model_name = model_name
        if config_changed:
            # Never reuse a client created with stale credentials or endpoint data.
            self._client = None

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    @property
    def usage(self) -> dict[str, int]:
        """Return cumulative provider-reported token usage for this gateway."""
        return dict(self._usage)

    def reset_usage(self) -> None:
        """Reset cumulative usage before a separately measured operation."""
        for key in self._usage:
            self._usage[key] = 0
        self.last_usage = dict(self._usage)

    @staticmethod
    def _usage_value(usage: Any, *names: str) -> int:
        for name in names:
            value = (
                usage.get(name)
                if isinstance(usage, dict)
                else getattr(usage, name, None)
            )
            if isinstance(value, Number):
                return max(0, int(value))
        return 0

    def _record_usage(
        self,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ) -> None:
        prompt = max(0, int(prompt_tokens or 0))
        completion = max(0, int(completion_tokens or 0))
        total = max(0, int(total_tokens or 0)) or prompt + completion
        self.last_usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "requests": 1,
        }
        for key, value in self.last_usage.items():
            self._usage[key] += value

    async def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """
        发送对话请求并返回响应文本

        支持的 provider:
        - openai / mimo / deepseek / zhipu / qwen / moonshot / custom → OpenAI 兼容协议
        - anthropic → Anthropic Messages API
        - ollama → Ollama 本地接口
        """
        # 所有国产模型 + openai + custom 都走 OpenAI 兼容协议
        openai_compatible = {
            "openai", "mimo", "deepseek", "zhipu", "qwen", "moonshot", "sensenova", "custom",
        }
        if self.provider in openai_compatible:
            return await self._chat_openai(messages, model, temperature, max_tokens, **kwargs)
        elif self.provider == "anthropic":
            return await self._chat_anthropic(messages, model, temperature, max_tokens, **kwargs)
        elif self.provider == "ollama":
            return await self._chat_ollama(messages, model, temperature, max_tokens, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def generate_image(self, prompt: str, size: str = "2048x2048", n: int = 1, **kwargs) -> dict:
        """
        生成图片（SenseNova U1 Fast）

        Returns:
            {"status": "ok", "url": "..."} 或 {"status": "error", "error": "..."}
        """
        api_key = self._api_key or settings.SENSENOVA_API_KEY
        base_url = self._base_url or settings.SENSENOVA_API_BASE

        import httpx
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(
                    f"{base_url}/images/generations",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self._model_name or "sensenova-u1-fast",
                        "prompt": prompt,
                        "size": size,
                        "n": n,
                    },
                )
                data = r.json()
                if r.status_code == 200 and data.get("data"):
                    return {"status": "ok", "url": data["data"][0].get("url", "")}
                else:
                    return {"status": "error", "error": data.get("error", {}).get("message", str(data)[:200])}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    async def test_connection(self) -> dict:
        """
        测试 LLM 连接

        Returns:
            包含 success(bool)、model(str)、可选 error(str) 的字典
        """
        try:
            response = await self.chat(
                messages=[{"role": "user", "content": "Say hello in one word."}],
                # Reasoning models may spend the first tokens on hidden reasoning.
                # Keep this small, but leave enough room for visible content.
                max_tokens=64,
            )
            return {
                "success": True,
                "model": self._get_default_model(),
                "response": response[:50],
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    async def _chat_openai(
        self,
        messages: List[dict],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        """Call an OpenAI-compatible provider with connection recovery."""
        import openai

        model_name = model or self._model_name or settings.OPENAI_DEFAULT_MODEL
        base_url = (self._base_url or settings.OPENAI_API_BASE or "").rstrip("/") or None
        endpoint_host = urlparse(base_url).netloc if base_url else "default"
        max_retries = max(0, int(getattr(settings, "LLM_MAX_RETRIES", 3)))
        request_timeout = max(30.0, float(getattr(settings, "LLM_TIMEOUT", 60)))
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                # 每次重试重建客户端，避免状态异常
                self._client = None
                content = await asyncio.wait_for(
                    self._chat_openai_once(
                        messages,
                        model_name,
                        temperature,
                        max_tokens,
                        **kwargs,
                    ),
                    timeout=request_timeout,
                )
                if not content or not content.strip():
                    raise EmptyLLMResponseError("LLM provider returned an empty response")
                return content
            except Exception as exc:
                last_error = exc
                retryable = isinstance(
                    exc, (EmptyLLMResponseError, asyncio.TimeoutError)
                ) or self._is_retryable_openai_error(exc, openai)
                if not retryable or attempt >= max_retries:
                    break

                delay = min(8.0, float(2 ** attempt))
                logger.warning(
                    "Retrying LLM request after %s (provider=%s model=%s host=%s "
                    "attempt=%s/%s delay=%.1fs)",
                    type(exc).__name__,
                    self.provider,
                    model_name,
                    endpoint_host,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                await self._discard_openai_client()
                await asyncio.sleep(delay)

        await self._discard_openai_client()
        error_name = type(last_error).__name__ if last_error else "UnknownError"
        raise RuntimeError(
            f"LLM request failed after {max_retries + 1} attempts "
            f"(provider={self.provider}, model={model_name}, host={endpoint_host}, "
            f"error={error_name}): {last_error}"
        ) from last_error

    @staticmethod
    def _is_retryable_openai_error(exc: Exception, openai_module) -> bool:
        """Return whether an OpenAI-compatible failure is safe to retry."""
        retryable_types = tuple(
            error_type
            for error_type in (
                getattr(openai_module, "APIConnectionError", None),
                getattr(openai_module, "APITimeoutError", None),
                getattr(openai_module, "RateLimitError", None),
                getattr(openai_module, "InternalServerError", None),
            )
            if isinstance(error_type, type)
        )
        if isinstance(exc, retryable_types):
            return True

        api_status_error = getattr(openai_module, "APIStatusError", None)
        if isinstance(api_status_error, type) and isinstance(exc, api_status_error):
            return getattr(exc, "status_code", None) in {408, 409, 425, 429, 500, 502, 503, 504}
        return False

    async def _discard_openai_client(self) -> None:
        """Close and forget a potentially broken pooled connection."""
        client = self._client
        self._client = None
        close = getattr(client, "close", None)
        if close:
            try:
                await close()
            except Exception:
                logger.debug("Failed to close LLM client", exc_info=True)

    async def _chat_openai_once(
        self,
        messages: List[dict],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        """调用 OpenAI Chat Completion API（含所有 OpenAI 兼容提供商）"""
        import openai

        api_key = self._api_key or settings.OPENAI_API_KEY
        base_url = self._base_url or settings.OPENAI_API_BASE

        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                max_retries=0,
                timeout=120.0,  # MiMo API 可能较慢
            )

        response = await self._client.chat.completions.create(
            model=model or self._model_name or settings.OPENAI_DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        usage = getattr(response, "usage", None)
        self._record_usage(
            prompt_tokens=self._usage_value(usage, "prompt_tokens", "input_tokens"),
            completion_tokens=self._usage_value(
                usage, "completion_tokens", "output_tokens"
            ),
            total_tokens=self._usage_value(usage, "total_tokens"),
        )
        return response.choices[0].message.content

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

    async def _chat_anthropic(
        self,
        messages: List[dict],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        """调用 Anthropic Messages API"""
        import anthropic

        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
            )

        # Anthropic 的 system 消息是独立参数，需要从 messages 中提取
        system_text = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                user_messages.append(msg)

        call_kwargs = dict(
            model=model or settings.ANTHROPIC_DEFAULT_MODEL,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if system_text:
            call_kwargs["system"] = system_text
        call_kwargs.update(kwargs)

        response = await self._client.messages.create(**call_kwargs)
        usage = getattr(response, "usage", None)
        self._record_usage(
            prompt_tokens=self._usage_value(usage, "input_tokens", "prompt_tokens"),
            completion_tokens=self._usage_value(
                usage, "output_tokens", "completion_tokens"
            ),
        )
        return response.content[0].text

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------

    async def _chat_ollama(
        self,
        messages: List[dict],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        """调用 Ollama /api/chat 接口"""
        import httpx

        payload = {
            "model": model or settings.OLLAMA_DEFAULT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            self._record_usage(
                prompt_tokens=self._usage_value(data, "prompt_eval_count"),
                completion_tokens=self._usage_value(data, "eval_count"),
            )
            return data["message"]["content"]

    # ------------------------------------------------------------------
    # SenseNova 图像生成
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        image_size: str = "2k",
        negative_prompt: str = "",
        save_path: Optional[str] = None,
    ) -> dict:
        """
        调用 SenseNova-U1 图像生成 API

        Args:
            prompt: 图像描述
            aspect_ratio: 宽高比 (16:9, 1:1, 9:16 等)
            image_size: 图像尺寸 (1k, 2k)
            negative_prompt: 反向提示词
            save_path: 保存路径（可选）

        Returns:
            包含 status, output/url, message 的字典
        """
        import httpx
        import time

        api_key = self._api_key or settings.SENSENOVA_API_KEY
        base_url = (self._base_url or settings.SENSENOVA_API_BASE).rstrip("/")
        model = self._model_name or settings.SENSENOVA_DEFAULT_MODEL

        # 将 aspect_ratio 转为像素尺寸
        size = self._resolve_image_size(image_size.upper(), aspect_ratio)

        url = f"{base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "response_format": "url",
            "output_format": "png",
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            return {"status": "failed", "error": f"HTTP {e.response.status_code}: {e.response.text[:300]}"}
        except httpx.HTTPError as e:
            return {"status": "failed", "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"status": "failed", "error": f"Request error: {str(e)}"}

        images_urls = [item.get("url") for item in data.get("data", []) if item.get("url")]
        if not images_urls:
            return {"status": "failed", "error": f"No image in response: {json.dumps(data, ensure_ascii=False)[:300]}"}

        image_url = images_urls[-1]

        # 可选：下载到本地
        if save_path:
            import os
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            async with httpx.AsyncClient(timeout=120.0) as client:
                img_resp = await client.get(image_url)
                img_resp.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
            return {"status": "ok", "output": save_path, "url": image_url, "message": "Image generated successfully"}

        return {"status": "ok", "url": image_url, "message": "Image generated successfully"}

    @staticmethod
    def _resolve_image_size(resolution: str, aspect_ratio: str) -> str:
        """将分辨率+宽高比转为像素尺寸字符串（SenseNova-U1 有效尺寸）"""
        # SenseNova-U1 API 支持的完整尺寸列表
        buckets = {
            "2:3": (1664, 2496), "3:2": (2496, 1664), "3:4": (1760, 2368),
            "4:3": (2368, 1760), "4:5": (1824, 2272), "5:4": (2272, 1824),
            "1:1": (2048, 2048), "16:9": (2752, 1536), "9:16": (1536, 2752),
            "21:9": (3072, 1376), "9:21": (1344, 3136),
            "32:9": (2560, 720), "32:27": (3072, 864),
        }
        if aspect_ratio in buckets:
            w, h = buckets[aspect_ratio]
        else:
            # 默认 16:9
            w, h = buckets["16:9"]
        return f"{w}x{h}"

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _get_default_model(self) -> str:
        """获取当前 provider 的默认模型名"""
        if self.provider == "openai":
            return settings.OPENAI_DEFAULT_MODEL
        elif self.provider == "anthropic":
            return settings.ANTHROPIC_DEFAULT_MODEL
        elif self.provider == "ollama":
            return settings.OLLAMA_DEFAULT_MODEL
        return "unknown"
