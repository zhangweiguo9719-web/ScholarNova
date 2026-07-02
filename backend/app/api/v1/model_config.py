"""
模型配置相关 API 端点
"""

import time

from fastapi import APIRouter, HTTPException, Request

from app.core.rate_limiter import check_rate_limit
from app.core.ssrf import validate_base_url
from app.schemas.search import (
    ModelConfig,
    ModelTestRequest,
    ModelTestResponse,
    SuccessResponse,
)

router = APIRouter()


@router.post("/config", response_model=SuccessResponse)
async def save_model_config(
    config: ModelConfig,
) -> SuccessResponse:
    """
    保存模型配置

    保存用户的 LLM 模型配置到内存缓存和本地文件
    """
    import json
    config_data = config.model_dump()

    # 更新全局多模型配置
    from app.config import MODEL_PROFILES, settings
    api_key = config.api_key
    base_url = config.base_url
    model_name = config.model_name
    provider = config.provider

    if config.tasks:
        # 有任务级配置，更新对应的任务
        for task_name, task_config in config.tasks.items():
            if task_name in MODEL_PROFILES:
                MODEL_PROFILES[task_name] = {
                    "provider": task_config.provider or provider,
                    "model": task_config.model_name or model_name,
                    "api_key": task_config.api_key or api_key,
                    "base_url": task_config.base_url or base_url,
                }

    # 所有未单独配置的任务用主配置
    for task_name in MODEL_PROFILES:
        if config.tasks and task_name in config.tasks:
            continue
        MODEL_PROFILES[task_name] = {
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

    # 保存到本地文件
    from app.config import runtime_path
    config_path = runtime_path("model_config.json")
    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"保存配置文件失败: {e}")

    return SuccessResponse(
        success=True,
        message="模型配置已保存",
    )


@router.post("/test", response_model=ModelTestResponse)
async def test_model_connection(
    request: ModelTestRequest,
    http_request: Request,
) -> ModelTestResponse:
    """
    测试模型连通性

    测试 LLM 模型配置是否正确，能否正常调用
    """
    # 速率限制检查
    rate_limit_response = check_rate_limit(http_request, endpoint_type="analysis")
    if rate_limit_response:
        return rate_limit_response

    # SSRF 防护：验证 base_url
    if request.base_url:
        is_valid, error = validate_base_url(request.base_url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"API 地址不安全: {error}",
            )

    from app.services.llm.gateway import LLMGateway

    start_time = time.time()

    try:
        # 创建 LLM 客户端
        gateway = LLMGateway(provider=request.provider)

        # 用用户提供的配置覆盖默认设置
        gateway.configure(
            api_key=request.api_key,
            base_url=request.base_url,
            model_name=request.model_name,
        )

        # 发送测试请求
        result = await gateway.test_connection()
        latency_ms = (time.time() - start_time) * 1000

        if result["success"]:
            return ModelTestResponse(
                success=True,
                latency_ms=latency_ms,
                model_info={
                    "provider": request.provider,
                    "model": request.model_name,
                },
                error=None,
            )
        else:
            return ModelTestResponse(
                success=False,
                latency_ms=latency_ms,
                model_info=None,
                error=result.get("error", "Unknown error"),
            )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return ModelTestResponse(
            success=False,
            latency_ms=latency_ms,
            model_info=None,
            error=str(e),
        )
