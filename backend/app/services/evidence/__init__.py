"""
证据验证服务模块
"""

from app.services.evidence.extractor import (
    EvidenceExtractor,
    EvidenceSpan,
    VerifiedEvidence,
)
from app.services.evidence.verifier import (
    EvidenceVerifier,
    VerifiedEvidenceResult,
)

__all__ = [
    "EvidenceExtractor",
    "EvidenceSpan",
    "VerifiedEvidence",
    "EvidenceVerifier",
    "VerifiedEvidenceResult",
]
