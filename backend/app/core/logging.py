"""
日志配置

提供结构化日志配置和敏感信息脱敏功能。
"""

import logging
import re
import sys
from typing import Optional
from urllib.parse import urlparse, urlencode

import structlog

from app.config import settings


# ---------------------------------------------------------------------------
# 敏感信息脱敏函数
# ---------------------------------------------------------------------------

def mask_api_key(key: Optional[str]) -> str:
    """
    脱敏 API Key

    规则：只显示前 4 位 + ****
    示例：sk-a1b2****

    Args:
        key: API Key 字符串

    Returns:
        脱敏后的字符串
    """
    if not key:
        return "****"
    if len(key) > 4:
        return key[:4] + "****"
    return "****"


def mask_url(url: Optional[str]) -> str:
    """
    脱敏 URL

    保留域名，隐藏路径中的敏感参数（如 API Key）。

    Args:
        url: URL 字符串

    Returns:
        脱敏后的 URL
    """
    if not url:
        return "****"
    try:
        parsed = urlparse(url)
        # 保留 scheme + host
        masked = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            masked += f":{parsed.port}"
        # 路径保留但查询参数脱敏
        if parsed.path and parsed.path != "/":
            masked += parsed.path
        if parsed.query:
            # 脱敏查询参数中的敏感字段
            masked += "?[参数已脱敏]"
        return masked
    except Exception:
        return "****"


def mask_sensitive(data: str, field_type: str) -> str:
    """
    根据字段类型脱敏

    Args:
        data: 待脱敏的数据
        field_type: 字段类型
            - "api_key": API Key
            - "url": URL
            - "query": 用户查询（保留，不脱敏）
            - "ip": IP 地址（保留，用于安全审计）

    Returns:
        脱敏后的字符串
    """
    if field_type == "api_key":
        return mask_api_key(data)
    elif field_type == "url":
        return mask_url(data)
    elif field_type in ("query", "ip"):
        # 查询和 IP 保留原样
        return data
    return data


# 已知的敏感 Key 模式（用于日志中自动脱敏）
_SENSITIVE_PATTERNS = [
    # OpenAI / 通用 sk- 开头的 key
    re.compile(r"(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{20,}"),
    # Anthropic key
    re.compile(r"(sk-ant-[a-zA-Z0-9]{4})[a-zA-Z0-9]{20,}"),
    # Bearer token
    re.compile(r"(Bearer\s+[a-zA-Z0-9]{4})[a-zA-Z0-9]{20,}"),
]


def auto_mask_secrets(text: str) -> str:
    """
    自动检测并脱敏日志文本中的敏感信息

    Args:
        text: 日志文本

    Returns:
        脱敏后的文本
    """
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub(r"\1****", text)
    return text


# ---------------------------------------------------------------------------
# structlog 处理器：自动脱敏
# ---------------------------------------------------------------------------

def _sensitive_mask_processor(
    logger: logging.Logger, method_name: str, event_dict: dict
) -> dict:
    """
    structlog 处理器：自动脱敏事件字典中的敏感字段

    检查所有键值对，如果键名包含 "key"、"token"、"secret"、"password" 等关键词，
    则对值进行脱敏。
    """
    sensitive_keys = {"api_key", "apikey", "token", "secret", "password", "authorization"}
    for key, value in event_dict.items():
        if isinstance(value, str) and any(s in key.lower() for s in sensitive_keys):
            event_dict[key] = mask_api_key(value)
        elif isinstance(value, str) and "key" in key.lower() and len(value) > 10:
            # 通用长字符串 key 脱敏
            event_dict[key] = mask_api_key(value)
    return event_dict


# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------

def setup_logging(log_level: Optional[str] = None) -> None:
    """
    设置日志配置

    Args:
        log_level: 日志级别
    """
    level = log_level or settings.LOG_LEVEL

    # 配置 structlog
    if settings.LOG_FORMAT == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            _sensitive_mask_processor,  # 脱敏处理器
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(level),
    )

    # 设置第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    return structlog.get_logger(name)
