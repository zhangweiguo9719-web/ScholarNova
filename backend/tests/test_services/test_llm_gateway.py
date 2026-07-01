"""
LLM 网关测试
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm.gateway import LLMGateway


class TestLLMGateway:
    """LLMGateway 测试套件"""

    def test_default_provider(self):
        """默认 provider 应从 settings 获取"""
        gateway = LLMGateway()
        assert gateway.provider is not None

    def test_custom_provider(self):
        """应支持自定义 provider"""
        gateway = LLMGateway(provider="ollama")
        assert gateway.provider == "ollama"

    def test_client_initially_none(self):
        """初始化时 _client 应为 None"""
        gateway = LLMGateway(provider="openai")
        assert gateway._client is None

    async def test_chat_unsupported_provider(self):
        """不支持的 provider 应抛出 ValueError"""
        gateway = LLMGateway(provider="unsupported")
        with pytest.raises(ValueError, match="Unsupported provider"):
            await gateway.chat(messages=[{"role": "user", "content": "hello"}])

    async def test_chat_openai_success(self):
        """OpenAI 调用成功应返回响应文本"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.usage = MagicMock(
            prompt_tokens=12,
            completion_tokens=4,
            total_tokens=16,
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        gateway = LLMGateway(provider="openai")

        with patch("app.services.llm.gateway.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_API_BASE = "https://api.openai.com/v1"
            mock_settings.OPENAI_DEFAULT_MODEL = "gpt-4o"

            with patch("openai.AsyncOpenAI", return_value=mock_client):
                result = await gateway.chat(
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_tokens=10,
                )

        assert result == "Hello, world!"
        assert gateway.last_usage == {
            "prompt_tokens": 12,
            "completion_tokens": 4,
            "total_tokens": 16,
            "requests": 1,
        }
        assert gateway.usage["total_tokens"] == 16

    async def test_usage_accumulates_and_resets(self):
        """连续模型调用应累计真实 usage，并支持按评测样本清零。"""
        gateway = LLMGateway(provider="openai")
        gateway._record_usage(prompt_tokens=10, completion_tokens=2)
        gateway._record_usage(prompt_tokens=20, completion_tokens=3)

        assert gateway.usage == {
            "prompt_tokens": 30,
            "completion_tokens": 5,
            "total_tokens": 35,
            "requests": 2,
        }

        gateway.reset_usage()
        assert gateway.usage == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        }

    async def test_chat_openai_rebuilds_client_after_connection_error(self):
        """A transient connection error should rebuild the client and retry."""
        import httpx
        import openai

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Recovered"

        failed_client = AsyncMock()
        failed_client.chat.completions.create = AsyncMock(
            side_effect=openai.APIConnectionError(
                request=httpx.Request("POST", "https://example.com/v1/chat/completions")
            )
        )
        healthy_client = AsyncMock()
        healthy_client.chat.completions.create = AsyncMock(return_value=mock_response)

        gateway = LLMGateway(provider="openai")

        with patch("app.services.llm.gateway.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_API_BASE = "https://example.com/v1"
            mock_settings.OPENAI_DEFAULT_MODEL = "test-model"
            mock_settings.LLM_MAX_RETRIES = 1

            with patch("openai.AsyncOpenAI", side_effect=[failed_client, healthy_client]):
                with patch("app.services.llm.gateway.asyncio.sleep", new=AsyncMock()):
                    result = await gateway.chat(
                        messages=[{"role": "user", "content": "Say hello"}],
                        max_tokens=10,
                    )

        assert result == "Recovered"
        failed_client.close.assert_awaited_once()
        assert failed_client.chat.completions.create.await_count == 1
        assert healthy_client.chat.completions.create.await_count == 1

    async def test_chat_ollama_success(self):
        """Ollama 调用成功应返回响应文本"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Hello from Ollama"},
            "prompt_eval_count": 8,
            "eval_count": 3,
        }
        mock_response.raise_for_status = MagicMock()

        gateway = LLMGateway(provider="ollama")

        with patch("app.services.llm.gateway.settings") as mock_settings:
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_DEFAULT_MODEL = "qwen2.5:14b"

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_http_client = AsyncMock()
                mock_http_client.post = AsyncMock(return_value=mock_response)
                mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
                mock_http_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_http_client

                result = await gateway.chat(
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_tokens=10,
                )

        assert result == "Hello from Ollama"
        assert gateway.usage["total_tokens"] == 11

    async def test_test_connection_success(self):
        """test_connection 成功应返回 success=True"""
        gateway = LLMGateway(provider="openai")
        gateway.chat = AsyncMock(return_value="hello")

        result = await gateway.test_connection()
        assert result["success"] is True
        assert "model" in result

    async def test_test_connection_failure(self):
        """test_connection 失败应返回 success=False"""
        gateway = LLMGateway(provider="openai")
        gateway.chat = AsyncMock(side_effect=Exception("Connection failed"))

        result = await gateway.test_connection()
        assert result["success"] is False
        assert "error" in result
        assert "Connection failed" in result["error"]

    async def test_chat_anthropic_success(self):
        """Anthropic 调用成功应返回响应文本"""
        mock_content = MagicMock()
        mock_content.text = "Hello from Claude"

        mock_response = MagicMock()
        mock_response.content = [mock_content]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        gateway = LLMGateway(provider="anthropic")

        with patch("app.services.llm.gateway.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mock_settings.ANTHROPIC_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                result = await gateway.chat(
                    messages=[
                        {"role": "system", "content": "You are helpful"},
                        {"role": "user", "content": "Say hello"},
                    ],
                    max_tokens=10,
                )

        assert result == "Hello from Claude"

    async def test_chat_anthropic_extracts_system_message(self):
        """Anthropic 调用应提取消息中的 system 消息"""
        mock_content = MagicMock()
        mock_content.text = "OK"
        mock_response = MagicMock()
        mock_response.content = [mock_content]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        gateway = LLMGateway(provider="anthropic")

        with patch("app.services.llm.gateway.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mock_settings.ANTHROPIC_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                await gateway.chat(
                    messages=[
                        {"role": "system", "content": "Be concise"},
                        {"role": "user", "content": "Hello"},
                    ],
                )

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["system"] == "Be concise"
