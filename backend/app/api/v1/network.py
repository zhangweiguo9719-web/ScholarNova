"""
网络配置与检测 API
纯增量功能，不影响现有搜索逻辑
"""
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter()

# 全局网络配置（内存存储，重启丢失）
_network_config = {
    "proxy_url": "",
    "google_scholar_accessible": None,
    "campus_proxy_accessible": None,
}


class NetworkConfigRequest(BaseModel):
    proxy_url: Optional[str] = ""


class NetworkConfigResponse(BaseModel):
    proxy_url: str
    google_scholar_accessible: Optional[bool] = None
    campus_proxy_accessible: Optional[bool] = None


@router.get("/config", response_model=NetworkConfigResponse)
async def get_network_config():
    """获取当前网络配置"""
    return NetworkConfigResponse(**_network_config)


@router.post("/config", response_model=NetworkConfigResponse)
async def save_network_config(request: NetworkConfigRequest):
    """保存网络配置（代理地址）"""
    _network_config["proxy_url"] = request.proxy_url or ""
    # 保存到文件
    import json
    from app.config import runtime_path
    config_path = runtime_path("network_config.json")
    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(_network_config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return NetworkConfigResponse(**_network_config)


@router.post("/detect")
async def detect_network():
    """检测网络环境"""
    results = {}

    # 检测 Google Scholar
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("https://scholar.google.com", follow_redirects=True)
            results["google_scholar"] = r.status_code == 200
    except Exception:
        results["google_scholar"] = False

    # 检测 Semantic Scholar
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1")
            results["semantic_scholar"] = r.status_code == 200
    except Exception:
        results["semantic_scholar"] = False

    # 检测 CrossRef
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("https://api.crossref.org/works?rows=1")
            results["crossref"] = r.status_code == 200
    except Exception:
        results["crossref"] = False

    # 检测 OpenAlex
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("https://api.openalex.org/works?per_page=1")
            results["openalex"] = r.status_code == 200
    except Exception:
        results["openalex"] = False

    # 检测学校代理（如果有配置）
    proxy_url = _network_config.get("proxy_url", "")
    if proxy_url:
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=10) as client:
                r = await client.get("https://api.crossref.org/works?rows=1")
                results["campus_proxy"] = r.status_code == 200
                _network_config["campus_proxy_accessible"] = True
        except Exception:
            results["campus_proxy"] = False
            _network_config["campus_proxy_accessible"] = False
    else:
        results["campus_proxy"] = None

    _network_config["google_scholar_accessible"] = results.get("google_scholar", False)

    return {
        "status": "ok",
        "results": results,
        "proxy_url": proxy_url,
        "available_sources": [
            s for s, ok in results.items()
            if ok is True
        ],
    }


@router.get("/proxy-test")
async def test_proxy():
    """测试学校代理是否可用"""
    proxy_url = _network_config.get("proxy_url", "")
    if not proxy_url:
        raise HTTPException(status_code=400, detail="未配置代理地址")

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=15) as client:
            # 测试通过代理访问 CrossRef
            r = await client.get("https://api.crossref.org/works?rows=1")
            return {"success": True, "status_code": r.status_code, "latency_ms": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代理测试失败: {str(e)[:200]}")


# 启动时加载配置
try:
    import json
    from app.config import runtime_path
    config_path = runtime_path("network_config.json")
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            _network_config.update(json.load(f))
except Exception:
    pass
