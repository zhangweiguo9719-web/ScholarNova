"""
自定义异常类
"""

from typing import Any, Optional


class ScholarNovaException(Exception):
    """ScholarAgent 基础异常"""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "detail": self.message,
            "code": self.code,
        }
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(ScholarNovaException):
    """资源不存在"""

    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="NOT_FOUND",
            status_code=404,
        )


class ValidationError(ScholarNovaException):
    """数据验证错误"""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class ExternalServiceError(ScholarNovaException):
    """外部服务错误"""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"Error from {service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
        )


class RateLimitError(ScholarNovaException):
    """速率限制错误"""

    def __init__(self, service: str):
        super().__init__(
            message=f"Rate limit exceeded for {service}",
            code="RATE_LIMIT_ERROR",
            status_code=429,
        )


class AuthenticationError(ScholarNovaException):
    """认证错误"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationError(ScholarNovaException):
    """授权错误"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class SearchError(ScholarNovaException):
    """搜索错误"""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="SEARCH_ERROR",
            status_code=500,
            details=details,
        )


class LLMError(ScholarNovaException):
    """LLM 调用错误"""

    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"LLM error from {provider}: {message}",
            code="LLM_ERROR",
            status_code=502,
        )


class DataSourceError(ScholarNovaException):
    """数据源错误"""

    def __init__(self, source: str, message: str):
        super().__init__(
            message=f"Data source error from {source}: {message}",
            code="DATA_SOURCE_ERROR",
            status_code=502,
        )
