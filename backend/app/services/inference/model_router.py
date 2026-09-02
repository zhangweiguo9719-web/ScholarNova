"""Explicit primary/fallback routing for text inference tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from app.config import get_fallback_model_config, get_model_for_task
from app.services.llm.gateway import LLMGateway

TEXT_TASKS = {
    "analysis",
    "query_planning",
    "translation",
    "recommendation",
    "assistant",
}


@dataclass(frozen=True)
class ModelAttempt:
    role: str
    provider: str
    model: str
    status: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoutedChatResult:
    content: str
    profile: dict[str, Any]
    usage: dict[str, int]
    attempts: tuple[ModelAttempt, ...]
    fallback_used: bool


class AllModelsUnavailableError(RuntimeError):
    """All explicitly allowed model routes failed."""

    def __init__(
        self,
        attempts: list[ModelAttempt],
        usage: dict[str, int],
    ) -> None:
        super().__init__("All configured text-model routes are unavailable")
        self.attempts = tuple(attempts)
        self.usage = usage


def _empty_usage() -> dict[str, int]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "requests": 0,
    }


def _read_usage(gateway: Any, *, succeeded: bool) -> dict[str, int]:
    raw = getattr(gateway, "usage", None)
    if raw is None and succeeded:
        raw = getattr(gateway, "last_usage", None)
    if not isinstance(raw, dict):
        return _empty_usage()
    return {
        key: max(0, int(raw.get(key, 0) or 0))
        for key in _empty_usage()
    }


def _add_usage(total: dict[str, int], usage: dict[str, int]) -> None:
    for key in total:
        total[key] += usage.get(key, 0)


def _gateway_for_profile(
    factory: Callable[..., Any],
    profile: dict[str, Any],
    *,
    task: str,
    role: str,
) -> Any:
    from_profile = getattr(factory, "from_profile", None)
    if callable(from_profile):
        return from_profile(profile)
    gateway = (
        factory(task=task)
        if role == "primary"
        else factory(provider=profile.get("provider"))
    )
    configure = getattr(gateway, "configure", None)
    if callable(configure):
        configure(
            api_key=profile.get("api_key"),
            base_url=profile.get("base_url"),
            model_name=profile.get("model"),
        )
    return gateway


def _request_options(provider: str) -> dict[str, Any]:
    if provider == "zhipu":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    return {}


async def chat_with_fallback(
    *,
    task: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    gateway_factory: Callable[..., Any] = LLMGateway,
) -> RoutedChatResult:
    """Call the primary route, then one explicitly enabled text fallback."""
    primary = get_model_for_task(task)
    routes: list[tuple[str, dict[str, Any]]] = [("primary", primary)]
    fallback = get_fallback_model_config()
    same_route = (
        fallback.get("provider") == primary.get("provider")
        and fallback.get("model") == primary.get("model")
        and fallback.get("base_url") == primary.get("base_url")
    )
    if task in TEXT_TASKS and fallback.get("enabled") and not same_route:
        routes.append(("fallback", fallback))

    attempts: list[ModelAttempt] = []
    total_usage = _empty_usage()
    for role, profile in routes:
        gateway = _gateway_for_profile(
            gateway_factory,
            profile,
            task=task,
            role=role,
        )
        try:
            content = await gateway.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **_request_options(str(profile.get("provider") or "")),
            )
            usage = _read_usage(gateway, succeeded=True)
            _add_usage(total_usage, usage)
            attempts.append(
                ModelAttempt(
                    role=role,
                    provider=str(profile.get("provider") or "unknown"),
                    model=str(profile.get("model") or "unknown"),
                    status="completed",
                    **usage,
                )
            )
            return RoutedChatResult(
                content=content,
                profile=profile,
                usage=total_usage,
                attempts=tuple(attempts),
                fallback_used=role == "fallback",
            )
        except Exception as exc:
            usage = _read_usage(gateway, succeeded=False)
            _add_usage(total_usage, usage)
            attempts.append(
                ModelAttempt(
                    role=role,
                    provider=str(profile.get("provider") or "unknown"),
                    model=str(profile.get("model") or "unknown"),
                    status="unavailable",
                    error_type=type(exc).__name__,
                    **usage,
                )
            )

    raise AllModelsUnavailableError(attempts, total_usage)
