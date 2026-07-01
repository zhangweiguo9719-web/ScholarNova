"""
应用配置管理

使用 pydantic-settings 管理配置，支持从环境变量和 .env 文件加载
"""

from typing import Any, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # =============================================================================
    # 应用配置
    # =============================================================================
    APP_NAME: str = "ScholarNova"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-secret-key"

    # =============================================================================
    # 数据库配置
    # =============================================================================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "scholar"
    POSTGRES_PASSWORD: str = "scholar_password"
    POSTGRES_DB: str = "scholar_agent"
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        """组装数据库连接字符串"""
        if isinstance(v, str) and v:
            return v
        data = info.data
        return (
            f"postgresql+asyncpg://{data.get('POSTGRES_USER', 'scholar')}"
            f":{data.get('POSTGRES_PASSWORD', 'scholar_password')}"
            f"@{data.get('POSTGRES_HOST', 'localhost')}"
            f":{data.get('POSTGRES_PORT', 5432)}"
            f"/{data.get('POSTGRES_DB', 'scholar_agent')}"
        )

    # =============================================================================
    # Redis 配置
    # =============================================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], info) -> Optional[str]:
        """组装 Redis 连接字符串"""
        if v is not None and isinstance(v, str) and v.strip():
            return v
        # 不自动生成 Redis URL，让 cache.py 自行处理
        return None

    # =============================================================================
    # LLM 模型配置
    # =============================================================================
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "qwen2.5:14b"

    # SenseNova
    SENSENOVA_API_KEY: str = ""
    SENSENOVA_API_BASE: str = "https://token.sensenova.cn/v1"
    SENSENOVA_DEFAULT_MODEL: str = "sensenova-u1-fast"

    # 默认 LLM 提供商
    DEFAULT_LLM_PROVIDER: str = "openai"

    # =============================================================================
    # 学术数据源 API Keys
    # =============================================================================
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    OPENALEX_EMAIL: Optional[str] = None
    CROSSREF_EMAIL: Optional[str] = None
    HF_ACCESS_TOKEN: Optional[str] = None
    HF_TOKEN: Optional[str] = None

    # =============================================================================
    # CORS 配置
    # =============================================================================
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # =============================================================================
    # 日志配置
    # =============================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # =============================================================================
    # 缓存配置
    # =============================================================================
    CACHE_TTL: int = 3600  # 默认缓存 1 小时
    CACHE_PREFIX: str = "scholar:"

    # =============================================================================
    # 数据源配置
    # =============================================================================
    DATA_SOURCE_TIMEOUT: int = 10  # 单个数据源请求超时（秒）
    DATA_SOURCE_MAX_RESULTS: int = 50  # 单个数据源默认最大结果数

    # =============================================================================
    # 搜索配置
    # =============================================================================
    MAX_SEARCH_RESULTS: int = 500
    DEFAULT_SEARCH_RESULTS: int = 50
    SEARCH_TIMEOUT: int = 120  # 搜索超时（秒）

    # =============================================================================
    # LLM 配置
    # =============================================================================
    LLM_TIMEOUT: int = 60  # LLM 调用超时（秒）
    LLM_MAX_RETRIES: int = 2
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # =============================================================================
    # 安全配置
    # =============================================================================
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    RATE_LIMIT_SEARCH_PER_MINUTE: int = 30  # 每 IP 每分钟搜索请求数
    RATE_LIMIT_ANALYSIS_PER_MINUTE: int = 10  # 每 IP 每分钟分析请求数
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 最大请求体 10MB
    MAX_QUERY_LENGTH: int = 2000  # 查询字符串最大长度
    MAX_LIST_ITEMS: int = 100  # 列表字段最大元素数

    # SSRF 防护
    ALLOW_PRIVATE_IPS: bool = False  # 是否允许访问内网 IP
    ALLOW_HTTP: bool = False  # 是否允许 HTTP（非 HTTPS）

    # LLM 响应限制
    LLM_MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024  # LLM 响应最大 10MB
    LLM_REQUEST_TIMEOUT: int = 30  # LLM 请求超时 30 秒

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# 全局配置实例
settings = Settings()

# 多模型配置（按任务类型分配模型）
# 未配置的任务回退到全局默认（由 load_saved_model_config 设置）
MODEL_PROFILES = {
    "analysis": {"provider": None, "model": None, "api_key": None, "base_url": None},
    "query_planning": {"provider": None, "model": None, "api_key": None, "base_url": None},
    "translation": {"provider": None, "model": None, "api_key": None, "base_url": None},
    "vision": {"provider": "mimo", "model": "mimo-v2.5", "api_key": None, "base_url": None},
    "recommendation": {"provider": None, "model": None, "api_key": None, "base_url": None},
    "diagram": {"provider": "sensenova", "model": "sensenova-u1-fast", "api_key": "ENV", "base_url": "https://token.sensenova.cn/v1"},
}

# 默认配置（所有任务用同一个模型）
DEFAULT_MODEL_CONFIG = {
    "provider": "openai",
    "api_key": None,
    "base_url": None,
    "model_name": None,
    "temperature": 0.7,
    "max_tokens": 4096,
}


def load_saved_model_config():
    """从本地文件加载保存的多模型配置"""
    import json
    import os

    config_path = os.path.join(os.path.dirname(__file__), "..", "model_config.json")
    config_path = os.path.normpath(config_path)
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 兼容旧格式（单模型）
            if "tasks" not in config:
                # 旧格式：所有任务用同一个模型
                api_key = config.get("api_key")
                base_url = config.get("base_url")
                model_name = config.get("model_name")
                provider = config.get("provider", "openai")

                for task in MODEL_PROFILES:
                    MODEL_PROFILES[task] = {
                        "provider": provider,
                        "model": model_name,
                        "api_key": api_key,
                        "base_url": base_url,
                    }

                # 更新全局设置
                if api_key:
                    settings.OPENAI_API_KEY = api_key
                if base_url:
                    settings.OPENAI_API_BASE = base_url
                if model_name:
                    settings.OPENAI_DEFAULT_MODEL = model_name
            else:
                # 新格式：每个任务独立配置
                for task_name, task_config in config.get("tasks", {}).items():
                    if task_name in MODEL_PROFILES:
                        MODEL_PROFILES[task_name].update(task_config)

                # 用 analysis 的配置作为全局默认
                primary = MODEL_PROFILES.get("analysis", {})
                if primary.get("api_key"):
                    settings.OPENAI_API_KEY = primary["api_key"]
                if primary.get("base_url"):
                    settings.OPENAI_API_BASE = primary["base_url"]
                if primary.get("model"):
                    settings.OPENAI_DEFAULT_MODEL = primary["model"]

            return config
    except Exception:
        pass
    return None


def get_model_for_task(task: str) -> dict:
    """获取指定任务的模型配置，回退到默认配置"""
    profile = MODEL_PROFILES.get(task, {})

    # 处理 API Key：如果值是 "ENV" 或空，从 settings 读取
    api_key = profile.get("api_key")
    if not api_key or api_key == "ENV":
        if profile.get("provider") == "sensenova":
            api_key = settings.SENSENOVA_API_KEY
        else:
            api_key = settings.OPENAI_API_KEY

    base_url = profile.get("base_url")
    if not base_url:
        base_url = settings.OPENAI_API_BASE

    return {
        "provider": profile.get("provider") or "openai",
        "api_key": api_key,
        "base_url": base_url,
        "model": profile.get("model") or settings.OPENAI_DEFAULT_MODEL,
    }


# 启动时加载保存的配置
load_saved_model_config()
