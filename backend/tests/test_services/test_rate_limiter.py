"""Rate-limit buckets must not interfere across user workflows."""

from types import SimpleNamespace

from app.config import settings
from app.core import rate_limiter


def test_endpoint_types_have_independent_rate_limit_buckets(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_ANALYSIS_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_AGENT_PER_MINUTE", 1)
    monkeypatch.setattr(rate_limiter, "_rate_limiter", rate_limiter.RateLimiter())
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

    assert rate_limiter.check_rate_limit(request, "search") is None
    assert rate_limiter.check_rate_limit(request, "analysis") is None
    assert rate_limiter.check_rate_limit(request, "agent") is None

    assert rate_limiter.check_rate_limit(request, "search").status_code == 429
    assert rate_limiter.check_rate_limit(request, "analysis").status_code == 429
    assert rate_limiter.check_rate_limit(request, "agent").status_code == 429
