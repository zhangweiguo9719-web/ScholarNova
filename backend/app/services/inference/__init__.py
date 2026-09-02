"""Inference-stage helpers for grounded research answers."""

from app.services.inference.answer_verifier import (
    CitationVerification,
    build_retrieval_fallback,
    verify_answer_citations,
)
from app.services.inference.model_router import (
    AllModelsUnavailableError,
    ModelAttempt,
    RoutedLLMGateway,
    RoutedChatResult,
    chat_with_fallback,
)
from app.services.inference.capability_probe import (
    latest_probe_report,
    run_capability_probe,
    save_probe_report,
)

__all__ = [
    "CitationVerification",
    "build_retrieval_fallback",
    "verify_answer_citations",
    "AllModelsUnavailableError",
    "ModelAttempt",
    "RoutedLLMGateway",
    "RoutedChatResult",
    "chat_with_fallback",
    "latest_probe_report",
    "run_capability_probe",
    "save_probe_report",
]
