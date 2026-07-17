"""Network and institutional-library configuration endpoints."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import runtime_path
from app.core.ssrf import validate_url


router = APIRouter()
_CONFIG_PATH = runtime_path("network_config.json")
_DEFAULT_LIBRARY_URL = "https://lib.lut.edu.cn/"

_network_config: dict[str, Any] = {
    "library_url": _DEFAULT_LIBRARY_URL,
    "campus_proxy_url": "",
    "google_scholar_accessible": None,
    "library_accessible": None,
    "campus_proxy_accessible": None,
    "last_results": {},
    "last_details": {},
}


class NetworkConfigRequest(BaseModel):
    library_url: Optional[str] = _DEFAULT_LIBRARY_URL
    campus_proxy_url: Optional[str] = ""
    # Backward-compatible only. Older clients stored the library homepage here.
    proxy_url: Optional[str] = None


class NetworkConfigResponse(BaseModel):
    library_url: str
    campus_proxy_url: str
    google_scholar_accessible: Optional[bool] = None
    library_accessible: Optional[bool] = None
    campus_proxy_accessible: Optional[bool] = None
    results: dict[str, Optional[bool]] = Field(default_factory=dict)
    details: dict[str, dict[str, Any]] = Field(default_factory=dict)


def _public_config() -> NetworkConfigResponse:
    return NetworkConfigResponse(
        library_url=_network_config["library_url"],
        campus_proxy_url=_network_config["campus_proxy_url"],
        google_scholar_accessible=_network_config.get("google_scholar_accessible"),
        library_accessible=_network_config.get("library_accessible"),
        campus_proxy_accessible=_network_config.get("campus_proxy_accessible"),
        results=_network_config.get("last_results", {}),
        details=_network_config.get("last_details", {}),
    )


def _persist_config() -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(_network_config, handle, ensure_ascii=False, indent=2)


def _validated_external_url(value: str, field_name: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    valid, error = validate_url(value)
    if not valid:
        raise HTTPException(status_code=422, detail=f"{field_name}: {error}")
    return value


async def _check_url(
    client: httpx.AsyncClient,
    name: str,
    url: str,
    *,
    reachable_statuses: set[int] | None = None,
) -> tuple[str, bool, dict[str, Any]]:
    started = time.monotonic()
    try:
        response = await client.get(url)
        status = response.status_code
        ok = (
            status in reachable_statuses
            if reachable_statuses is not None
            else 200 <= status < 400
        )
        return name, ok, {
            "status_code": status,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
            "final_url": str(response.url),
            "host": urlparse(str(response.url)).hostname,
        }
    except Exception as exc:
        return name, False, {
            "status_code": None,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
            "error": type(exc).__name__,
        }


@router.get("/config", response_model=NetworkConfigResponse)
async def get_network_config() -> NetworkConfigResponse:
    return _public_config()


@router.post("/config", response_model=NetworkConfigResponse)
async def save_network_config(request: NetworkConfigRequest) -> NetworkConfigResponse:
    legacy = (request.proxy_url or "").strip()
    library_url = (request.library_url or "").strip()
    campus_proxy_url = (request.campus_proxy_url or "").strip()
    if legacy and not library_url:
        legacy_host = (urlparse(legacy).hostname or "").lower()
        if "lib." in legacy_host:
            library_url = legacy
        else:
            campus_proxy_url = legacy

    _network_config["library_url"] = _validated_external_url(
        library_url or _DEFAULT_LIBRARY_URL,
        "图书馆地址",
    )
    # A proxy is not fetched by the server here, but it must still be HTTP(S).
    if campus_proxy_url:
        parsed = urlparse(campus_proxy_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise HTTPException(status_code=422, detail="校园代理必须是有效的 HTTP(S) 代理地址")
    _network_config["campus_proxy_url"] = campus_proxy_url
    _persist_config()
    return _public_config()


@router.post("/detect")
async def detect_network() -> dict[str, Any]:
    """Detect sources concurrently, including the library portal itself."""
    library_url = _network_config.get("library_url") or _DEFAULT_LIBRARY_URL
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
        checks = [
            _check_url(
                client,
                "google_scholar",
                "https://scholar.google.com/scholar?q=academic+search",
                reachable_statuses={200},
            ),
            _check_url(
                client,
                "semantic_scholar",
                "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1",
                reachable_statuses={200, 429},
            ),
            _check_url(client, "crossref", "https://api.crossref.org/works?rows=1"),
            _check_url(client, "openalex", "https://api.openalex.org/works?per-page=1"),
            _check_url(client, "library", library_url),
        ]
        detected = await asyncio.gather(*checks)

    results: dict[str, Optional[bool]] = {}
    details: dict[str, dict[str, Any]] = {}
    for name, ok, detail in detected:
        results[name] = ok
        details[name] = detail

    proxy_url = _network_config.get("campus_proxy_url", "")
    if proxy_url:
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=8) as proxy_client:
                response = await proxy_client.get("https://api.crossref.org/works?rows=1")
            results["campus_proxy"] = 200 <= response.status_code < 400
            details["campus_proxy"] = {
                "status_code": response.status_code,
                "latency_ms": round((time.monotonic() - started) * 1000, 1),
            }
        except Exception as exc:
            results["campus_proxy"] = False
            details["campus_proxy"] = {
                "status_code": None,
                "latency_ms": round((time.monotonic() - started) * 1000, 1),
                "error": type(exc).__name__,
            }
    else:
        results["campus_proxy"] = None
        details["campus_proxy"] = {"message": "未配置；图书馆网页地址不等同于代理地址"}

    _network_config.update({
        "google_scholar_accessible": results["google_scholar"],
        "library_accessible": results["library"],
        "campus_proxy_accessible": results["campus_proxy"],
        "last_results": results,
        "last_details": details,
    })
    _persist_config()
    return {
        "status": "ok",
        "results": results,
        "details": details,
        "library_url": library_url,
        "available_sources": [name for name, ok in results.items() if ok is True],
    }


@router.get("/library-link")
async def get_library_link(q: str = Query("", max_length=2000)) -> dict[str, Any]:
    """Return a legal institutional-discovery handoff without bypassing auth."""
    return {
        "url": _network_config.get("library_url") or _DEFAULT_LIBRARY_URL,
        "query": q.strip(),
        "mode": "portal_handoff",
        "instructions": "已复制检索词；请在图书馆页面完成校园网或统一身份认证后粘贴检索。",
        "requires_institutional_auth": True,
    }


@router.get("/proxy-test")
async def test_proxy() -> dict[str, Any]:
    proxy_url = _network_config.get("campus_proxy_url", "")
    if not proxy_url:
        raise HTTPException(status_code=400, detail="未配置真正的 HTTP(S) 校园代理")
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=10) as client:
            response = await client.get("https://api.crossref.org/works?rows=1")
        return {
            "success": 200 <= response.status_code < 400,
            "status_code": response.status_code,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"代理测试失败: {type(exc).__name__}",
        ) from exc


try:
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open(encoding="utf-8") as handle:
            saved = json.load(handle)
        legacy = saved.get("proxy_url", "")
        if legacy and "lib." in (urlparse(legacy).hostname or ""):
            saved.setdefault("library_url", legacy)
            saved["campus_proxy_url"] = ""
        _network_config.update(saved)
except (OSError, json.JSONDecodeError):
    pass
